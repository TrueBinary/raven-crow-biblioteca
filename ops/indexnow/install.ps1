[CmdletBinding()]
param(
    [string]$SourceRoot,
    [string]$InstallRoot = 'D:\CorteFlow\ops\indexnow',
    [string]$PythonExe,
    [switch]$PlanOnly
)

function Get-IndexNowInstallPlan {
    [CmdletBinding()]
    param([string]$SourceRoot, [string]$InstallRoot, [string]$PythonExe)
    $source = [IO.Path]::GetFullPath($SourceRoot).TrimEnd('\')
    $root = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\')
    if ($root -eq $source -or $root.StartsWith($source + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $source.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'InstallRoot and SourceRoot must not overlap.'
    }
    if (-not [IO.Path]::IsPathRooted($PythonExe) -or -not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
        throw 'PythonExe must be an existing absolute python.exe or pythonw.exe.'
    }
    $python = [IO.Path]::GetFullPath($PythonExe)
    if ([IO.Path]::GetFileName($python) -notin @('python.exe', 'pythonw.exe')) {
        throw 'Choose python.exe or pythonw.exe from the Python installation.'
    }
    $console = Join-Path ([IO.Path]::GetDirectoryName($python)) 'python.exe'
    $windowless = Join-Path ([IO.Path]::GetDirectoryName($python)) 'pythonw.exe'
    if (-not (Test-Path -LiteralPath $console -PathType Leaf) -or
        -not (Test-Path -LiteralPath $windowless -PathType Leaf)) { throw 'Both python.exe and pythonw.exe are required.' }
    $sha = & git -C $source rev-parse --verify 'HEAD^{commit}'
    if ($LASTEXITCODE -ne 0 -or "$sha" -notmatch '^[0-9a-f]{40}$') { throw 'SourceRoot must contain a valid Git commit.' }
    $entries = @(& git -C $source ls-tree -r $sha -- ops/indexnow/)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inventory the pinned commit.' }
    $files = @($entries | ForEach-Object {
        if ($_ -notmatch '^100(?:644|755) blob [0-9a-f]{40}\t(ops/indexnow/[^\r\n]+)$') {
            throw 'Only regular committed package files may be installed.'
        }
        $relative = $Matches[1]
        if ($relative -match '(^|/)\.\.(/|$)|["\\:]') { throw 'Unsafe package path.' }
        @{ source = $relative; destination = Join-Path (Join-Path $root 'app') $relative }
    })
    $required = @('__init__.py', '__main__.py', 'snapshot.py', 'state.py', 'client.py')
    $missing = @($required | Where-Object { 'ops/indexnow/' + $_ -notin @($files | ForEach-Object { $_.source }) })
    return @{
        source_root = $source; install_root = $root; installed_sha = "$sha"
        task_name = 'Raven Crow - IndexNow'; interval_minutes = 5
        execution_limit_seconds = 120; multiple_instances = 'IgnoreNew'
        working_directory = Join-Path $root 'app'; executable = $windowless; console_executable = $console
        arguments = '-m ops.indexnow run --config "' + (Join-Path $root 'config.json') + '"'
        config_path = Join-Path $root 'config.json'; files = $files; missing_runtime_files = $missing
        interactive_only = $true; logon_type = 'Interactive'; hidden = $true; start_when_available = $true
    }
}

function Assert-IndexNowChildPath {
    param([string]$Root, [string]$Path)
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith([IO.Path]::GetFullPath($Root).TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Installer operation escaped InstallRoot.'
    }
    if (Test-Path -LiteralPath $full) {
        if ((Get-Item -LiteralPath $full -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'Installer refuses reparse points.'
        }
    }
}

function Install-IndexNowRuntime {
    [CmdletBinding()]
    param([hashtable]$Plan, [scriptblock]$RegisterTask)
    if (-not $RegisterTask) { throw 'A task registration callback is required.' }
    # Revalidate the pinned commit, never replace it with a newer HEAD.
    if ($Plan.installed_sha -notmatch '^[0-9a-f]{40}$') { throw 'Invalid installed_sha.' }
    if (@($Plan.missing_runtime_files).Count) { throw 'Pinned commit lacks the complete IndexNow runtime.' }
    $root = [IO.Path]::GetFullPath($Plan.install_root).TrimEnd('\')
    $app = Join-Path $root 'app'
    $id = [Guid]::NewGuid().ToString('N')
    $stage = Join-Path $root ('.stage-' + $id)
    $backup = Join-Path $root ('.backup-' + $id)
    $version = Join-Path $root 'installed-version.txt'
    foreach ($path in @($app, $stage, $backup, $version, (Join-Path $root '.install.lock'))) {
        Assert-IndexNowChildPath $root $path
    }
    if (-not (Test-Path -LiteralPath $root)) { $null = New-Item -ItemType Directory -Path $root }
    $lock = $null; $lease = $null; $swapped = $false; $hadApp = $false
    $oldVersion = $null
    if (Test-Path -LiteralPath $version) { $oldVersion = [IO.File]::ReadAllBytes($version) }
    try {
        # A persistent file, exclusively opened; no unlink race between installers.
        try { $lock = [IO.File]::Open((Join-Path $root '.install.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
        catch { throw 'Another IndexNow installation is in progress.' }
        $null = New-Item -ItemType Directory -Path $stage
        $archive = Join-Path $stage 'runtime.zip'
        & git -C $Plan.source_root archive --format=zip "--output=$archive" $Plan.installed_sha -- ops/indexnow/
        if ($LASTEXITCODE -ne 0) { throw 'Cannot archive the pinned runtime commit.' }
        $stagedApp = Join-Path $stage 'app'
        Expand-Archive -LiteralPath $archive -DestinationPath $stagedApp
        foreach ($name in @('__init__.py', '__main__.py', 'snapshot.py', 'state.py', 'client.py')) {
            if (-not (Test-Path -LiteralPath (Join-Path $stagedApp ('ops\indexnow\' + $name)) -PathType Leaf)) {
                throw "Pinned commit is missing $name."
            }
        }
        # Keep the StateStore lease AND a SQLite write transaction until registration
        # finishes. The latter fences renewal/claim even if the 180s lease expires.
        # Parent death closes stdin; the child then rolls back and releases the lease.
        $helper = @'
import json, os, pathlib, sqlite3, sys, time, uuid
ctx = json.loads(os.environ['INDEXNOW_INSTALL_CONTEXT'])
sys.path.insert(0, ctx['app'])
from ops.indexnow.state import StateStore
config_path = pathlib.Path(ctx['config'])
config = json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
db = pathlib.Path(config.get('state_db', str(config_path.parent / 'state.sqlite3')))
if not db.is_absolute():
    raise ValueError('state_db must be absolute')
store = StateStore(db)
owner = 'install-' + uuid.uuid4().hex
fence = None
claimed = False
try:
    claimed = store.claim(owner, int(time.time()), ttl=180)
    if not claimed:
        raise RuntimeError('IndexNow runner lease is busy; retry installation after it exits')
    fence = sqlite3.connect(db, timeout=5)
    fence.execute('BEGIN IMMEDIATE')
    print('READY', flush=True)
    sys.stdin.readline()
finally:
    if fence is not None:
        fence.rollback()
        fence.close()
    if claimed:
        store.release(owner)
    store.close()
'@
        $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($helper))
        $start = New-Object Diagnostics.ProcessStartInfo
        $start.FileName = $Plan.console_executable
        $start.Arguments = '-I -B -u -c "exec(__import__(''base64'').b64decode(''' + $encoded + '''))"'
        $start.UseShellExecute = $false; $start.CreateNoWindow = $true
        $start.RedirectStandardInput = $true; $start.RedirectStandardOutput = $true; $start.RedirectStandardError = $true
        $start.EnvironmentVariables['INDEXNOW_INSTALL_CONTEXT'] = (@{ app=$stagedApp; config=$Plan.config_path } | ConvertTo-Json -Compress)
        $lease = New-Object Diagnostics.Process
        $lease.StartInfo = $start
        $null = $lease.Start()
        $leaseErrors = $lease.StandardError.ReadToEndAsync()
        $ready = $lease.StandardOutput.ReadLineAsync()
        if (-not $ready.Wait(15000)) { throw 'Timed out acquiring the installer lease.' }
        if ($ready.Result -ne 'READY') {
            $lease.WaitForExit()
            throw ('Cannot acquire IndexNow installer lease: ' + $leaseErrors.Result)
        }
        $hadApp = Test-Path -LiteralPath $app
        if ($hadApp) { Move-Item -LiteralPath $app -Destination $backup }
        try { Move-Item -LiteralPath $stagedApp -Destination $app }
        catch {
            if ($hadApp) { Move-Item -LiteralPath $backup -Destination $app }
            throw
        }
        $swapped = $true
        [IO.File]::WriteAllText($version, $Plan.installed_sha + "`n", (New-Object Text.UTF8Encoding($false)))
        $null = & $RegisterTask $Plan
        return @{ installed_sha=$Plan.installed_sha; task_name=$Plan.task_name; install_root=$root }
    }
    catch {
        if ($swapped) {
            Assert-IndexNowChildPath $root $app
            Remove-Item -LiteralPath $app -Recurse -Force
            if ($hadApp) { Move-Item -LiteralPath $backup -Destination $app }
            if ($null -ne $oldVersion) { [IO.File]::WriteAllBytes($version, $oldVersion) }
            elseif (Test-Path -LiteralPath $version) { Remove-Item -LiteralPath $version -Force }
        }
        throw
    }
    finally {
        if ($lease) {
            if (-not $lease.HasExited) {
                $lease.StandardInput.Close()
                if (-not $lease.WaitForExit(10000)) { $lease.Kill(); $lease.WaitForExit() }
            }
            $lease.Dispose()
        }
        foreach ($path in @($stage, $backup)) {
            Assert-IndexNowChildPath $root $path
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
        }
        if ($lock) { $lock.Dispose() }
    }
}

# Dot-source is definition-only, including when arguments were supplied.
if ($MyInvocation.InvocationName -ne '.') {
    $ErrorActionPreference = 'Stop'
    try {
        if (-not $SourceRoot) { $SourceRoot = Join-Path $PSScriptRoot '..\..' }
        $plan = Get-IndexNowInstallPlan $SourceRoot $InstallRoot $PythonExe
        if ($PlanOnly) { $plan | ConvertTo-Json -Depth 8 }
        else {
            Install-IndexNowRuntime $plan {
                param($request)
                $action = New-ScheduledTaskAction -Execute $request.executable -Argument $request.arguments -WorkingDirectory $request.working_directory
                $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 5)
                $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Seconds 120) -StartWhenAvailable -Hidden
                $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
                Register-ScheduledTask -TaskName $request.task_name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force -ErrorAction Stop
            } | ConvertTo-Json -Depth 8
        }
    }
    catch { Write-Error $_; exit 1 }
}
