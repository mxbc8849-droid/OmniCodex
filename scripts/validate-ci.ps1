$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$workflow = Join-Path $root '.github/workflows/ci.yml'
$compose = Join-Path $root 'docker-compose.yml'

$missing = @()
if (-not (Get-Command actionlint -ErrorAction SilentlyContinue)) { $missing += 'actionlint (https://github.com/rhysd/actionlint/releases)' }
if (-not (Get-Command yamllint -ErrorAction SilentlyContinue)) { $missing += 'yamllint (python -m pip install yamllint)' }
if ($missing.Count -gt 0) { throw "Missing required CI lint tools: $($missing -join ', ')" }

Push-Location $root
try {
  actionlint $workflow
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  yamllint -c .yamllint.yml $workflow $compose
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  Write-Host 'CI configuration is valid.' -ForegroundColor Green
} finally { Pop-Location }
