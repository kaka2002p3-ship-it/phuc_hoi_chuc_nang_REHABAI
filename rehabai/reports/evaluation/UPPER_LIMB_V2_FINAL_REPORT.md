# Upper-limb RehabMotionNet Final Report

## Outcome

Selected model for exercise classification: **v2**, based on held-out LOSO
Macro-F1. For completion classification, **v1 remains marginally better** and
neither version is materially above a balanced binary baseline.

| Experiment | Samples | Exercise Macro-F1 | Exercise Accuracy | Completion Macro-F1 | Completion Accuracy |
|---|---:|---:|---:|---:|---:|
| Original full-pose | 202 | 0.2507 | - | - | - |
| Upper-limb v1 | 387 | 0.3491 | 0.4174 | 0.4846 | 0.5426 |
| Upper-limb v2 (6 joints + balanced loss) | 387 | 0.3544 | 0.4379 | 0.4828 | 0.5024 |

## Per-fold v2

| Fold | N | Exercise F1 | Accuracy | Completion F1 | Completion Accuracy |
|---|---:|---:|---:|---:|---:|
| fold_01 | 42 | 0.2575 | 0.3571 | 0.6636 | 0.6667 |
| fold_02 | 51 | 0.5652 | 0.5686 | 0.6077 | 0.6078 |
| fold_03 | 44 | 0.5950 | 0.4545 | 0.4070 | 0.4318 |
| fold_04 | 59 | 0.7392 | 0.7458 | 0.5062 | 0.5085 |
| fold_05 | 71 | 0.6919 | 0.6761 | 0.5145 | 0.5493 |
| fold_06 | 44 | 0.3091 | 0.4773 | 0.4909 | 0.5227 |
| fold_07 | 20 | 0.0238 | 0.0500 | 0.2929 | 0.3000 |
| fold_08 | 20 | 0.0652 | 0.1500 | 0.5200 | 0.5500 |
| fold_09 | 16 | 0.1000 | 0.2500 | 0.3766 | 0.4375 |
| fold_10 | 20 | 0.1970 | 0.6500 | 0.4486 | 0.4500 |

## Scientific limitation

Subjects 07-10 contain restricted exercise coverage. Their fold Macro-F1
includes all four canonical classes and therefore correctly penalizes
missing-class generalization. No test subject was used for training,
normalization, checkpoint selection, or pseudo-labeling.

## Decision

- Use v2 only for experimental exercise classification: exercise Macro-F1
  improved from 0.3491 to 0.3544 and accuracy from 0.4174 to 0.4379.
- Do not promote the completion head to production. Its Macro-F1 is 0.4828;
  v1 scored 0.4846, so balanced loss did not improve this task.
- The dominant remaining limitation is subject/exercise coverage, especially
  folds 07-10, rather than optimization duration.
