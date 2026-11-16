# Datanew expert-label full training — seed 42

**Protocol:** all confirmed expert labels, `class_weight=balanced`, group split by `video_id`.  
**Extraction:** reused; no new extraction was run.  
**Status:** research only.

## Results

| Exercise | Status | Train reps | Test reps | Test videos | Accuracy | Macro-F1 |
|---|---|---:|---:|---:|---:|---:|
| `ELBOW_FLEXION` | complete | 290 | 92 | 13 | 0.8043 | 0.5354 |
| `HAND_OPENING` | skipped | — | — | — | — | — |

`ELBOW_FLEXION` test details:

- Incorrect: precision `0.1053`, recall `0.6667`, F1 `0.1818`, support `3`.
- Correct: precision `0.9863`, recall `0.8090`, F1 `0.8889`, support `89`.

Accuracy 0.8043 is dominated by the correct class. Macro-F1 and per-class F1 are the relevant indicators; the incorrect test support of three samples is too small for a stable claim.

`HAND_OPENING` was correctly blocked because all four incorrect repetitions come from one video. A video-disjoint split cannot put incorrect examples in both train and test without leakage.

## Decision

- Supervised expert-label pipeline: PASS.
- Reliable ELBOW_FLEXION correctness model: NOT YET.
- HAND_OPENING video-disjoint evaluation: BLOCKED by one incorrect video.
- Production promotion: FAIL.

Artifacts:

- `experiments/datanew_rep_expert_full_seed42/metrics.json`
- `logs/datanew_rep_expert_full_seed42_visual.log`
