# RehabMotionNet strict ablation summary

All variants use the same 387 REAL_VERIFIED samples, ten-fold LOSO, seed 42,
train-only normalization/augmentation and validation-only checkpoint selection.

| Variant | Exercise Macro-F1 | Accuracy | Weighted-F1 | Completion Macro-F1 | Completion accuracy | Delta vs full | W/T/L |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 0.3544 ± 0.2704 | 0.4379 ± 0.2335 | 0.4985 ± 0.2230 | 0.4828 ± 0.1083 | 0.5024 ± 0.1032 | +0.0000 | 0/10/0 |
| − hand | 0.2811 ± 0.2740 | 0.3579 ± 0.2772 | 0.4047 ± 0.2767 | 0.4910 ± 0.0810 | 0.5219 ± 0.0605 | -0.0733 | 3/2/5 |
| − kinematic | 0.3365 ± 0.2517 | 0.4610 ± 0.2613 | 0.5055 ± 0.2798 | 0.5273 ± 0.0985 | 0.5547 ± 0.0893 | -0.0179 | 5/0/5 |
| − contrastive | 0.3655 ± 0.2840 | 0.5015 ± 0.2779 | 0.5604 ± 0.2592 | 0.5078 ± 0.0799 | 0.5449 ± 0.0619 | +0.0112 | 4/2/4 |
| − MS-TCN | 0.3627 ± 0.2688 | 0.4864 ± 0.2511 | 0.5363 ± 0.2478 | 0.5021 ± 0.1226 | 0.5468 ± 0.0880 | +0.0083 | 4/1/5 |
| − attention | 0.3763 ± 0.3246 | 0.4653 ± 0.3199 | 0.5094 ± 0.3035 | 0.4737 ± 0.1195 | 0.4966 ± 0.1109 | +0.0219 | 3/2/5 |

Best ablation by mean exercise Macro-F1: `minus_attention`.
It wins/ties/loses 3/2/5 folds against full.
The mean gain is exploratory and not fold-stable; it is not sufficient for promotion.
Production remains unchanged; ablations are research artifacts. The next optimization
should confirm the simplified candidate across additional seeds or fresh subjects before
any architecture decision.
