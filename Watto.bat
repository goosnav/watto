@echo off
rem Watto launcher for Windows -- double-click me.
cd /d "%~dp0"
where python >nul 2>nul || (echo Watto needs Python 3 - install it from python.org & pause & exit /b 1)
python server.py --open
if errorlevel 1 pause
