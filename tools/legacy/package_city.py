from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
target = Path(r'C:\Users\vivek\SUMO_KARS')
files = ['kars/city.py', 'kars/city_routing.py', 'kars/city_safety.py',
         'kars/city_reachability.py', 'kars/models.py', 'kars/simulation.py',
         'simulation_ui/motion.js', 'simulation_ui/scene3d.js', 'simulation_ui/app.js',
         'simulation_ui/app.bundle.js', 'simulation_ui/index.html', 'tests/test_city.py',
         'tests/test_city_reachability.py', 'tests/test_metro_routes.py', 'tests/motion.test.mjs','simulation_ui/driver-assist.js','simulation_ui/vehicle-wheels.js','simulation_ui/road-surface.js','simulation_ui/style.css','tests/driver_ux.test.mjs','kars/console.py']
items = []
for name in files:
    original = target / name
    items.append({'path': name,
                  'expected': hashlib.sha256(original.read_bytes()).hexdigest() if original.exists() else None,
                  'updated': hashlib.sha256((root/name).read_bytes()).hexdigest()})
ps = r'''$ErrorActionPreference = 'Stop'
$source = 'SOURCEPATH'
$target = 'C:\Users\vivek\SUMO_KARS'
$items = @'
PAYLOAD
'@ | ConvertFrom-Json
foreach ($item in $items) {
    $destination = Join-Path $target $item.path
    if (Test-Path -LiteralPath $destination) {
        $hash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
        if ($hash -ne $item.updated -and $hash -ne $item.expected) {
            throw ('File edited since preparation: ' + $item.path + '. No files changed; ask ChatGPT to merge it.')
        }
    } elseif ($item.expected) { throw ('Missing file: ' + $item.path) }
    if ((Get-FileHash -LiteralPath (Join-Path $source $item.path) -Algorithm SHA256).Hash -ne $item.updated) {
        throw ('Prepared file changed: ' + $item.path)
    }
}
$backup = 'C:\Users\vivek\SUMO_KARS_city_backup_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
foreach ($item in $items) {
    $destination = Join-Path $target $item.path
    if (Test-Path -LiteralPath $destination) {
        $saved = Join-Path $backup $item.path
        New-Item -ItemType Directory -Path (Split-Path $saved) -Force | Out-Null
        Copy-Item -LiteralPath $destination -Destination $saved
    }
    New-Item -ItemType Directory -Path (Split-Path $destination) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $source $item.path) -Destination $destination -Force
}
Write-Host 'City update applied. No commit or push was performed.' -ForegroundColor Green
Write-Host ('Backup: ' + $backup)
'''.replace('SOURCEPATH', str(root)).replace('PAYLOAD', json.dumps(items))
(root/'Apply_Driver_Update.ps1').write_text(ps, encoding='utf-8-sig')
cmd = r'''@echo off
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "SCRIPTFILE"
if errorlevel 1 (
    echo Update stopped. Share the message above.
    pause
    exit /b 1
)
cd /d "C:\Users\vivek\SUMO_KARS"
"%LocalAppData%\Programs\Python\Python312\python.exe" main.py serve --port 8766
if errorlevel 1 pause
'''.replace('SCRIPTFILE', str(root/'Apply_Driver_Update.ps1'))
(root/'Install_Driver_Update.cmd').write_text(cmd, encoding='ascii')
print('Installer ready:', root/'Install_Driver_Update.cmd')
