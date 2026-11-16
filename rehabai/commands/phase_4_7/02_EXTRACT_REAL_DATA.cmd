@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0..\.."

python scripts\stage3_preflight.py
if errorlevel 1 (
  echo.
  echo [STOP] Preflight failed. Extraction was not started.
  exit /b 1
)

if not exist "logs\phase_4_7_stage3" mkdir "logs\phase_4_7_stage3"
set "LOG=%CD%\logs\phase_4_7_stage3\02_extract_real_data.log"
set "WORKERS=2"

echo.
echo Starting real MediaPipe extraction with %WORKERS% workers.
echo Output is isolated under data\stage3_real.
echo The command is resumable: rerun this CMD after an interruption.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "& python scripts\extract_keypoints.py --workers %WORKERS% 2>&1 | Tee-Object -FilePath '%LOG%'; exit $LASTEXITCODE"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [STOP] Extraction reported an error. Do not process features yet.
  echo Send this log for review: %LOG%
  exit /b %EXIT_CODE%
)

echo.
echo [PASS] Extraction completed without execution errors.
echo Send these two files for review before running step 03:
echo   %LOG%
echo   %CD%\data\stage3_real\indexes\extraction_quality.csv
exit /b 0
