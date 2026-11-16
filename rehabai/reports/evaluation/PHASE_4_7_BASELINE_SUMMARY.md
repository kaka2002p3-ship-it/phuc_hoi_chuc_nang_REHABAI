# Phase 4.7 strict LOSO baseline summary

All trainable checkpoints were selected using validation data only and evaluated
once on the held-out subject. Results cover all ten folds and 387 REAL_VERIFIED samples.

| Model | Exercise Macro-F1 | Accuracy | Weighted-F1 | Completion Macro-F1 | Completion accuracy |
|---|---:|---:|---:|---:|---:|
| Majority Class | 0.0547 ± 0.0713 | 0.1515 ± 0.1992 | 0.0842 ± 0.1143 | 0.3234 ± 0.0457 | 0.4839 ± 0.0966 |
| Linear SVM (48-D kinematics) | 0.2880 ± 0.2440 | 0.3651 ± 0.2662 | 0.3938 ± 0.2392 | 0.4391 ± 0.1478 | 0.4688 ± 0.1461 |
| MLP | 0.2779 ± 0.2994 | 0.3451 ± 0.3106 | 0.3670 ± 0.3172 | 0.3967 ± 0.1718 | 0.4538 ± 0.1847 |
| Simple LSTM | 0.3245 ± 0.3377 | 0.3996 ± 0.3555 | 0.4030 ± 0.3513 | 0.5384 ± 0.1181 | 0.5741 ± 0.0817 |
| RehabMotionNet v2 | 0.3544 ± 0.2704 | 0.4379 ± 0.2335 | 0.4985 ± 0.2230 | 0.4828 ± 0.1083 | 0.5024 ± 0.1032 |
| Ensemble v1 (research) | 0.3744 ± 0.3319 | 0.4345 ± 0.3038 | n/a | n/a | n/a |

## Range and stability

| Model | Exercise Macro-F1 min | max |
|---|---:|---:|
| Majority Class | 0.0000 | 0.1508 |
| Linear SVM (48-D kinematics) | 0.0238 | 0.6175 |
| MLP | 0.0000 | 0.7812 |
| Simple LSTM | 0.0000 | 0.9429 |
| RehabMotionNet v2 | 0.0238 | 0.7392 |
| Ensemble v1 (research) | 0.0000 | 0.8883 |

## Decision

Best single model: `rehabmotionnet_v2`.
Best research candidate: `ensemble_v1`.
The production artifact is unchanged. Model optimization and ablation must retain
the same strict protocol, and no promotion is allowed without stronger evidence.
