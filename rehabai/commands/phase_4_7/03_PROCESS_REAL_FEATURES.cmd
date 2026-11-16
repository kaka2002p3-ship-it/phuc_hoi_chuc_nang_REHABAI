@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0..\.."

if not exist "data\stage3_real\indexes\extraction_quality.csv" (
  echo [STOP] Missing Stage 3 extraction quality log.
  exit /b 1
)
if not exist "logs\phase_4_7_stage3" mkdir "logs\phase_4_7_stage3"
set "LOG=%CD%\logs\phase_4_7_stage3\03_process_real_features.log"

powershell -NoProfile -ExecutionPolicy Bypass -Command "& python scripts\process_features.py 2>&1 | Tee-Object -FilePath '%LOG%'; exit $LASTEXITCODE"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [STOP] Feature processing reported an error. Do not verify provenance.
  echo Send this log for review: %LOG%
  exit /b %EXIT_CODE%
)

echo.
echo [PASS] Features and REAL_CANDIDATE records were created.
echo Next command after review: 04_VERIFY_PROVENANCE.cmd
exit /b 0
