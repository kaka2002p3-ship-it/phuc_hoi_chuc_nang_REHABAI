# RehabCTR-TCN evaluation

Protocol: subject-wise LOSO on verified real landmark data.

| Exercise | Valid folds | Skipped folds | Mean accuracy | Mean Macro-F1 |
|---|---:|---:|---:|---:|
| HAND_OPENING | 5 | 5 | 0.4615 | 0.6297 |
| ELBOW_EXTENSION | 4 | 6 | 0.3662 | 0.5057 |

## Interpretation

The model was trained with Joint/Bone/Motion streams, graph encoders, MS-TCN refinement, attention pooling and a binary correctness head.

Rep MAE, exact count accuracy, boundary F1 and temporal IoU are **not available** because the verified manifests contain video-level Complete/Incomplete labels but no repetition boundaries or rep-level labels. No pseudo-labels were used.

A fold is skipped when its target exercise has no test samples or only one test class; this is required for a valid binary LOSO estimate.

The current result is a research baseline for correctness classification, not a clinical or product-ready rep counter.
