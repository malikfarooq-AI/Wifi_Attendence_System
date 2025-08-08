@echo off
echo ========================================
echo WiFi Attendance Tracker Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.6+ from https://python.org
    pause
    exit /b 1
)

echo Python found. Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Setup completed successfully!
echo.
echo To run the application:
echo   1. Right-click Command Prompt and select "Run as Administrator"
echo   2. Navigate to this folder
echo   3. Run: python main.py
echo.
echo The web interface will be available at: http://localhost:5000
echo.
pause

