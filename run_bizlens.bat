@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher ^(py^) was not found. Install Python 3.13 and try again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating BizLens virtual environment with Python 3.13...
  py -3.13 -m venv .venv
  if errorlevel 1 (
    echo Could not create the Python 3.13 environment.
    echo Check that: py -0p shows Python 3.13.
    pause
    exit /b 1
  )
)

echo Checking BizLens dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed or was cancelled.
  echo Run this file again to retry.
  pause
  exit /b 1
)

echo Starting BizLens...
".venv\Scripts\python.exe" -m streamlit run app.py
endlocal
