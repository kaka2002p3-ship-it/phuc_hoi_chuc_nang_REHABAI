# Optimized-v1 multi-seed ensemble

Equal softmax-probability averaging of the existing seed 42, 7 and 2026 checkpoints.
No new training and no test-fold weight selection were used.

| Candidate | Macro-F1 | Accuracy |
|---|---:|---:|
| Three-seed ensemble | 0.3904 ± 0.3352 | 0.4776 ± 0.3174 |
| seed 42 | 0.3945 ± 0.3478 | 0.4837 ± 0.3306 |
| seed 7 | 0.3779 ± 0.3143 | 0.4680 ± 0.2800 |
| seed 2026 | 0.3869 ± 0.3319 | 0.4777 ± 0.3111 |

## Paired result

- Versus seed_42: delta=-0.0041; W/T/L=3/4/3.
- Versus seed_7: delta=+0.0124; W/T/L=5/1/4.
- Versus seed_2026: delta=+0.0035; W/T/L=3/2/5.

This remains exploratory. Production is unchanged and fresh-subject validation is required.
