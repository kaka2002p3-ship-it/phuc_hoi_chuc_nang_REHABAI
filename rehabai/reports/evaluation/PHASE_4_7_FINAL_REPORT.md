# Phase 4.7 Final Report — Real Data + True LOSO

> Status: **PASS (protocol and acceptance artifacts complete)**. The scientific
> decision remains **E — dataset too small / insufficient for a strong generalization
> conclusion**. PASS here means the evaluation protocol is complete, not that the
> model is clinically validated or that its accuracy is high.

## 1. Data provenance

The source index contains 491 real MP4 videos from 10 subjects. The upper-limb
quality gate accepted 387 samples. Every accepted NPZ is linked to an existing
source video and has a verified source/feature checksum.

Trace artifacts: `reports/data_provenance/h5_provenance.csv` and
`reports/data_provenance/label_provenance.csv`.

## 2. Real vs synthetic verification

The strict training/evaluation manifest contains 387 `REAL_VERIFIED` samples.
The historical mock extractor remains in the repository but its artifacts are
excluded by the strict manifest and loader.

## 3. Feature, label and subject verification

Features are finite, shape-checked and physically traced to source videos.
Exercise and completion labels come from `upper_limb_master.csv`; subject IDs
come from the authoritative index. No random or inferred labels are admitted.

## 4. True LOSO protocol

Ten folds are evaluated with one held-out test subject per fold. Validation is
drawn only from the training subjects. Subject split precedes loading/windowing,
normalization is fitted on train only, and augmentation is train only.
Checkpoint selection and all hyperparameter decisions use validation only.

## 5. Strict baseline results

| Model | Exercise Macro-F1 | Accuracy | Weighted-F1 | Completion Macro-F1 | Completion accuracy |
|---|---:|---:|---:|---:|---:|
| Majority Class | 0.0547 ± 0.0713 | 0.1515 ± 0.1992 | 0.0842 ± 0.1143 | 0.3234 ± 0.0457 | 0.4839 ± 0.0966 |
| Linear SVM (48-D kinematics) | 0.2880 ± 0.2440 | 0.3651 ± 0.2662 | 0.3938 ± 0.2392 | 0.4391 ± 0.1478 | 0.4688 ± 0.1461 |
| MLP | 0.2779 ± 0.2994 | 0.3451 ± 0.3106 | 0.3670 ± 0.3172 | 0.3967 ± 0.1718 | 0.4538 ± 0.1847 |
| Simple LSTM | 0.3245 ± 0.3377 | 0.3996 ± 0.3555 | 0.4030 ± 0.3513 | 0.5384 ± 0.1181 | 0.5741 ± 0.0817 |
| RehabMotionNet v2 | 0.3544 ± 0.2704 | 0.4379 ± 0.2335 | 0.4985 ± 0.2230 | 0.4828 ± 0.1083 | 0.5024 ± 0.1032 |
| Ensemble v1 (research) | 0.3744 ± 0.3319 | 0.4345 ± 0.3038 | n/a | n/a | n/a |

The MLP and LSTM rows are strict evaluations of the 20 completed checkpoints
(`baseline_mlp_v1` and `baseline_lstm_v1`), not retraining runs.

## 6. Per-fold, per-subject and confusion artifacts

Machine-readable per-fold outputs are in `loso_strict_mlp.json`,
`loso_strict_lstm.json` and `loso_upper_limb_v2.json`. Per-subject metrics are
in `loso_per_subject.csv`; the aggregate confusion matrix is in
`confusion_matrix_loso.csv`; protocol and generalization-gap tables are
`loso_protocol.csv` and `loso_generalization_gap.csv`.

## 7. Overfitting and failure analysis

MLP mean final train–validation F1 gap: 0.3109; warning folds: fold_01, fold_02, fold_03, fold_05, fold_06, fold_08, fold_10.
LSTM mean final train–validation F1 gap: 0.3297; warning folds: fold_03, fold_04, fold_06, fold_07, fold_10.
Subjects 07–10 have restricted exercise coverage, which strongly depresses
four-class macro-F1 on those held-out folds. This is the dominant limitation.

## 8. Limitations

There are only 10 subjects and 387 accepted samples, with one seed (42). The
runtime is Python 3.11.9, PyTorch 2.5.1+cu121 and MediaPipe 0.10.9, rather than
the canonical V3.1 lock. The results are research subject-independent evaluation,
not clinical validation or a medical-grade claim.

## 9. Decision and next step

**Protocol status: PASS. Scientific conclusion: E — DATASET TOO SMALL /
INSUFFICIENT FOR STRONG CONCLUSION.**

Production remains unchanged. The project may now proceed to the planned ablation
matrix, preserving the same ten-fold LOSO protocol and validation-only selection.
Ablation results must remain research artifacts until they beat the current
baseline/ensemble with stable fold-wise evidence and independent confirmation.
