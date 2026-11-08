# Local stand-in for GitHub Actions (news-pages.yml + release) while Actions is unavailable.
# Runs from Task Scheduler. Writes only to its own two worktrees, to main (generated pages, fast-forward) and to R2.
param(
  [string]$ReleaseTree = 'D:\CorteFlow\work\raven-cf-release',
  [string]$BuildTree = 'D:\CorteFlow\work\raven-builder-outputs-20261107',
  [string]$LogDir = 'D:\CorteFlow\work\raven-cf-release-logs',
  [string]$AccountId = 'f6140a337d3b05e5e27c7f64ed166134'
)
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'release.mjs'
New-Item -ItemType Directory -Force $LogDir | Out-Null
$log = Join-Path $LogDir 'release.log'
$last = Join-Path $LogDir 'last-released-sha.txt'
function Log($m) { "$(Get-Date -Format s) $m" | Add-Content -Encoding utf8 $log }

# What news-pages.yml did: regenerate pages/covers for new news commits and push them to main.
function Update-Pages {
  $ErrorActionPreference = 'Continue'
  git -C $BuildTree fetch -q origin main
  git -C $BuildTree reset -q --hard origin/main
  git -C $BuildTree clean -fdq -- index.html public  # own worktree: drop leftovers of earlier runs
  Push-Location $BuildTree
  try {
    foreach ($b in 'build-raven.py', 'build-column.py', 'build-news-index.py', 'build-library.py') {
      $o = & python $b 2>&1
      if ($LASTEXITCODE -ne 0) { Log "PAGES FAILED $b`: $((($o | Out-String).Trim() -split "\r?\n")[-1])"; return }
    }
    git add index.html public/noticias.html public/noticias public/sitemap.xml public/robots.txt public/raven-analytics.js public/editorial-feed.json public/editorial-images.json public/editorial/covers public/editorial/photos public/editorial-photo-credits.json public/creditos-fotos.html public/coluna.html public/coluna public/livros.html public/livros.json
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) { return }  # builders produced nothing new
    git -c user.name="github-actions[bot]" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" commit -q -m "Atualizar paginas indexaveis da Coluna"
    foreach ($v in 'content-integrity.mjs', 'public-pages.mjs') {
      $o = & node (Join-Path $PSScriptRoot $v) HEAD 2>&1
      if ($LASTEXITCODE -ne 0) { Log "PAGES BLOCKED by $v (not pushed)"; ($o | Out-String) -split "\r?\n" | Where-Object { $_ -match '"[^"]+: |missing|no page' } | ForEach-Object { Log "  $_" }; return }
    }
    git push -q origin HEAD:main 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Log "PAGES push rejected (main moved); retrying next run"; return }
    Log "PAGES pushed $(git rev-parse --short HEAD)"
  } finally { Pop-Location }
}

try {
  Update-Pages
  git -C $ReleaseTree fetch -q origin main
  $sha = (git -C $ReleaseTree rev-parse origin/main).Trim()
  if ((Test-Path $last) -and ((Get-Content $last -Raw).Trim() -eq $sha)) { exit 0 }  # nothing new
  if (Test-Path $last) {
    $prev = (Get-Content $last -Raw).Trim()
    git -C $ReleaseTree merge-base --is-ancestor $prev $sha
    if ($LASTEXITCODE -eq 1) { Log "SKIP $sha`: not a descendant of last released $prev"; exit 0 }
  }
  # No-checkout worktree: moving HEAD only, no files are written.
  git -C $ReleaseTree reset -q --soft $sha
  # Touching the cf CLI refreshes its short-lived OAuth token, which release.mjs reuses.
  & "$env:APPDATA\npm\cf.cmd" auth whoami *> $null
  $env:CLOUDFLARE_ACCOUNT_ID = $AccountId
  $cfFile = Join-Path $env:APPDATA 'xdg.config\cloudflare\config\default.json'
  if (-not (Test-Path $cfFile)) { Log "cf login file not visible: $cfFile (USER=$env:USERNAME, PROFILE=$env:USERPROFILE)" }
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
