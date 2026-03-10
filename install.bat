@echo off
REM Tax Receipt Autopilot -- Windows Installer
REM Run once to install Python dependencies for bank statement parsing.
REM Usage: Double-click install.bat, or run from Command Prompt

setlocal EnableDelayedExpansion

echo.
echo Tax Receipt Autopilot -- Setup
echo ==============================
echo.

REM --- Find Python ---
set PYTHON=
where python >nul 2>&1
if %ERRORLEVEL% == 0 (
    for /f "tokens=*" %%v in ('python -c "import sys; print(sys.version_info.major)" 2^>nul') do set PY_MAJOR=%%v
    if "!PY_MAJOR!" == "3" (
        set PYTHON=python
    )
)

if "!PYTHON!" == "" (
    where python3 >nul 2>&1
    if %ERRORLEVEL% == 0 (
        set PYTHON=python3
    )
)

if "!PYTHON!" == "" (
    where py >nul 2>&1
    if %ERRORLEVEL% == 0 (
        for /f "tokens=*" %%v in ('py -c "import sys; print(sys.version_info.major)" 2^>nul') do set PY_MAJOR=%%v
        if "!PY_MAJOR!" == "3" (
            set PYTHON=py
        )
    )
)

if "!PYTHON!" == "" (
    echo Python 3 not found.
    echo.
    echo Install it from: https://python.org/downloads
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    echo NOTE: Python is only needed for CSV/PDF bank statement parsing.
    echo You can use the skill without it -- just paste bank rows into Claude
    echo or submit receipt photos directly.
    echo.
    pause
    exit /b 0
)

for /f "tokens=*" %%v in ('!PYTHON! --version 2^>^&1') do echo Python found: %%v
echo.

REM --- Install dependencies ---
set SCRIPT_DIR=%~dp0
set REQUIREMENTS=%SCRIPT_DIR%scripts\requirements.txt
set VALIDATOR=%SCRIPT_DIR%scripts\setup_validator.py

REM Optional: for a cleaner isolated install, create a virtual environment first:
REM   python -m venv %USERPROFILE%\.tax-autopilot-venv
REM   %USERPROFILE%\.tax-autopilot-venv\Scripts\activate.bat
REM   install.bat
REM Then activate before each use: %USERPROFILE%\.tax-autopilot-venv\Scripts\activate.bat

echo Installing dependencies...
!PYTHON! -m pip install -r "%REQUIREMENTS%" --quiet --upgrade
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo pip install failed. Common fixes:
    echo   1. Run this window as Administrator and try again
    echo   2. Run manually: !PYTHON! -m pip install -r scripts\requirements.txt --user
    echo   3. Use a virtual environment (see venv note at top of this file)
    echo.
    pause
    exit /b 1
)

echo.
echo Dependencies installed.
echo.

REM --- Install optional speedup (requires C compiler -- fails gracefully) ---
echo Installing optional fuzzy matching speedup (python-Levenshtein)...
!PYTHON! -m pip install "python-Levenshtein>=0.12.0" --quiet >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Speedup installed -- fuzzy matching will be faster.
) else (
    echo Speedup skipped -- C compiler not available (this is fine).
    echo Fuzzy matching still works, just slightly slower without it.
)
echo.

REM --- Run validator ---
if exist "%VALIDATOR%" (
    echo Running setup check...
    echo.
    !PYTHON! "%VALIDATOR%"
) else (
    echo Validation skipped (validator not found).
)

echo.
pause
