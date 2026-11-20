@echo off
rem Double-click to run the eshop on this PC.
rem First run: creates venv and installs requirements.txt (again whenever that file changes).
rem Then serves the shop at http://localhost:8000, or on a public address through Cloudflare.
setlocal
cd /d "%~dp0"
title eShop

rem ---- Python 3.10 or newer (the py launcher first, then python on PATH)
set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1 && set "PY=python"
if not defined PY (
    echo Python 3.10 or newer is needed. Get it from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during the install.
    pause
    exit /b 1
)

rem ---- Virtual environment
if not exist venv\Scripts\python.exe (
    echo Creating the virtual environment...
    %PY% -m venv venv || goto :failed
)

rem ---- Dependencies, only when requirements.txt changed since the last install
fc /b requirements.txt venv\requirements.installed >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    venv\Scripts\python -m pip install --disable-pip-version-check -q -r requirements.txt || goto :failed
    copy /y requirements.txt venv\requirements.installed >nul
)

rem ---- Local or public
echo.
choice /c LP /n /m "Run [L]ocally or make it [P]ublic on the internet? "
if errorlevel 2 goto :public

echo.
echo The shop is at http://localhost:8000  -  close this window to stop it.
start "" cmd /c "timeout /t 2 >nul & start http://localhost:8000"
venv\Scripts\waitress-serve --listen=127.0.0.1:8000 --call eshop:create_app
goto :end

:public
echo.
echo Starting the public tunnel; look for the https://....trycloudflare.com address below.
echo Close this window to take the site offline.
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\start_public.ps1
goto :end

:failed
echo.
echo Setup failed - see the messages above.

:end
pause
