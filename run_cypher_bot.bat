@echo off
rem ======================================================================
rem Cypher Bot Premium Interactive Windows Launcher
rem Coordinates automatic virtual env activation, concurrent processes,
rem pip dependencies installations, and clean shutdown targets.
rem ======================================================================
title Cypher Bot Premium Console Launcher
color 0B

rem Explicitly set project root directory into Python search path to guarantee absolute imports reliability
set PYTHONPATH=%~dp0

:menu
cls
echo ======================================================================
echo **********************************************************************
echo **                                                                  **
echo **                      CYPHER BOT SYSTEM MENU                      **
echo **                                                                  **
echo **********************************************************************
echo ======================================================================
echo                  CYPHER BOT :: SYSTEM LAUNCHER
echo ======================================================================
echo.
echo [1] Run Bot and Export Worker (Concurrent Windows)
echo [2] Run Bot Only (Main runner + Webhook Web-Server)
echo [3] Run Background Export Worker Only
echo [4] Install / Update Dependencies (requirements.txt)
echo [5] Exit
echo.
echo ======================================================================
set /p opt="Choose an option [1-5]: "

rem Routing menu choice actions
if "%opt%"=="1" goto launch_all
if "%opt%"=="2" goto launch_bot
if "%opt%"=="3" goto launch_worker
if "%opt%"=="4" goto install_deps
if "%opt%"=="5" goto exit_app
goto menu

rem ======================================================================
rem Helper: Detects and activates standard Python virtual environments (.venv/venv/env)
rem ======================================================================
:detect_venv
echo.
echo [*] Scanning for active Python Virtual Environments...
if exist .venv\Scripts\activate.bat (
    echo [+] Found active environment in .venv
    call .venv\Scripts\activate.bat
    goto :eof
)
if exist venv\Scripts\activate.bat (
    echo [+] Found active environment in venv
    call venv\Scripts\activate.bat
    goto :eof
)
if exist env\Scripts\activate.bat (
    echo [+] Found active environment in env
    call env\Scripts\activate.bat
    goto :eof
)
echo [-] No virtual environment detected. Operating with system Python interpreter.
goto :eof

rem ======================================================================
rem Action 1: Concurrent startup of BOTH the Telegram Bot (main.py) and Worker (worker.py)
rem Launches the worker in a separate, colorful CMD terminal window with dedicated logging
rem ======================================================================
:launch_all
cls
echo ======================================================================
echo   Launching Cypher Bot and Background Worker in Concurrent Mode
echo ======================================================================
call :detect_venv
echo.
echo [+] Starting Background Export Worker in a separate terminal...
rem Launches worker.py inside a newly spawned CMD process, preserving logs in its own window
start "Cypher Bot Background Export Worker" cmd /c "title Cypher Worker && color 0E && python bot/worker.py"
echo [+] Launching Telegram Bot and Webhook Server on port 8080...
echo.
python bot/main.py
pause
goto menu

rem ======================================================================
rem Action 2: Starts ONLY the Telegram Bot interface and AIOHTTP Webhook endpoint
rem ======================================================================
:launch_bot
cls
echo ======================================================================
echo   Launching Telegram Bot and Webhook Server Only
echo ======================================================================
call :detect_venv
echo.
python bot/main.py
pause
goto menu

rem ======================================================================
rem Action 3: Starts ONLY the Redis background export worker task
rem ======================================================================
:launch_worker
cls
echo ======================================================================
echo   Launching Background Export Task Worker Only
echo ======================================================================
call :detect_venv
echo.
python bot/worker.py
pause
goto menu

rem ======================================================================
rem Action 4: Updates package installer (pip) and installs workspace dependencies
rem ======================================================================
:install_deps
cls
echo ======================================================================
echo   Installing Dependencies from requirements.txt
echo ======================================================================
call :detect_venv
echo.
echo [+] Upgrading pip to latest version...
python -m pip install --upgrade pip
echo [+] Fetching required packages...
pip install -r requirements.txt
echo.
echo [+] Installation completed successfully!
pause
goto menu

rem ======================================================================
rem Action 5: Standard exit target
rem ======================================================================
:exit_app
cls
echo Thank you for using Cypher Bot. Keep it secure!
timeout /t 3 >nul
exit
