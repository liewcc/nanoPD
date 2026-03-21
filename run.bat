@echo off
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [!] Environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

cls
echo +-------------------------------------------------------------+
echo ^|                                                             ^|
echo ^|           _   _    _    _   _  ___  ____  ____              ^|
echo ^|          ^| \ ^| ^|  / \  ^| \ ^| ^|/ _ \^|  _ \^|  _ \             ^|
echo ^|          ^|  \^| ^| / _ \ ^|  \^| ^| ^| ^| ^| ^|_) ^| ^| ^| ^|            ^|
echo ^|          ^| ^|\  ^|/ ___ \^| ^|\  ^| ^|_^| ^|  __/^| ^|_^| ^|            ^|
echo ^|          ^|_^| \_/_/   \_\_^| \_^|\___/^|_^|   ^|____/             ^|
echo ^|                                                             ^|
echo ^|                       NANOPD 2.0                            ^|
echo ^|                                                             ^|
echo +-------------------------------------------------------------+
"%PYTHON_EXE%" -m streamlit run main.py

echo.
echo ==========================================
echo   Application has closed.
echo ==========================================
pause
