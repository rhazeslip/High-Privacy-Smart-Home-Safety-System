@echo off
REM Smart Home Safety System - Setup Only (no server start)

echo ========================================
echo Smart Home Safety System - Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
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

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo You can now run:
echo   - start.bat        (Full startup with menu)
echo   - quick-start.bat  (Quick server startup)
echo   - stop.bat         (Stop all servers)
echo.
pause
