$ErrorActionPreference = 'Stop'
$source = 'C:\Users\vivek\Documents\Codex\2026-10-15\new-chat\SUMO_KARS'
$target = 'C:\Users\vivek\SUMO_KARS'
$items = @'
[{"path": "kars/city.py", "expected": "d494d9636cee222b4290b084164fbfa0951bec952680925fc0944b8e55a3bec1", "updated": "99419def55d32c5c1b9f986827fc297d6cee90d253ea1a8cbe042e51ba7efec4"}, {"path": "kars/city_routing.py", "expected": null, "updated": "ea308319955d83ae726e2662d5d403b3027a267c37eccb20b5c3742280677cb5"}, {"path": "kars/city_safety.py", "expected": null, "updated": "e45d7073fa5b8d7e2f17fa9f735adc1d2cf75d23280af4eea941c006cae145ba"}, {"path": "kars/city_reachability.py", "expected": "03626be02c5de1524b13ab0275b79ef980cc4570a0581195d8c7bafaacb34f00", "updated": "d642796582cdd93ab7b5f2d5292e0890199d00940c67f24bccece9b1580a2dc5"}, {"path": "kars/models.py", "expected": "681532e8c8ea470e270f2014fce521b9095b48772512f0aa2d99c473cbef0805", "updated": "b688e96cc2b89ad1b2d9ce5ced241797df566ad28e21403c2e920f2461245ee0"}, {"path": "kars/simulation.py", "expected": "446ff65d3d59884db436eebeeb7fe56db6aa9ca19375cc509853a5e4463888d3", "updated": "e29e83dc9d24c6950bef7c12f629a70de497cfe965d3ff8213a1b593ec4d6b29"}, {"path": "simulation_ui/motion.js", "expected": "60b5992ab0699cba31b3a57e68ef779184b4166c34501bc2131374b653ccb752", "updated": "e501dad17467b3b355c08ce40519fd6ed4cef1f18d15c96455dad5f9046879fb"}, {"path": "simulation_ui/scene3d.js", "expected": "e8de6702496f7f516034ce80d1d2b3c83ce1f6609241b1165058406cdbec020a", "updated": "46ef1d4122492b015459f125a1e915156966b8e72fcdc2a1590425f5480b79f7"}, {"path": "simulation_ui/app.js", "expected": "ebc6b9c34cacb5ed08910140bfa429e680752627473ea3d3cbd60c5fd0c569b6", "updated": "ec6b8b618d2f9966f3452978a116661a972cfeaf948bffe5c8ed1aa05a6ed654"}, {"path": "simulation_ui/app.bundle.js", "expected": "c99f4e90b1aee44d4f13149bff729421c54f75655d19fb74b11013ed18f01278", "updated": "8418ae6b5614f4c9dc8cbf689f432f3b62be0a85b3465ece6fc4d52aad565125"}, {"path": "simulation_ui/index.html", "expected": "cd8406e095696d1637b4686dd570a657d10daa2e8af694eeb127caa0078f032c", "updated": "3befa288f3a3efbcabf8d98a74bc8fec91751c56203ddf19d315c1027258e520"}, {"path": "tests/test_city.py", "expected": "be4f9d1e902903102c4e03af1b2a64f454e56bd82f612bfd2fc6a3aff9a9fc9f", "updated": "b363d08585d054224ddda3e8e648cabf281a7f7de7f3a9db35cbf6eb3f52dba5"}, {"path": "tests/test_city_reachability.py", "expected": "862f01bdaa027f0d74980420a19bfef7f450f909b9cd67a63b0c1b6681f4529d", "updated": "f3910f011f5fb6c55048cdde94c846307fcd978cf5e26a5d271edeeb6d6f45ae"}, {"path": "tests/test_metro_routes.py", "expected": null, "updated": "f7c2acfb015bbf0f0d45e2aedcac4f3296d15229de99a5862e55ab13e43d3e1b"}, {"path": "tests/motion.test.mjs", "expected": "7cb4a881a7b95620f66220c23ea86fa88c715fa04530eda81e4da5bcb29b1318", "updated": "b15267b70e52b05d67c4490cfa3f173e5524390c9860697ac94fec2028fc18c6"}]
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
