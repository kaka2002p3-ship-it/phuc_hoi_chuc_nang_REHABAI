@echo off
REM ============================================================
REM RehabAI Web Application Starter
REM ============================================================

echo.
echo ============================================================
echo  RehabAI - Starting Web Application
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.11+
    pause
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found! Please install Node.js 18+
    pause
    exit /b 1
)

echo [1/4] Setting up environment...
cd /d "%~dp0rehabai"
set PYTHONPATH=.
set JWT_SECRET=local-development-secret-at-least-32-characters
set APP_ENV=development

echo.
echo [2/4] Installing frontend dependencies (if needed)...
cd /d "%~dp0rehabai\frontend"
if not exist "node_modules" (
    echo Installing npm packages...
    call npm install
) else (
    echo Dependencies already installed.
)

echo.
echo [3/4] Starting Backend (port 8000)...
cd /d "%~dp0rehabai"
start "RehabAI Backend" cmd /k "python -m uvicorn backend.main:app --reload --port 8000 --host 127.0.0.1"

echo.
echo [4/4] Starting Frontend (port 5173)...
cd /d "%~dp0rehabai\frontend"
start "RehabAI Frontend" cmd /k "npm run dev"

echo.
echo ============================================================
echo  Servers are starting...
echo  Backend:  http://127.0.0.1:8000
echo  Frontend: http://localhost:5173
echo ============================================================
echo.
echo Open http://localhost:5173 in your browser.
echo Close the terminal windows to stop the servers.
echo.
pause
