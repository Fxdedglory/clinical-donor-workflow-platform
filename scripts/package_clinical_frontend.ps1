$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistRoot = Join-Path $RepoRoot "app\frontend\dist"
$TargetRoot = Join-Path $RepoRoot "artifacts\teemails-Clinical\Clinical"

if (!(Test-Path $DistRoot)) {
  throw "Missing frontend dist folder. Run npm run build first."
}

Remove-Item $TargetRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $TargetRoot | Out-Null

Copy-Item -Path (Join-Path $DistRoot "*") -Destination $TargetRoot -Recurse -Force

$indexPath = Join-Path $TargetRoot "index.html"

if (!(Test-Path $indexPath)) {
  throw "Missing packaged Clinical index.html"
}

$index = Get-Content $indexPath -Raw

if ($index -notmatch "Meridian Clinical") {
  throw "Packaged Clinical index does not include Meridian Clinical."
}

Write-Host "Clinical frontend packaged successfully:" -ForegroundColor Green
Write-Host "  $TargetRoot"