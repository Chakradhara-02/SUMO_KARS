$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$env:RUNTIME_NODE_MODULES='C:\Users\velug\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:PATH='C:\Users\velug\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\override;C:\Users\velug\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback;'+$env:PATH
& 'C:\Users\velug\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' docs\build_presentation.mjs
if ($LASTEXITCODE -ne 0) { throw 'Presentation build failed.' }
