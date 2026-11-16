@echo off
chcp 65001 >nul
title RehabAI Frontend Only

echo.
echo ============================================================
echo   RehabAI Frontend - Vite Dev Server
echo ============================================================
echo.

cd /d "%~dp0frontend"

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing dependencies (this may take a few minutes)...
    call npm install
    if errorlevel 1 (
        echo.
        echo [ERROR] npm install failed!
        echo Make sure Node.js 18+ is installed: https://nodejs.org/
        pause
        exit /b 1
    )
)

echo.
echo Starting Vite dev server...
echo.
call npm run dev

pause
