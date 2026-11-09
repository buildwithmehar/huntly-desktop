@echo off
setlocal
title Huntly
cd /d "%~dp0"
set "HUNTLY_PYTHON=.venv\Scripts\python.exe"

if exist "%HUNTLY_PYTHON%" goto check
echo Setting up Huntly. This takes a few minutes the first time.
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 (
  py -3 -m venv .venv
  if errorlevel 1 goto failed
  goto install
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto no_python
python -m venv .venv
if errorlevel 1 goto failed
goto install

:check
"%HUNTLY_PYTHON%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto broken_environment
"%HUNTLY_PYTHON%" -c "from importlib.metadata import version; version('huntly'); import aiosqlite, fastapi, uvicorn" >nul 2>&1
if not errorlevel 1 goto launch

:install
"%HUNTLY_PYTHON%" -m pip install --disable-pip-version-check -e .
if errorlevel 1 goto failed

:launch
"%HUNTLY_PYTHON%" -m huntly dashboard --open
if errorlevel 1 goto failed
exit /b 0

:no_python
echo Install Python 3.11 or newer from https://www.python.org/downloads/windows/.
echo Then double-click Open Huntly again.
pause
exit /b 1

:broken_environment
echo The .venv folder came from a different Python installation.
echo Rename .venv to .venv-old, then double-click Open Huntly again.
pause
exit /b 1

:failed
echo.
echo Huntly could not open. The error above explains what needs attention.
pause
exit /b 1
