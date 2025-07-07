@echo off
setlocal enabledelayedexpansion

:: Dream Layer Windows Installation Launcher
:: This batch file automatically detects the best installation method and runs it

:: Set colors for output (if supported)
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "BLUE=%ESC%[94m"
set "PURPLE=%ESC%[95m"
set "CYAN=%ESC%[96m"
set "NC=%ESC%[0m"

:: ASCII Art Header
echo.
echo %PURPLE%================================================%NC%
echo %PURPLE%    DREAM LAYER - WINDOWS INSTALLATION%NC%
echo %PURPLE%================================================%NC%
echo.
echo %CYAN%Welcome to Dream Layer Windows Installation!%NC%
echo.
echo %YELLOW%This installer will set up all dependencies needed to run Dream Layer:%NC%
echo   ^• Python 3.8+ with required packages
echo   ^• Node.js 16+ with npm
echo   ^• System dependencies (Git, ffmpeg, etc.)
echo   ^• All project-specific dependencies
echo.

:: Check for administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[INFO]%NC% For best results, consider running as Administrator
    echo       Right-click this file and select "Run as administrator"
    echo.
    timeout /t 3 /nobreak >nul
)

:: Check Windows version
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
echo %BLUE%[INFO]%NC% Detected Windows version: %VERSION%

:: Check if we're in the correct directory
if not exist "dream_layer_backend" (
    echo %RED%[ERROR]%NC% This script must be run from the Dream Layer project root directory!
    echo %RED%[ERROR]%NC% Please navigate to the dream_layer_v1 folder and try again.
    echo.
    pause
    exit /b 1
)

:: Check if PowerShell 5.0+ is available
echo %BLUE%[INFO]%NC% Checking PowerShell availability...
powershell -Command "if ($PSVersionTable.PSVersion.Major -ge 5) { exit 0 } else { exit 1 }" >nul 2>&1

if %errorlevel% equ 0 (
    echo %GREEN%[SUCCESS]%NC% PowerShell 5.0+ detected - using advanced installer
    goto :use_powershell
) else (
    echo %YELLOW%[WARNING]%NC% PowerShell 5.0+ not available - using basic installer
    goto :use_basic
)

:use_powershell
echo %CYAN%[STEP]%NC% Starting PowerShell installation script...
echo.

:: Check if script exists
if not exist "install_windows_dependencies.ps1" (
    echo %RED%[ERROR]%NC% PowerShell script 'install_windows_dependencies.ps1' not found!
    goto :use_basic
)

:: Run PowerShell script with bypass execution policy
powershell -ExecutionPolicy Bypass -NoProfile -File "install_windows_dependencies.ps1"
set PS_EXIT_CODE=%errorlevel%

if %PS_EXIT_CODE% equ 0 (
    echo.
    echo %GREEN%[SUCCESS]%NC% PowerShell installation completed successfully!
    goto :installation_complete
) else (
    echo.
    echo %RED%[ERROR]%NC% PowerShell installation failed (Exit code: %PS_EXIT_CODE%)
    echo %YELLOW%[INFO]%NC% Falling back to basic installation method...
    goto :use_basic
)

:use_basic
echo %CYAN%[STEP]%NC% Using basic installation method...
echo.

:: Check for required tools
echo %BLUE%[INFO]%NC% Checking for basic requirements...

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[WARNING]%NC% Python not found! Please install Python 3.8+ from:
    echo              https://www.python.org/downloads/
    set MISSING_DEPS=1
)

:: Check for Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[WARNING]%NC% Node.js not found! Please install Node.js 16+ from:
    echo              https://nodejs.org/
    set MISSING_DEPS=1
)

:: Check for Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[WARNING]%NC% Git not found! Please install Git from:
    echo              https://git-scm.com/downloads
    set MISSING_DEPS=1
)

