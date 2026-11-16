<#
Visible PowerShell runner for the datanew research pipeline.

Examples:
  .\scripts\run_datanew_experiment.ps1 -Stage extract
  .\scripts\run_datanew_experiment.ps1 -Stage pretrain
  .\scripts\run_datanew_experiment.ps1 -Stage train
  .\scripts\run_datanew_experiment.ps1 -Stage evaluate
  .\scripts\run_datanew_experiment.ps1 -Stage all

Raw data is read-only. Outputs are isolated under data/datanew_unlabeled and
experiments/datanew_ssl_all_full. This runner never promotes a model.
#>
[CmdletBinding()]
param(
  [ValidateSet('extract','pretrain','train','evaluate','all')]
  [string]$Stage = 'all',
  [int]$Workers = 2,
  [int]$Epochs = 30,
  [int]$SSL_Epochs = 50,
  [string]$ExtractRoot = 'E:\PhucHoiChucNangTay_datanew_extract\data_khuyu_tay'
)
$ErrorActionPreference = 'Stop'
$Project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Root = (Resolve-Path (Join-Path $Project '..')).Path
Set-Location $Project
$env:PYTHONPATH = $Project
$keyPath = Join-Path $Project '.secrets\provenance_hmac_key.txt'
$env:REHABAI_PROVENANCE_HMAC_KEY = (Get-Content -LiteralPath $keyPath -Raw).Trim()
$Data = Join-Path $Project 'data\datanew_unlabeled'
$Exp = Join-Path $Project 'experiments\datanew_ssl_all'
$FullExp = Join-Path $Project 'experiments\datanew_ssl_all_full'
$RawDatanew = Join-Path $Root 'datanew'
$RawExtract = $ExtractRoot
$VerifiedRoot = Join-Path $Root 'RehabAI_Datasets_FULL_VERIFIED\01_Upper_Limb_Stroke'
$StageRoot = Join-Path $Project 'data\stage3_upper_limb'

function Run-Python([string[]]$PyArgs) {
  Write-Host ('> python ' + ($PyArgs -join ' ')) -ForegroundColor Cyan
  & python @PyArgs
  if ($LASTEXITCODE -ne 0) { throw "Python failed with exit code $LASTEXITCODE" }
}
function Extract-One([string]$Name, [string]$Source, [string]$Prefix) {
  $out = Join-Path $Data ('features_' + $Name)
  $manifest = Join-Path $Data ('extraction_' + $Name + '_manifest.csv')
  New-Item -ItemType Directory -Force -Path $out | Out-Null
  Run-Python @('scripts/extract_datanew.py','--source-root',$Source,'--output-dir',$out,'--manifest',$manifest,'--workers',$Workers,'--target-frames','96','--sample-prefix',$Prefix)
}
function Extract-Stage {
  New-Item -ItemType Directory -Force -Path $Data | Out-Null
  # The five tgz archives are expected to be extracted once to this external
  # read-only workspace. Do not silently extract into the repository.
  if (-not (Test-Path (Join-Path $RawExtract 'videos'))) {
    throw "Missing extracted AVI root: $RawExtract\videos. Extract archives to E: first; raw archives are not modified by this runner."
  }
  # Reuse the already established AVI artifact locations.
  Run-Python @('scripts/extract_datanew.py','--source-root',(Join-Path $RawExtract 'videos'),'--output-dir',(Join-Path $Data 'features'),'--manifest',(Join-Path $Data 'extraction_manifest.csv'),'--workers',$Workers,'--target-frames','96','--sample-prefix','DATANEW')
  Extract-One 'ehw' (Join-Path $RawDatanew 'EHWGesture_10Subjects_OC_RGB\DataKinects') 'EHW'
  Extract-One 'ex1' (Join-Path $RawDatanew 'ex1') 'EX1'
  Extract-One 'ex2' (Join-Path $RawDatanew 'ex2') 'EX2'
  Extract-One 'ex3' (Join-Path $RawDatanew 'ex3') 'EX3'
  $manifests = @(
    (Join-Path $Data 'extraction_manifest.csv'),
    (Join-Path $Data 'extraction_ehw_manifest.csv'),
    (Join-Path $Data 'extraction_ex1_manifest.csv'),
    (Join-Path $Data 'extraction_ex2_manifest.csv'),
    (Join-Path $Data 'extraction_ex3_manifest.csv')
  )
  $frames = foreach ($m in $manifests) { if (Test-Path $m) { Import-Csv $m | Where-Object status -eq 'ready' } }
  $frames | Sort-Object file -Unique | Export-Csv (Join-Path $Data 'combined_ready_manifest.csv') -NoTypeInformation -Encoding UTF8
  Write-Host ('READY FEATURES: ' + @($frames | Sort-Object file -Unique).Count) -ForegroundColor Green
}
function Pretrain-Stage {
  $manifest = Join-Path $Data 'combined_ready_manifest.csv'
  if (-not (Test-Path $manifest)) { throw "Missing $manifest; run -Stage extract first." }
  New-Item -ItemType Directory -Force -Path $Exp | Out-Null
  Run-Python @('training/pretrain_datanew_ssl.py','--manifest',$manifest,'--output',(Join-Path $Exp 'datanew_ssl_all_encoder.pth'),'--epochs',$SSL_Epochs,'--batch-size','32','--lr','0.001')
}
function Train-Stage {
  $encoder = Join-Path $Exp 'datanew_ssl_all_encoder.pth'
  if (-not (Test-Path $encoder)) { throw "Missing $encoder; run -Stage pretrain first." }
  $check = Join-Path $FullExp 'checkpoints'; $runs = Join-Path $FullExp 'runs'
  New-Item -ItemType Directory -Force -Path $check,$runs | Out-Null
  for ($i=1; $i -le 10; $i++) {
    $fold = ('fold_{0:D2}' -f $i); $fd = Join-Path $StageRoot ('loso\' + $fold)
    Write-Host "===== TRAIN $fold =====" -ForegroundColor Yellow
    Run-Python @('-m','training.proposed_trainer','--data-dir',(Join-Path $StageRoot 'processed\keypoints'),'--source-dir',$VerifiedRoot,'--model-name','RehabMotionNet','--external-encoder',$encoder,'--checkpoint-root',$check,'--run-root',$runs,'--epochs',$Epochs,'--batch_size','16','--lr','0.0003','--upper-limb-only','--balanced-loss','--train-manifest',(Join-Path $fd 'train_manifest.csv'),'--val-manifest',(Join-Path $fd 'val_manifest.csv'),'--norm-json',(Join-Path $fd 'normalization.json'),'--fold-id',$fold)
  }
}
function Evaluate-Stage {
  Run-Python @('scripts/build_external_eval.py','--experiment','datanew_ssl_all_full','--report-name','datanew_ssl_all_full_loso.json')
  Run-Python @('scripts/evaluate.py',(Join-Path $FullExp 'eval_config.json'))
}
Write-Host "DATANEW RESEARCH RUNNER: stage=$Stage workers=$Workers" -ForegroundColor Magenta
if ($Stage -in @('extract','all')) { Extract-Stage }
if ($Stage -in @('pretrain','all')) { Pretrain-Stage }
if ($Stage -in @('train','all')) { Train-Stage }
if ($Stage -in @('evaluate','all')) { Evaluate-Stage }
Write-Host "DONE. No production artifact was changed." -ForegroundColor Green
