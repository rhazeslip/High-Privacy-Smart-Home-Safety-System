@echo off
REM Smart Home Safety System - Setup Only (no server start)

echo ================================================
echo Smart Home Safety System - Setup
echo ================================================
echo.

REM Check python installation
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] py is not installed or not in PATH
    echo Please install the latest version of py from https://www.py.org/
    pause
    exit /b 1
)

echo py version:
py --version
echo.

REM Create virtual environment
if not exist ".venv\" (
    echo Creating virtual environment
    py -m venv .venv
    echo Virtual environment created!
) else (
    echo Virtual environment already exists
)
echo.

REM Activate and install
echo Installing dependencies
call .venv\Scripts\activate.bat
pip install -r backend\requirements.txt
echo.

REM Generate certificates
echo Checking SSL certificates
if not exist "cert.pem" (
    echo Generating self-signed certificates
    py tools\make_selfsigned_cert.py
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
echo   - py -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem (Launch Backend Server)
echo   - py frontend\serve_https.py (Launch Frontend Server)
echo Or run:
echo   - start.bat
echo ================================================
echo.
pause
