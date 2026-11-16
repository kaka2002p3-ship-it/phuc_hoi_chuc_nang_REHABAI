# Datanew automation handoff — 2026-09-20

## Completed automatically

- Existing extraction reused; no duplicate extraction was run.
- 179 ready videos scanned and 921 repetition candidates generated.
- Experimental `auto_rule_v1` labels generated with provenance.
- Validation passed: 921 rows, 462 labeled `correct/incorrect`, 459 `uncertain`.
- Strict timing-only baseline evaluated at seeds 42, 7 and 2026.
- Metrics and visual training logs saved under `experiments/` and `logs/`.

## Current research result

| Exercise | Three-seed Macro-F1 mean | Standard deviation |
|---|---:|---:|
| `ELBOW_FLEXION` | 0.6518 | 0.0577 |
| `HAND_OPENING` | 0.6475 | 0.1199 |

These are scores against heuristic labels, not clinical correctness labels.

## Safety status

- Production promotion: **blocked**.
- Clinical interpretation: **blocked**.
- New extraction: not required for current artifacts.
- New training: not required until human-reviewed labels replace heuristic labels.

## When the user is ready

Run the review UI and replace/augment the experimental manifest:

```powershell
cd D:\PhucHoiChucNangTay\rehabai
streamlit run tools\datanew_review_app.py --server.port 8502
```

Then validate:

```powershell
python scripts\validate_datanew_reviews.py `
  --reviews data\annotations\datanew_rep_reviewed.csv `
  --queue data\annotations\datanew_rep_review_queue.csv
```

Before any future extraction/training, show the user the exact PowerShell command with `Tee-Object` logging and wait for confirmation.
