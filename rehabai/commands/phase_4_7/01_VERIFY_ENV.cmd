@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0..\.."

if not exist ".secrets" mkdir ".secrets"
if not exist ".secrets\provenance_hmac_key.txt" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$bytes = New-Object byte[] 48; $rng = [Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($bytes); $rng.Dispose(); [IO.File]::WriteAllText('.secrets\provenance_hmac_key.txt', [Convert]::ToBase64String($bytes), [Text.UTF8Encoding]::new($false))"
  if errorlevel 1 (
    echo [FAIL] Could not create the local provenance key.
    exit /b 1
  )
)

set /p REHABAI_PROVENANCE_HMAC_KEY=<".secrets\provenance_hmac_key.txt"
if not defined REHABAI_PROVENANCE_HMAC_KEY (
  echo [FAIL] The local provenance key is empty.
  exit /b 1
)

if not exist "logs\phase_4_7_stage3" mkdir "logs\phase_4_7_stage3"
set "LOG=logs\phase_4_7_stage3\01_verify_env.log"

python scripts\stage3_preflight.py > "%LOG%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
type "%LOG%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [STOP] Preflight failed. Do not run extraction.
  exit /b %EXIT_CODE%
)

echo.
echo [PASS] Environment is ready. Next command: 02_EXTRACT_REAL_DATA.cmd
exit /b 0
