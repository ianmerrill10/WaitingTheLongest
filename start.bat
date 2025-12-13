@echo off
REM ============================================================================
REM Waiting The Longest - Quick Start Script (Windows)
REM ============================================================================
REM Usage: Double-click this file or run from command prompt
REM ============================================================================

echo.
echo ============================================
echo  Waiting The Longest - Quick Start
echo ============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Navigate to script directory
cd /d "%~dp0"
cd ..

REM Check if venv exists
if not exist "backend\.venv" (
    echo Setting up development environment...
    python scripts\dev_setup.py
    if errorlevel 1 (
        echo Setup failed!
        pause
        exit /b 1
    )
)

REM Start the server
echo.
echo Starting development server...
echo Press Ctrl+C to stop
echo.
python scripts\run.py --open

pause
