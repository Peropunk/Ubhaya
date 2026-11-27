# UBHAYA offline setup for Windows (P0.8).
#   While online, once:   .\scripts\setup_offline.ps1 -Download   (fills vendor\wheels)
#   On any laptop:        .\scripts\setup_offline.ps1             (installs from vendor\wheels if present)
param([switch]$Download)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$start = Get-Date

if (-not (Test-Path .venv)) { python -m venv .venv }
$py = ".\.venv\Scripts\python.exe"

if ($Download) {
    & $py -m pip download -r requirements.txt -d vendor\wheels
    Write-Host "Wheels saved to vendor\wheels. Copy the whole repo folder to the offline laptop."
    exit 0
}

if (Test-Path vendor\wheels) {
    & $py -m pip install --no-index --find-links vendor\wheels -r requirements.txt
} else {
    Write-Host "vendor\wheels not found: installing from the internet"
    & $py -m pip install -r requirements.txt
}

& $py manage.py load-demo --fresh
& $py manage.py test
if ($LASTEXITCODE -ne 0) { throw "tests failed" }
$mins = [math]::Round(((Get-Date) - $start).TotalMinutes, 1)
Write-Host "Setup done in $mins min. Start with:  .\.venv\Scripts\python.exe manage.py run   then open http://127.0.0.1:8000/ui/"
