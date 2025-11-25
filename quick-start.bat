@echo off
REM Smart Home Safety System - Quick Start (assumes already set up)
REM Use start.bat for first-time setup

echo ========================================
echo Quick Start - Smart Home Safety System
echo ========================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Virtual environment not found. Run start.bat first.
    pause
    exit /b 1
)

REM Start Backend
echo Starting Backend Server (Port 8000)...
start "Backend Server" cmd /k "cd /d %CD% && .venv\Scripts\activate.bat && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem"

REM Wait for backend
timeout /t 3 /nobreak >nul

REM Start Frontend
echo Starting Frontend Server (Port 3000)...
start "Frontend Server" cmd /k "cd /d %CD%\Front-End-User && python serve_https.py"

REM Wait for frontend
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo Servers Started!
echo ========================================
echo Backend:  https://127.0.0.1:8000
echo Frontend: https://127.0.0.1:3000
echo.
echo Opening dashboard...
timeout /t 2 /nobreak >nul
start https://127.0.0.1:3000

echo.
echo Press any key to exit (servers will keep running)...
pause >nul
