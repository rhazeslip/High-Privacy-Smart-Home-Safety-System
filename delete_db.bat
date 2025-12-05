@echo off
REM Quick test script for setup wizard
REM This will reset the database and restart the system

echo ========================================
echo Delete Database
echo ========================================
echo.
echo Warning: This will delete all data
echo.

set /p confirm="Are you sure you want to delete database? (y/n): "
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
    echo No database found 
)