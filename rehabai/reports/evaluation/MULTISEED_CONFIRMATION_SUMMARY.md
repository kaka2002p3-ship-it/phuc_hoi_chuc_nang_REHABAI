# Multi-seed confirmation: Full v2 vs Optimized-v1

Protocol: strict 10-fold subject-wise LOSO. Seeds 7 and 2026 were
predeclared confirmations; seed 42 is the original exploratory comparison.
Checkpoints were selected only from validation performance.

| Seed | Full v2 Macro-F1 | Optimized-v1 Macro-F1 | Paired delta | W/T/L |
|---:|---:|---:|---:|---:|
| 42 | 0.3544 +/- 0.2704 | 0.3945 +/- 0.3478 | +0.0401 | 4/1/5 |
| 7 | 0.3212 +/- 0.2720 | 0.3779 +/- 0.3143 | +0.0567 | 6/1/3 |
| 2026 | 0.2953 +/- 0.2450 | 0.3869 +/- 0.3319 | +0.0916 | 7/2/1 |

## Aggregate descriptive result

Across 30 paired fold-seed evaluations, mean Macro-F1 delta is +0.0628; W/T/L=17/4/9.
The seed-averaged optimized candidate is better on 6/10 held-out subjects.

These 30 rows are repeated evaluations of only 10 subjects, not 30
independent subjects. Multi-seed confirmation measures training randomness;
it cannot repair post-selection bias or establish clinical generalization.

## Decision

Robustness: `directionally_consistent_across_seeds`.
Production remains unchanged. Final research classification remains
`E_DATASET_TOO_SMALL_OR_INSUFFICIENT_FOR_STRONG_CONCLUSION`.
Optimized-v1 is a promising research candidate, but validate the frozen architecture on fresh subjects before any production promotion.
