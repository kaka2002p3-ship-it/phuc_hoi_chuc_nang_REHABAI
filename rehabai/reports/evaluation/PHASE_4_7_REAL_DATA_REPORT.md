# Phase 4.7 Real-Data Report (PASS — protocol complete)

> This version supersedes the historical synthetic-data report for the new
> Stage 3 real-data pipeline. The historical report is retained for audit history.

## 1. Data Provenance

The source index contains 491 real MP4 videos from 10 subjects. The upper-limb quality gate accepted 387 samples. Every accepted NPZ is linked to an existing source video and verified by physical checksums.

Trace tables: `reports/data_provenance/h5_provenance.csv` (historical filename,
actual feature format is NPZ) and `reports/data_provenance/label_provenance.csv`.

## 2. Real vs Synthetic Data Verification

All 387 samples in the training/evaluation manifest have `data_status=REAL_VERIFIED`.
The old mock extraction remains in the repository as a development utility but none
of its artifacts are admitted by the strict manifest loader.

## 3. Feature Verification

Strict loading checks exact arrays/shapes, finite values, physical source and processed
file existence, checksums, quality gate and signed provenance before training/evaluation.

## 4. Label Verification

Exercise and Complete/Incomplete labels trace to `data/indexes/upper_limb_master.csv`.
No label is inferred or randomly generated.

## 5. Subject Verification

Verified subjects: 10. Accepted sample counts by subject are 01: 42, 02: 51, 03: 44, 04: 59, 05: 71, 06: 44, 07: 20, 08: 20, 09: 16, 10: 20.

## 6. Current Split Audit

The evaluated pipeline is true ten-fold subject-wise LOSO. Each fold has one test
subject, one validation subject drawn only from the remaining subjects, and eight
training subjects. See `reports/evaluation/loso_protocol.csv`.

## 7. True LOSO Protocol

Subject split precedes loading/resampling. Normalization is fitted only on each fold's
training manifest; augmentation is enabled only for training. Manifest and normalization
hashes are checked before model loading and inference.

## 8. Baseline Results

Strict Majority, Linear SVM, MLP and simple LSTM baselines are complete under
the exact 387-sample LOSO protocol. See `PHASE_4_7_BASELINE_SUMMARY.md` and the
machine-readable `loso_majority.json`, `loso_linear_svm.json`,
`loso_strict_mlp.json` and `loso_strict_lstm.json` artifacts. Phase 4.7 passes
its protocol/acceptance requirements; this does not imply strong performance.

## 9. RehabMotionNet Results

| Metric | Mean | Std | Min | Max |
|---|---:|---:|---:|---:|
| Exercise Macro-F1 | 0.3544 | 0.2704 | 0.0238 | 0.7392 |
| Exercise accuracy | 0.4379 | 0.2335 | 0.0500 | 0.7458 |
| Exercise weighted-F1 | 0.4985 | 0.2230 | 0.0952 | 0.7879 |
| Completion Macro-F1 | 0.4828 | 0.1083 | 0.2929 | 0.6636 |
| Completion accuracy | 0.5024 | 0.1032 | 0.3000 | 0.6667 |

## 10. Per-Fold and Per-Subject Results

Machine-readable per-fold results are in `loso_upper_limb_v2.json`; the derived
per-subject table is `loso_per_subject.csv`. No difficult fold is removed.

## 11. Generalization and Failure Analysis

Performance varies strongly by subject. Subjects 07-10 contain only one canonical
exercise each after source/quality constraints, so four-class Macro-F1 correctly
penalizes the unavailable class coverage. This is the dominant scientific limitation.

## 12. Limitations

Only ten subjects and 387 accepted samples are available. One seed (42) was used.
Completion labels mean Complete/Incomplete, not clinical correctness. The current
runtime environment is Python 3.11.9, PyTorch 2.5.1+cu121 and MediaPipe 0.10.9,
which does not match the canonical V3.1 lock (PyTorch 2.7.0+cu126, MediaPipe 1.0.1).
Existing model metrics must therefore be described with their actual environment.

## 13. Final Decision

**E. DATASET TOO SMALL / INSUFFICIENT FOR STRONG CONCLUSION.**

The real-data pipeline and strict LOSO protocol are valid for research evaluation,
but the sample/subject/class coverage is insufficient for a clinical or robust
generalization claim. Production remains unchanged.

## 14. Post-Phase 4.7 Research

The complete six-way ablation matrix is in `ABLATION_SUMMARY.md`. An exploratory
post-ablation simplified model reached exercise Macro-F1 0.3945, but its fold-wise
gain was not stable and its design used the observed ablation results. It is not
eligible for production promotion without predeclared multi-seed or fresh-subject
confirmation.
