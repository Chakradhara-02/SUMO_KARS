@echo off
cd /d "%~dp0"
set "KARS_PYTHON=%LocalAppData%\Programs\Python\Python312\python.exe"
if exist "sumo_env\Scripts\python.exe" set "KARS_PYTHON=%~dp0sumo_env\Scripts\python.exe"
if not exist "%KARS_PYTHON%" set "KARS_PYTHON=python"
"%KARS_PYTHON%" launch_city.py
if errorlevel 1 pause
