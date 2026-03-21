@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   NanoPD 2.0 Setup (UV Environment)
echo ==========================================
echo [NOTE] This will set up a Python 3.11 environment in the .venv folder.
echo [NOTE] Using astral-uv for faster and complete environment management.
echo.

:: 1. Check for uv
echo [*] Checking for uv...
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Installing uv via PowerShell...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    if !errorlevel! neq 0 (
        echo [X] Failed to install uv. Please install it manually from https://astral.sh/uv/
        pause
        exit /b 1
    )
)

:: 2. Create Virtual Environment
echo [*] Creating virtual environment with Python 3.11...
uv venv --python 3.11
if !errorlevel! neq 0 (
    echo [X] Failed to create virtual environment.
    pause
    exit /b 1
)

:: 3. Install Dependencies
echo [*] Installing dependencies from requirements.txt...
uv pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [X] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   SETUP COMPLETE!
echo ==========================================
echo.
echo To start the app, double-click 'run.bat'.
echo.
pause
