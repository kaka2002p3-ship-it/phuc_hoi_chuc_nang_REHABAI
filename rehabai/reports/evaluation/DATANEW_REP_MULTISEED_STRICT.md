# Datanew strict multi-seed smoke test

- Labels: `auto_rule_v1` heuristic, not clinical ground truth.
- Split: grouped by video ID; strict features contain timing only.

## Per-seed results

| Seed | Exercise | Macro-F1 | Accuracy | Test reps | Test videos |
|---:|---|---:|---:|---:|---:|
| 42 | ELBOW_FLEXION | 0.7018 | 0.7027 | 37 | 13 |
| 42 | HAND_OPENING | 0.7723 | 0.8065 | 62 | 26 |
| 7 | ELBOW_FLEXION | 0.6648 | 0.6667 | 54 | 13 |
| 7 | HAND_OPENING | 0.5333 | 0.5714 | 63 | 26 |
| 2026 | ELBOW_FLEXION | 0.5887 | 0.6034 | 58 | 13 |
| 2026 | HAND_OPENING | 0.6369 | 0.6721 | 61 | 26 |

## Mean ± standard deviation

- ELBOW_FLEXION: Macro-F1 `0.6518 ± 0.0577`, accuracy `0.6576 ± 0.0502`.
- HAND_OPENING: Macro-F1 `0.6475 ± 0.1199`, accuracy `0.6833 ± 0.1179`.

## Decision

- Research pipeline: PASS.
- Stable clinical correctness evidence: FAIL.
- Production promotion: FAIL.
- Reason: labels are generated from a heuristic and results vary materially by held-out videos/seeds.