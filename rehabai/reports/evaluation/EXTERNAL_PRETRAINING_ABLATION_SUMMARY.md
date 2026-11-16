# External-pretraining ablation summary

All figures use the same strict ten-fold subject-wise LOSO test protocol on data 01.
No test fold was used for checkpoint or hyperparameter selection.

| Model | Exercise Macro-F1 mean | F1 std | Accuracy mean | Accuracy std |
|---|---:|---:|---:|---:|
| REHAB24-6 only (02) | 0.3458 | 0.3154 | 0.4229 | 0.3104 |
| MobiPhysio only (03) | 0.3398 | 0.2873 | 0.4161 | 0.2701 |
| 02 + 03 | 0.3003 | 0.2723 | 0.3768 | 0.2954 |
| Existing RehabMotionNet v2 | 0.3544 | 0.2704 | 0.4379 | 0.2335 |
| Existing validation-selected ensemble | 0.3744 | 0.3319 | 0.4345 | 0.3038 |
| Existing teacher-student | 0.3351 | 0.2336 | 0.4673 | 0.2681 |

## Decision

The external-pretraining branches remain research artifacts and are not promoted.
The combined 02+03 branch is below the existing v2 and validation-selected ensemble.
The single-source ablations do not recover the loss, so the issue is not explained by
simple source mixing alone; domain/ontology mismatch and limited target data remain likely.
Production remains unchanged.

Recommended next experiment: freeze the external encoder and train only a small target
adapter or use external data for self-supervised motion objectives without source-exercise
classification heads, then repeat the same paired LOSO evaluation.
