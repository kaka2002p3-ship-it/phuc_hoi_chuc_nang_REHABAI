# Frozen external-encoder adapter summary

All figures use strict ten-fold subject-wise LOSO on data 01. Because three adapter
sources share the test folds, selecting the best result is exploratory only.

| Model | Exercise Macro-F1 | Accuracy | Completion Macro-F1 | Wins vs ensemble |
|---|---:|---:|---:|---:|
| Frozen REHAB24-6 encoder + adapter | 0.2832 | 0.3662 | 0.4771 | 3 |
| Frozen MobiPhysio encoder + adapter | 0.3106 | 0.4199 | 0.4753 | 4 |
| Frozen 02+03 encoder + adapter | 0.2494 | 0.3990 | 0.5509 | 3 |
| Existing RehabMotionNet v2 | 0.3544 | 0.4379 | 0.4828 | n/a |
| Existing validation-selected ensemble | 0.3744 | 0.4345 | n/a | n/a |

## Decision

Best adapter: `mobiphysio_adapter`.
Research gate passed: `false`.
Production remains unchanged. Any promotion requires confirmation on fresh subjects
or a new evaluation protocol that was not used to select among these variants.
