@echo off
REM Smart Home Safety System - Automated Setup and Start Script
REM This script will set up the environment and start both backend and frontend servers

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

echo [1/5] Checking Python installation...
python --version
echo.

REM Check if virtual environment exists
if not exist ".venv\" (
    echo [2/5] Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully!
) else (
    echo [2/5] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [3/5] Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated
echo.

REM Install/Update backend requirements
echo [4/5] Installing backend dependencies...
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
    echo [WARNING] SSL certificate not found
    echo Generating self-signed certificate...
    if exist "tools\make_selfsigned_cert.py" (
        python tools\make_selfsigned_cert.py
    ) else (
        echo [ERROR] Certificate generation script not found
        echo Please create cert.pem and key.pem manually
    )
)
echo.

REM Delete old database to ensure fresh start (optional - comment out if you want to keep data)
REM if exist "data.db" (
REM     echo Removing old database...
REM     del data.db
REM )

echo [5/5] Starting servers...
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
echo Servers Started Successfully!
echo ========================================
echo.
echo Backend:  https://127.0.0.1:8000
echo API Docs: https://127.0.0.1:8000/docs
echo Frontend: https://127.0.0.1:3000
echo.
echo Default Login Credentials:
echo   Username: admin
echo   Password: admin123
echo.
echo ========================================
echo Opening frontend in browser...
echo ========================================
timeout /t 2 /nobreak >nul
start https://127.0.0.1:3000

echo.
echo Press any key to open additional tools menu...
pause >nul

:MENU
cls
echo ========================================
echo Smart Home Safety System - Tools Menu
echo ========================================
echo.
echo 1. Open Frontend Dashboard
echo 2. Open Backend API Docs
echo 3. Open Simple Alert Creator
echo 4. Generate Random Events
echo 5. Run Break-in Scenario
echo 6. Run Fire Emergency Scenario
echo 7. View Running Processes
echo 8. Stop All Servers
echo 9. Exit
echo.
set /p choice="Enter your choice (1-9): "

if "%choice%"=="1" (
    start https://127.0.0.1:3000
    goto MENU
)
if "%choice%"=="2" (
    start https://127.0.0.1:8000/docs
    goto MENU
)
if "%choice%"=="3" (
    start https://127.0.0.1:8001/simple-alert.html
    goto MENU
)
if "%choice%"=="4" (
    .venv\Scripts\python.exe tools\simulate_events.py --random 5 --delay 2
    echo.
    pause
    goto MENU
)
if "%choice%"=="5" (
    .venv\Scripts\python.exe tools\simulate_events.py --scenario break_in
    echo.
    pause
    goto MENU
)
if "%choice%"=="6" (
    .venv\Scripts\python.exe tools\simulate_events.py --scenario fire_emergency
    echo.
    pause
    goto MENU
)
if "%choice%"=="7" (
    echo.
    echo Running Python processes:
    powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, StartTime | Format-Table -AutoSize"
    echo.
    pause
    goto MENU
)
if "%choice%"=="8" (
    echo Stopping all servers...
    taskkill /FI "WindowTitle eq Backend Server*" /T /F >nul 2>&1
    taskkill /FI "WindowTitle eq Frontend Server*" /T /F >nul 2>&1
    echo Servers stopped.
    echo.
    pause
    exit /b 0
)
if "%choice%"=="9" (
    echo.
    echo Servers are still running in background windows.
    echo To stop them, run this script again and choose option 8.
    echo.
    exit /b 0
)

echo Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto MENU