if defined MISSING_DEPS (
    echo.
    echo %RED%[ERROR]%NC% Missing required dependencies. Please install them manually and run this script again.
    echo %CYAN%[INFO]%NC% Or try running the PowerShell script directly: install_windows_dependencies.ps1
    goto :end_with_error
)

:: Basic installation steps
echo %GREEN%[SUCCESS]%NC% All basic requirements found!
echo.

echo %CYAN%[STEP]%NC% Installing Python dependencies...
if exist "dream_layer_backend\requirements.txt" (
    python -m pip install --upgrade pip
    python -m pip install -r dream_layer_backend\requirements.txt
    if %errorlevel% neq 0 (
        echo %RED%[ERROR]%NC% Failed to install backend dependencies
        goto :end_with_error
    )
    echo %GREEN%[SUCCESS]%NC% Backend dependencies installed
) else (
    echo %YELLOW%[WARNING]%NC% Backend requirements.txt not found
)

if exist "ComfyUI\requirements.txt" (
    python -m pip install -r ComfyUI\requirements.txt
    if %errorlevel% neq 0 (
        echo %RED%[ERROR]%NC% Failed to install ComfyUI dependencies
        goto :end_with_error
    )
    echo %GREEN%[SUCCESS]%NC% ComfyUI dependencies installed
) else (
    echo %YELLOW%[WARNING]%NC% ComfyUI requirements.txt not found
)

echo %CYAN%[STEP]%NC% Installing frontend dependencies...
if exist "dream_layer_frontend\package.json" (
    cd dream_layer_frontend
    call npm install
    if %errorlevel% neq 0 (
        echo %RED%[ERROR]%NC% Failed to install frontend dependencies
        cd ..
        goto :end_with_error
    )
    cd ..
    echo %GREEN%[SUCCESS]%NC% Frontend dependencies installed
) else (
    echo %YELLOW%[WARNING]%NC% Frontend package.json not found
)

echo %CYAN%[STEP]%NC% Setting up environment...
if not exist "logs" mkdir logs
if not exist "dream_layer_backend\input" mkdir dream_layer_backend\input
if not exist "dream_layer_backend\served_images" mkdir dream_layer_backend\served_images

echo %GREEN%[SUCCESS]%NC% Basic installation completed!

:installation_complete
echo.
echo %GREEN%================================================%NC%
echo %GREEN%    INSTALLATION COMPLETE!%NC%
echo %GREEN%================================================%NC%
echo.
echo %CYAN%Next steps:%NC%
echo   1. %YELLOW%Configure your environment:%NC%
echo      • Edit %BLUE%dream_layer_backend\.env%NC% with your API keys
echo.
echo   2. %YELLOW%Start the application:%NC%
echo      • Run: %BLUE%start_dream_layer.bat%NC% (when available)
echo      • Or manually: %BLUE%start_dream_layer.sh%NC% (requires Git Bash/WSL)
echo.
echo   3. %YELLOW%Access the application:%NC%
echo      • Frontend: %BLUE%http://localhost:8080%NC%
echo      • Main API: %BLUE%http://localhost:5002%NC%
echo      • ComfyUI: %BLUE%http://localhost:8188%NC%
echo.
echo %GREEN%Happy creating with Dream Layer! 🎨✨%NC%
echo.
pause
exit /b 0

:end_with_error
echo.
echo %RED%[ERROR]%NC% Installation failed. Please check the errors above and try again.
echo %CYAN%[INFO]%NC% You can also try installing dependencies manually:
echo.
echo %YELLOW%Manual installation steps:%NC%
echo   1. Install Python 3.8+: https://www.python.org/downloads/
echo   2. Install Node.js 16+: https://nodejs.org/
echo   3. Install Git: https://git-scm.com/downloads
echo   4. Run: python -m pip install -r dream_layer_backend\requirements.txt
echo   5. Run: python -m pip install -r ComfyUI\requirements.txt
echo   6. Run: cd dream_layer_frontend ^&^& npm install
echo.
pause
exit /b 1 