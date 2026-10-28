@echo off
cd /d "%~dp0"
set "PYTHONDONTWRITEBYTECODE=1"
if exist "sumo_env\Scripts\python.exe" (
    set "KARS_PYTHON=sumo_env\Scripts\python.exe"
) else (
    set "KARS_PYTHON=C:\Users\vivek\AppData\Local\Programs\Python\Python312\python.exe"
)
"%KARS_PYTHON%" main.py setup
if errorlevel 1 (
    echo Setup failed. Please share the error above.
    pause
    exit /b 1
)
"%KARS_PYTHON%" main.py serve
if errorlevel 1 pause
