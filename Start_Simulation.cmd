@echo off
cd /d "%~dp0"
"sumo_env\Scripts\python.exe" main.py serve
if errorlevel 1 pause
