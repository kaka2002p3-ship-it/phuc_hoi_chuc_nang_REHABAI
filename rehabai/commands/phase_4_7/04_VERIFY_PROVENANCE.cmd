@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0..\.."

if not exist ".secrets\provenance_hmac_key.txt" (
  echo [STOP] Missing local provenance key. Run 01_VERIFY_ENV.cmd.
  exit /b 1
)
if not exist "data\stage3_real\indexes\provenance_candidates.csv" (
  echo [STOP] Missing provenance candidates. Run and review step 03.
  exit /b 1
)

set /p REHABAI_PROVENANCE_HMAC_KEY=<".secrets\provenance_hmac_key.txt"
if not defined REHABAI_PROVENANCE_HMAC_KEY (
  echo [STOP] The local provenance key is empty.
  exit /b 1
)

if not exist "logs\phase_4_7_stage3" mkdir "logs\phase_4_7_stage3"
set "LOG=%CD%\logs\phase_4_7_stage3\04_verify_provenance.log"

python scripts\verify_provenance.py ^
  --input-csv "data\stage3_real\indexes\provenance_candidates.csv" ^
  --output-csv "data\stage3_real\indexes\provenance_verified.csv" ^
  --source-root "%CD%\..\RehabAI_Datasets_FULL_VERIFIED\01_Upper_Limb_Stroke" ^
  --processed-root "%CD%\data\stage3_real\processed\keypoints" > "%LOG%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
type "%LOG%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [STOP] Provenance verification failed. Do not generate LOSO folds.
  exit /b %EXIT_CODE%
)

echo.
echo [PASS] Signed REAL_VERIFIED manifest created.
echo Send the log and provenance_verified.csv for review before LOSO generation.
exit /b 0
