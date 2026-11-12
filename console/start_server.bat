@echo off
title TTT2 Local Console Server
cd /d "%~dp0"
rem open the operator dashboard on this laptop once the server is up
start "" /min cmd /c "timeout /t 3 >nul & start http://localhost:8000/"
python server.py
pause
