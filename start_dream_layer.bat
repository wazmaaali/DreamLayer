@echo off
setlocal enabledelayedexpansion

:: Dream Layer Windows Startup Script
:: This script starts all the necessary services for the Dream Layer application on Windows

:: Colors for output (basic)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "NC=[0m"

echo.
echo %CYAN%================================================%NC%
echo %CYAN%       DREAM LAYER - WINDOWS STARTUP%NC%
echo %CYAN%================================================%NC%
echo.

:: Check if we're in the correct directory
if not exist "dream_layer_backend" (
    echo %RED%[ERROR]%NC% This script must be run from the Dream Layer project root directory!
    echo %RED%[ERROR]%NC% Please navigate to the dream_layer_v1 folder and try again.
    pause
    exit /b 1
)

:: Check for required tools
echo %BLUE%[INFO]%NC% Checking for required dependencies...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% Python not found! Please run install_windows_dependencies.bat first.
    pause
    exit /b 1
)

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% Node.js not found! Please run install_windows_dependencies.bat first.
    pause
    exit /b 1
)

echo %GREEN%[SUCCESS]%NC% All dependencies found!

:: Kill any existing processes on our ports
echo %BLUE%[INFO]%NC% Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8188') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5001') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5002') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5003') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5004') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080') do taskkill /f /pid %%a >nul 2>&1

:: Create logs directory
if not exist "logs" mkdir logs

:: Delete settings.json if it exists
if exist "dream_layer_backend\settings.json" (
    echo %YELLOW%[WARNING]%NC% Removing existing settings.json...
    del "dream_layer_backend\settings.json"
)

echo %CYAN%[STEP]%NC% Starting Dream Layer services...

:: Start Python servers in background
echo %BLUE%[INFO]%NC% Starting Dream Layer main server...
cd dream_layer_backend
start /b "" python dream_layer.py > "..\logs\dream_layer.log" 2>&1
cd ..

echo %BLUE%[INFO]%NC% Starting txt2img server...
cd dream_layer_backend
start /b "" python txt2img_server.py > "..\logs\txt2img_server.log" 2>&1
cd ..

echo %BLUE%[INFO]%NC% Starting img2img server...
cd dream_layer_backend
start /b "" python img2img_server.py > "..\logs\img2img_server.log" 2>&1
cd ..

echo %BLUE%[INFO]%NC% Starting extras server...
cd dream_layer_backend
start /b "" python extras.py > "..\logs\extras.log" 2>&1
cd ..

:: Wait for backend services to start
echo %BLUE%[INFO]%NC% Waiting for backend services to start...
timeout /t 10 /nobreak >nul

:: Start frontend
echo %BLUE%[INFO]%NC% Starting frontend development server...
cd dream_layer_frontend
start /b "" npm run dev > "..\logs\frontend.log" 2>&1
cd ..

:: Wait for frontend to start
echo %BLUE%[INFO]%NC% Waiting for frontend to start...
timeout /t 5 /nobreak >nul

echo.
echo %GREEN%================================================%NC%
echo %GREEN%    ALL SERVICES STARTED SUCCESSFULLY!%NC%
echo %GREEN%================================================%NC%
echo.
echo %CYAN%Services running:%NC%
echo   - Dream Layer (main): %BLUE%http://localhost:5002%NC%
echo   - txt2img server: %BLUE%http://localhost:5001%NC%
echo   - img2img server: %BLUE%http://localhost:5004%NC%
echo   - Extras server: %BLUE%http://localhost:5003%NC%
echo   - Frontend: %BLUE%http://localhost:8080%NC%
echo   - ComfyUI: %BLUE%http://localhost:8188%NC%
echo.
echo %YELLOW%[INFO]%NC% Opening Dream Layer in your default browser...
timeout /t 3 /nobreak >nul

:: Try to open in browser
start http://localhost:8080

echo.
echo %GREEN%Dream Layer is now running! 🎨✨%NC%
echo.
echo %YELLOW%[INFO]%NC% Log files are available in the 'logs' directory
echo %YELLOW%[INFO]%NC% Press Ctrl+C or close this window to stop all services
echo %YELLOW%[INFO]%NC% To stop manually, close this window or run: taskkill /f /im python.exe /im node.exe
echo.

:: Keep the window open
pause 