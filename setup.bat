@echo off
:: Do not close immediately on error to allow reading error messages
if not defined DEBUG_MODE (
    set DEBUG_MODE=1
)

echo ==========================================
echo   NanoPD 2.0 Setup (Debug Mode)
echo ==========================================
[cite: 1, 6]

:: 1. Check and install uv
echo [*] Checking for uv...
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Installing uv via PowerShell... [cite: 3]
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    
    :: Manually sync path, use %USERPROFILE% to ensure compatibility [cite: 3]
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
) else (
    echo [*] uv is already installed.
)

:: Verify if uv is available
uv --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [X] Error: uv was installed but the system still cannot find it.
    echo Please try to run manually: set Path=%%USERPROFILE%%\.local\bin;%%Path%%
    pause
    exit /b 1
)

:: 2. Create virtual environment
echo [*] Creating virtual environment with Python 3.11... [cite: 4]
uv venv --python 3.11
if %errorlevel% neq 0 (
    echo [X] Failed to create virtual environment.
    pause
    exit /b 1
)

:: 3. Install dependencies
echo [*] Installing dependencies from requirements.txt... [cite: 5]
uv pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [X] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   SETUP COMPLETE!
echo ==========================================
echo.
pause