@echo off
REM Quick test script for setup wizard
REM This will reset the database and restart the system

echo ========================================
echo Setup Wizard Test
echo ========================================
echo.
echo This script will:
echo 1. Delete the existing database (data.db)
echo 2. Start the backend server
echo 3. You can then test the setup wizard
echo.

set /p confirm="Do you want to delete the database and test setup? (y/n): "
if /i not "%confirm%"=="y" (
    echo Cancelled.
    exit /b
)

echo.
echo Deleting database...
if exist "backend\data.db" (
    del "backend\data.db"
    echo Database deleted.
) else (
    echo No database found - will create new one.
)

echo.
echo ========================================
echo Starting backend server...
echo ========================================
echo.
echo The setup wizard should appear when you open:
echo https://localhost:3000
echo.
echo Press Ctrl+C to stop the server when done testing.
echo.

REM Activate virtual environment if exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Start backend
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
