$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.\sumo_env\Scripts\python.exe')) {
    py -3 -m venv sumo_env
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 or newer first.' }
}
& .\sumo_env\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed.' }
& .\sumo_env\Scripts\python.exe main.py setup
if ($LASTEXITCODE -ne 0) { throw 'SUMO network setup failed.' }
& .\sumo_env\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Verification failed.' }
Write-Host 'Ready. Run: .\sumo_env\Scripts\python.exe main.py run --scenario demo --gui'
