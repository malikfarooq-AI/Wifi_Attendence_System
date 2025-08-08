@echo off
echo ========================================
echo WiFi Attendance Tracker
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This application must be run as Administrator
    echo.
    echo Please:
    echo   1. Right-click Command Prompt
    echo   2. Select "Run as Administrator"
    echo   3. Navigate to this folder
    echo   4. Run this script again
    echo.
    pause
    exit /b 1
)

echo Starting WiFi Attendance Tracker...
echo Web interface will be available at: http://localhost:5000
echo Press Ctrl+C to stop
echo.

python main.py

pause

