@echo off
REM Smart Home Safety System - Setup Only (no server start)

echo ================================================
echo Smart Home Safety System - Setup
echo ================================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install the latest version of Python from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Python found:
python --version
echo.

REM Create virtual environment
if not exist ".venv\" (
    echo [2/4] Creating virtual environment...
    python -m venv .venv
    echo Virtual environment created!
) else (
    echo [2/4] Virtual environment already exists
)
echo.

REM Activate and install
echo [3/4] Installing dependencies...
call .venv\Scripts\activate.bat
pip install -r backend\requirements.txt
echo.

REM Generate certificates
echo [4/4] Checking SSL certificates...
if not exist "cert.pem" (
    echo Generating self-signed certificates...
    python tools\make_selfsigned_cert.py
    echo Certificates created!
) else (
    echo Certificates already exist
)
echo.

echo ================================================
echo Setup Complete
echo. 
echo Run the program using the following commands:
echo   - .venv\Scripts\activate.bat  (Activate virtual environment)
echo   - python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem (Launch Backend Server)
echo   - python frontend\serve_https.py (Launch Frontend Server)
echo Or run:
echo   - start.bat
echo ================================================
echo.
pause
