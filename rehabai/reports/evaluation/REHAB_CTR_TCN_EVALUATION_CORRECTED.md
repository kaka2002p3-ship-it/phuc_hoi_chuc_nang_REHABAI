# RehabCTR-TCN evaluation

Protocol: subject-wise LOSO on verified real landmark data.

| Exercise | Valid folds | Skipped folds | Accuracy | Macro Precision | Macro Recall | Macro-F1 | Majority F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| HAND_OPENING | 5 | 5 | 0.5368 | 0.3661 | 0.5100 | 0.3646 | 0.3540 |
| ELBOW_EXTENSION | 4 | 6 | 0.2960 | 0.2105 | 0.5000 | 0.2392 | 0.4096 |

## Interpretation

The model was trained with Joint/Bone/Motion streams, graph encoders, MS-TCN refinement, attention pooling and a binary correctness head.

Rep MAE, exact count accuracy, boundary F1 and temporal IoU are **not available** because the verified manifests contain video-level Complete/Incomplete labels but no repetition boundaries or rep-level labels. No pseudo-labels were used.

A fold is skipped when its target exercise has no test samples or only one test class; this is required for a valid binary LOSO estimate.

The current result is a research baseline for correctness classification, not a clinical or product-ready rep counter.
