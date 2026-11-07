# Local stand-in for the GitHub Actions release while Actions is unavailable.
# Runs from Task Scheduler; only reads Git and writes to R2. Never commits, resets files or touches other worktrees.
param(
  [string]$ReleaseTree = 'D:\CorteFlow\work\raven-cf-release',
  [string]$LogDir = 'D:\CorteFlow\work\raven-cf-release-logs',
  [string]$AccountId = 'f6140a337d3b05e5e27c7f64ed166134'
)
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'release.mjs'
New-Item -ItemType Directory -Force $LogDir | Out-Null
$log = Join-Path $LogDir 'release.log'
$last = Join-Path $LogDir 'last-released-sha.txt'
function Log($m) { "$(Get-Date -Format s) $m" | Add-Content -Encoding utf8 $log }

try {
  git -C $ReleaseTree fetch -q origin main
  $sha = (git -C $ReleaseTree rev-parse origin/main).Trim()
  if ((Test-Path $last) -and ((Get-Content $last -Raw).Trim() -eq $sha)) { exit 0 }  # nothing new
  # No-checkout worktree: moving HEAD only, no files are written.
  git -C $ReleaseTree reset -q --soft $sha
  # Touching the cf CLI refreshes its short-lived OAuth token, which release.mjs reuses.
  & "$env:APPDATA\npm\cf.cmd" auth whoami *> $null
  $env:CLOUDFLARE_ACCOUNT_ID = $AccountId
  Push-Location $ReleaseTree
  # PS 5.1 turns native stderr lines into terminating errors under 'Stop'; node logs progress there.
  $ErrorActionPreference = 'Continue'
  try { $out = & node $script $sha 2>&1 } finally { Pop-Location; $ErrorActionPreference = 'Stop' }
  $code = $LASTEXITCODE
  ($out | Out-String) -split "\r?\n" | Where-Object { $_.Trim() } | ForEach-Object { Log "  $_" }
  if ($code -eq 0) { Set-Content -Encoding ascii $last $sha; Log "OK $sha" }
  else { Log "FAILED $sha (exit $code)"; exit $code }
} catch {
  Log "ERROR $($_.Exception.Message)"
  exit 1
}
