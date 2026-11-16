# IntelliRehabDS SSL adapter pilot

This is a frozen fold-0 self-supervised IntelliRehabDS encoder attached to the predeclared Optimized-v1 target model.
It is exploratory and does not change production.

| Model | Exercise Macro-F1 | Accuracy |
|---|---:|---:|
| SSL adapter | 0.3599 ± 0.3387 | 0.4529 ± 0.3358 |
| Optimized-v1 | 0.3945 ± 0.3478 | 0.4837 ± 0.3306 |

Paired Macro-F1 delta: -0.0346; wins/ties/losses=4/2/4.

Production remains unchanged; fresh-subject validation is required before promotion.
