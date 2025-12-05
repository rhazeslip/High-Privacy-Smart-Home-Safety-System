@echo off
echo ========================================
echo Smart Home Safety System - Startup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo Python version:
python --version
echo.

REM Check if virtual environment exists
if not exist ".venv\" (
    echo Creating virtual environment
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
) else (
    echo Virtual environment already exists
)
echo.

REM Activate virtual environment
echo Starting virtual environment
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start virtual environment
    pause
    exit /b 1
)
echo Virtual environment started
echo.

REM Install/Update backend requirements
echo Installing backend dependencies
if exist "backend\requirements.txt" (
    pip install -r backend\requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo [WARNING] Some packages may have failed to install
    ) else (
        echo Backend dependencies installed successfully!
    )
) else (
    echo [WARNING] backend\requirements.txt not found
)
echo.

REM Check if certificates exist
if not exist "cert.pem" (
    echo Generating self-signed certificate
    if exist "tools\make_selfsigned_cert.py" (
        python tools\make_selfsigned_cert.py
    ) else (
        echo [ERROR] Certificate generation script not found
        echo Please create cert.pem and key.pem manually
    )
) else (
    echo self-signed certificates found
)
echo.

echo Starting servers
echo.
echo ========================================
echo Starting Backend Server (Port 8000)
echo ========================================
start "Backend Server" cmd /k "cd /d %CD% && .venv\Scripts\activate.bat && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo Starting Frontend Server (Port 3000)
echo ========================================
start "Frontend Server" cmd /k "cd /d %CD%\Front-End-User && python serve_https.py"

REM Wait a moment for frontend to start
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo Servers Started Successfully
echo ========================================
echo.
echo Backend:  https://127.0.0.1:8000
echo API Docs: https://127.0.0.1:8000/docs
echo Frontend: https://127.0.0.1:3000
echo.
echo ========================================
echo Opening frontend in browser
echo ========================================
timeout /t 2 /nobreak >nul
start https://127.0.0.1:3000

echo.
echo Press any key to open menu
pause >nul

:MENU
cls
echo ========================================
echo.
echo 1. Open Frontend Dashboard
echo 2. Open Backend Status Page
echo 3. Open Backend API Docs
echo 4. View Running Processes
echo.
echo 9. Stop All Servers
echo 0. Exit
echo.
set /p choice="Enter your choice: "

if "%choice%"=="1" (
    start https://127.0.0.1:3000
    goto MENU
)
if "%choice%"=="2" (
    start https://127.0.0.1:8000/
    goto MENU
)
if "%choice%"=="3" (
    start https://127.0.0.1:8000/docs
    goto MENU
)
if "%choice%"=="4" (
    echo.
    echo Running Python processes:
    powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, StartTime | Format-Table -AutoSize"
    echo.
    pause
    goto MENU
)
if "%choice%"=="9" (
    echo Stopping all servers
    taskkill /FI "WindowTitle eq Backend Server*" /T /F >nul 2>&1
    taskkill /FI "WindowTitle eq Frontend Server*" /T /F >nul 2>&1
    echo Servers stopped.
    echo.
    pause
    exit /b 0
)
if "%choice%"=="0" (
    echo.
    echo Servers are still running in the background.
    echo To stop them, run stop.bat
    echo.
    exit /b 0
)

echo Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto MENU
