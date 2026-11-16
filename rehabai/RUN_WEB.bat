@echo off
chcp 65001 >nul
title RehabAI Web - Backend + Frontend

echo.
echo ============================================================
echo   RehabAI - Starting Web Application
echo ============================================================
echo.

REM Change to rehabai directory
cd /d "%~dp0"

REM Set environment variables
set PYTHONPATH=.
set JWT_SECRET=local-development-secret-at-least-32-characters
set APP_ENV=development

REM Start Backend
echo [1/2] Starting Backend on port 8000...
start "RehabAI Backend" /D "%~dp0" cmd /k "title RehabAI Backend && python -m uvicorn backend.main:app --reload --port 8000 --host 127.0.0.1"

REM Wait a bit for backend
timeout /t 3 /nobreak >nul

REM Start Frontend
echo [2/2] Starting Frontend on port 5173...
start "RehabAI Frontend" /D "%~dp0frontend" cmd /k "title RehabAI Frontend && npm run dev"

echo.
echo ============================================================
echo   Servers are starting!
echo.
echo   Backend:  http://127.0.0.1:8000
echo   API Docs: http://127.0.0.1:8000/docs
echo   Frontend: http://localhost:5173
echo.
echo   Open http://localhost:5173 in your browser.
echo   Close the terminal windows to stop the servers.
echo ============================================================
echo.
pause
