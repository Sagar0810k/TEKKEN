@echo off
title TTT2 Local Lounge - Automatic Setup
cd /d "%~dp0"
setlocal

echo.
echo  ============================================
echo   TTT2 LOCAL LOUNGE - AUTOMATIC SETUP
echo   (libraries + controller driver + game path)
echo  ============================================
echo.

rem ---------------------------------------------------------------------
rem STEP 1: Python
rem ---------------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 goto python_missing
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [1/5] %%v found
goto pip_step

:python_missing
echo  [1/5] PYTHON IS NOT INSTALLED.
echo.
echo        Opening the Python download page now...
echo        IMPORTANT: in the installer, tick "Add python.exe to PATH",
echo        then click Install Now. When it finishes, run this file again.
start "" https://www.python.org/downloads/
pause
exit /b 1

rem ---------------------------------------------------------------------
rem STEP 2: Python libraries
rem ---------------------------------------------------------------------
:pip_step
echo  [2/5] Installing Python libraries (fastapi, uvicorn, qrcode, vgamepad)...
python -m pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
  echo        ERROR: pip install failed - check your internet once and rerun.
  python -m pip install -r requirements.txt
  pause
  exit /b 1
)
echo        done.

rem ---------------------------------------------------------------------
rem STEP 3: ViGEm Bus driver (the virtual controllers)
rem ---------------------------------------------------------------------
sc query ViGEmBus >nul 2>&1
if errorlevel 1 goto install_driver
echo  [3/5] ViGEm Bus driver already installed.
goto game_step

:install_driver
echo  [3/5] ViGEm Bus driver missing - downloading it (about 4 MB)...
set "DRIVER_EXE=%TEMP%\ViGEmBusSetup_x64.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/ViGEm/ViGEmBus/releases/download/ViGEmBus_v1.22.0/ViGEmBusSetup_x64.exe' -OutFile $env:DRIVER_EXE -UseBasicParsing"
if not exist "%DRIVER_EXE%" (
  echo        ERROR: download failed. Install it by hand from:
  echo        https://github.com/ViGEm/ViGEmBus/releases
  echo        Then run this file again.
  pause
  exit /b 1
)
echo        Installing the driver - Windows may ask for permission (YES).
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath $env:DRIVER_EXE -ArgumentList '/VERYSILENT /NORESTART' -Verb RunAs -Wait" >nul 2>&1
sc query ViGEmBus >nul 2>&1
if errorlevel 1 (
  echo        The driver was not detected yet.
  echo        If you clicked "No" on the Windows permission box, run the
  echo        installer manually:  %DRIVER_EXE%
  echo        Then run this file again.
  pause
  exit /b 1
)
echo        driver installed.

rem ---------------------------------------------------------------------
rem STEP 4: game exe path
rem ---------------------------------------------------------------------
:game_step
python -c "import json,sys; sys.exit(1 if not json.load(open('settings.json')).get('game_exe') else 0)" >nul 2>&1
if errorlevel 1 goto ask_game
echo  [4/5] Game path already set in settings.json.
goto verify

:ask_game
echo  [4/5] Now tell it where your game is.
echo        DRAG your Tekken Tag Tournament 2 .exe file into this window
echo        and press Enter.
echo        (No game installed yet? Type S and press Enter - run this
echo         file again after the game is built.)
set "GAMEEXE="
set /p GAMEEXE=
if not defined GAMEEXE goto ask_game
if /i "%GAMEEXE%"=="S" goto game_skip
if /i "%GAMEEXE%"=="s" goto game_skip
set GAMEEXE=%GAMEEXE:"=%
if not exist "%GAMEEXE%" (
  echo        That file does not exist - try again.
  goto ask_game
)
python -c "import json,os; json.dump({'game_exe': os.environ['GAMEEXE']}, open('settings.json','w'), indent=2)"
echo        saved to settings.json.
goto verify

:game_skip
echo        Skipped - remember to run INSTALL.bat again after the game
echo        is installed, so it can save the game path.

rem ---------------------------------------------------------------------
rem STEP 5: verification
rem ---------------------------------------------------------------------
:verify
echo  [5/5] Checking everything...
python -c "import fastapi, uvicorn, qrcode, vgamepad" >nul 2>&1
if errorlevel 1 (
  echo        ERROR: a library is still missing - rerun this file.
  pause
  exit /b 1
)
echo        libraries OK, driver OK.
echo.
echo  ============================================
echo   SETUP COMPLETE!
echo   Next: double-click start_server.bat
echo   (first run: send the fingerprint shown on the
echo    dashboard to your seller, enter the key)
echo  ============================================
echo.
pause
