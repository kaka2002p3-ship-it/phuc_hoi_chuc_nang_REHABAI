# Datanew multi-seed evaluation

**Ngày đánh giá:** 2026-09-18  
**Seeds:** 42, 7, 2026  
**Protocol:** strict 10-fold subject-wise LOSO, 387 test samples mỗi seed  
**Kết luận:** **completion research PASS / exercise FAIL / production FAIL**

## Artifact verification

- Seed 7 và seed 2026 đều có encoder SSL, 10/10 supervised checkpoints, 10/10 training summaries và 10-fold evaluation report.
- Encoder metadata của cả hai seed khớp manifest 619 mẫu (`2d5c5fa...3ec1e`), đúng seed và không có product ontology mapping.
- 20/20 checkpoint khai báo đúng seed, đúng external encoder hash và manifest hash.
- Training history đều hữu hạn. Có 6/10 warning summaries ở seed 7 và 2/10 ở seed 2026.
- Strict evaluator chạy lại thành công; SHA-256 report trước/sau không đổi.

## Mean result across ten folds

| Candidate | Exercise Macro-F1 | Exercise accuracy | Completion Macro-F1 | Completion accuracy |
|---|---:|---:|---:|---:|
| Baseline v2 | 0.3544 | 0.4379 | 0.4828 | 0.5024 |
| Datanew seed 42 | 0.3718 | 0.4646 | 0.5606 | 0.5803 |
| Datanew seed 7 | 0.3226 | 0.4273 | 0.5285 | 0.5514 |
| Datanew seed 2026 | 0.3435 | 0.4140 | 0.5441 | 0.5671 |
| **Three-seed mean** | **0.3460** | **0.4353** | **0.5444** | **0.5663** |

Three-seed mean delta versus baseline:

- Exercise Macro-F1: `-0.0084`.
- Exercise accuracy: `-0.0027`.
- Completion Macro-F1: `+0.0616`.
- Completion accuracy: `+0.0638`.

On seed-averaged held-out subjects, completion wins/losses are 7/3. Exercise Macro-F1 wins/losses are 4/6; exercise accuracy is 3 wins, 1 tie and 6 losses.

## Statistical caution

- Paired Wilcoxon on the ten seed-averaged subject deltas gives `p=0.1055` for both completion Macro-F1 and accuracy.
- Subject bootstrap 95% descriptive intervals for mean completion delta are approximately `[+0.0032, +0.1241]` Macro-F1 and `[+0.0054, +0.1240]` accuracy.
- These are only ten subjects. Repeated seeds reduce optimizer randomness but do not create new independent subjects. The result is encouraging, not confirmatory clinical evidence.

## Decision

1. Do not use the datanew model to replace the exercise classifier. Its three-seed exercise mean is slightly below baseline and remains unstable on subjects 07–10.
2. Retain the datanew representation/completion head as a research candidate. Completion improvement reproduced for all three seeds: `+0.0778`, `+0.0457`, and `+0.0613` Macro-F1 over baseline.
3. The practical next architecture is task-specific: keep `optimized_v1` for exercise and evaluate the datanew branch for completion. Do not route by test fold or choose a seed using test performance.
4. Do not promote to production until fresh-subject validation and a predeclared completion selection/calibration protocol pass.

## Final gate

| Gate | Result |
|---|---|
| Multi-seed run completeness | PASS |
| Artifact/provenance integrity | PASS |
| Completion direction reproduced across seeds | PASS |
| Exercise replacement | FAIL |
| Statistical/fresh-subject confirmation | FAIL |
| Production promotion | FAIL |

