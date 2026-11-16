# Datanew expert final training — seed 42

**Protocol:** fixed video-disjoint train/validation/test, class-weighted logistic baseline.  
**Labels:** final review by `PT_01` and second review `PT_02`; 920 confirmed, one uncertain excluded.  
**Extraction:** reused; no new extraction.

| Exercise | Validation Macro-F1 | Test accuracy | Test Macro-F1 | Incorrect test F1 |
|---|---:|---:|---:|---:|
| `ELBOW_FLEXION` | 0.5887 | 0.2759 | 0.2435 | 0.0870 |
| `HAND_OPENING` | 0.4886 | 0.6447 | 0.5177 | 0.2703 |

## Interpretation

- Both validation and test now contain correct and incorrect examples from video-disjoint groups.
- `ELBOW_FLEXION` drops sharply from validation to test, indicating poor generalization across videos.
- `HAND_OPENING` is better but incorrect precision/F1 remain low.
- Class weighting helps expose the minority class, but cannot replace more diverse motion evidence or a sequence model.
- This summary-feature logistic baseline must not be promoted to production.

## Next technical experiment

Use the actual landmark sequence for each reviewed repetition, resampled to a fixed length, then train an exercise-specific temporal model. Preserve the current fixed video split and report per-class F1/confusion matrices across multiple seeds.

Artifacts:

- `experiments/datanew_expert_final_seed42/metrics.json`
- `logs/datanew_expert_final_seed42_visual.log`
