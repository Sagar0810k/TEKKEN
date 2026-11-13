@echo off
title TTT2 Local Lounge - Setup
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
  echo Python is not installed yet.
  echo Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" in the installer, then run this again.
  pause
  exit /b 1
)
echo Installing libraries (one time)...
python -m pip install -r requirements.txt
echo.
echo Done. Next: install the ViGEm driver once (see START_HERE.txt),
echo set your game path in settings.json, then double-click start_server.bat
pause
