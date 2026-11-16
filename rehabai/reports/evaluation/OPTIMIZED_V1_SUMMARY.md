# Optimized-v1 exploratory result

Optimized-v1 keeps pose, hand, kinematic and MS-TCN branches while removing
attention and the frozen contrastive encoder. It uses strict ten-fold LOSO and
validation-only checkpoint selection, but its architecture was chosen after seeing
the ablation results, so this comparison is exploratory.

| Model | Exercise Macro-F1 | Accuracy |
|---|---:|---:|
| Optimized-v1 | 0.3945 ± 0.3478 | 0.4837 ± 0.3306 |
| Full v2 | 0.3544 ± 0.2704 | 0.4379 ± 0.2335 |
| Ensemble v1 | 0.3744 ± 0.3319 | 0.4345 ± 0.3038 |

## Paired evidence

- Versus Full v2: delta=+0.0401; wins/ties/losses=4/1/5.
- Versus Ensemble v1: delta=+0.0201; wins/ties/losses=5/2/3.

<!-- MULTISEED_CONFIRMATION_START -->
## Multi-seed confirmation

Additional predeclared seeds 7 and 2026 are complete. Across all three seeds, the paired Macro-F1 delta is +0.0628 with W/T/L=17/4/9. Robustness: `directionally_consistent_across_seeds`.

This reuses the same 10 subjects and does not remove post-ablation selection bias.
Production remains unchanged; validation on fresh subjects is required.
<!-- MULTISEED_CONFIRMATION_END -->

Production is unchanged. Confirmation on predeclared additional seeds or fresh subjects is required before promotion.
