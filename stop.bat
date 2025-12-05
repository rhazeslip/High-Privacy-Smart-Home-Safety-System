@echo off
REM Smart Home Safety System - Stop All Servers

echo ========================================
echo Stop Smart Home Safety System
echo ========================================
echo.

echo Stopping Backend Server
taskkill /FI "WindowTitle eq Backend Server*" /T /F >nul 2>&1
if %errorlevel% equ 0 (
    echo Backend server stopped
) else (
    echo No backend server found running
)

echo Stopping Frontend Server
taskkill /FI "WindowTitle eq Frontend Server*" /T /F >nul 2>&1
if %errorlevel% equ 0 (
    echo Frontend server stopped
) else (
    echo No frontend server found running
)


echo.
echo Finished
echo.
pause
