# External pretraining decision

Evaluation uses the unchanged data-01 strict ten-fold LOSO test sets.
External data is used only to initialize the shared encoder.

| Model | Mean Macro-F1 | Fold std | Mean accuracy |
|---|---:|---:|---:|
| External pretraining 02+03 | 0.3003 | 0.2723 | 0.3768 |
| Existing ensemble | 0.3744 | 0.3319 | 0.4345 |

Recommendation: `keep_existing_model_and_run_external_ablation`.

The production artifact is not changed automatically. External-only ablations and
fresh-subject validation remain required before any production promotion.
