@echo off
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "C:\Users\vivek\Documents\Codex\2026-10-15\new-chat\SUMO_KARS\Apply_Driver_Update.ps1"
if errorlevel 1 (
    echo Update stopped. Share the message above.
    pause
    exit /b 1
)
cd /d "C:\Users\vivek\SUMO_KARS"
"%LocalAppData%\Programs\Python\Python312\python.exe" main.py serve --port 8766
if errorlevel 1 pause
