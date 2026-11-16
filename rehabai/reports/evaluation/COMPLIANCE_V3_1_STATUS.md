# Master Prompt V3.1 compliance status

This file records verified status; it is not a claim that every product
acceptance test has passed.

## Completed

- Real Upper Limb Stroke audit: 491 source videos, four canonical exercises.
- MediaPipe extraction and upper-limb quality gate: 387 eligible samples.
- Subject-wise 10-fold LOSO with train-only normalization and provenance hashes.
- RehabMotionNet upper-limb v2 evaluation: exercise Macro-F1 0.3544,
  accuracy 0.4379.
- Strict export bundle: `artifacts/model_v2`.
- Backend API smoke test and frontend production build.
- Automated Python tests: 132 passed, 1 skipped (2026-09-14).
- Phase 4.7 real-data trace tables and report generated from the signed 387-sample
  upper-limb manifest; all source and processed SHA-256 values were rechecked.
- Phase 4.7 strict baselines completed: Majority, Linear SVM, MLP and simple LSTM,
  with ten held-out-subject folds and completion/exercise metrics.
- RehabMotionNet ablation matrix completed under the same protocol: Full, minus
  hand, minus kinematic, minus contrastive, minus MS-TCN and minus attention.
- Exploratory optimized-v1 (minus attention + contrastive) reached exercise
  Macro-F1 0.3945, but was selected post-ablation and is not promoted.
- Focused Python test suite: 49 passed, 1 skipped (2026-09-15).

<!-- MULTISEED_CONFIRMATION_START -->
## Multi-seed confirmation status

- Full v2 and Optimized-v1 were evaluated over strict 10-fold LOSO with
  seeds 42, 7 and 2026 (30 paired fold-seed comparisons).
- Aggregate paired Macro-F1 delta: +0.0628; W/T/L=17/4/9; robustness `directionally_consistent_across_seeds`.
- Production was not changed. The same 10 subjects are reused across seeds,
  so fresh-subject validation remains necessary.
<!-- MULTISEED_CONFIRMATION_END -->

## Still environment-dependent

- Docker build/up, browser camera and WebSocket E2E require Docker Desktop and
  a browser runtime. Docker daemon was unavailable during this audit.
- Clinical correctness/error-type evaluation requires an ethics-approved,
  expert-annotated extension dataset (Phase 10).
- The installed runtime is Python 3.11.9, PyTorch 2.5.1+cu121 and MediaPipe
  0.10.9. This differs from the V3.1 canonical lock (PyTorch 2.7.0+cu126 and
  MediaPipe 1.0.1); new adapter runs are therefore marked exploratory.

## Scientific limitation

The 10-subject dataset is small and folds 07-10 have restricted class
coverage. The reported metrics are therefore research results, not a clinical
performance guarantee. The completion head is not promoted to production.
The historical `PHASE_4_7_FINAL_REPORT.md` describes the earlier mock-data
state; `PHASE_4_7_REAL_DATA_REPORT.md` is the current Stage 3 real-data report.
