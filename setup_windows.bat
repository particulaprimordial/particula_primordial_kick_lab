@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo PARTÍCULA PRIMORDIAL - KICK LABORATORY SETUP
echo ================================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found.
  echo Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/
  echo During installation, enable the Python Launcher and Add Python to PATH.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Creating local Python environment...
  py -3.12 -m venv .venv
  if errorlevel 1 py -3.11 -m venv .venv
  if errorlevel 1 goto :failed
)
call .venv\Scripts\activate.bat
echo Installing application dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
pip install -r requirements.txt
if errorlevel 1 goto :failed
echo.
echo Setup completed. Double-click run_dashboard.bat to open the app.
pause
exit /b 0
:failed
echo.
echo Setup failed. Check the Python installation and internet connection.
pause
exit /b 1
