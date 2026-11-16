# Datanew automated extraction and training report

> **Superseded:** this is the initial run summary. For the independently verified artifact inventory, current LOSO metrics, PASS/FAIL gates, and promotion decision, see [DATANEW_FINAL_VERIFICATION_REPORT.md](DATANEW_FINAL_VERIFICATION_REPORT.md). The final verification report uses the latest regenerated `datanew_ssl_all_full_loso.json` as the source of truth.

Date: 2026-09-18

## Data preparation

- Raw archives were preserved.
- 200 AVI files were extracted to an external workspace on drive E.
- Sparse MediaPipe pose/hand extraction samples 96 frames per video.
- The unlabeled combined quality-gated corpus contains 619 unique videos:
  - AVI archives: 200/200 ready;
  - EHWGesture RGB: 240/240 ready;
  - ex1: 36 ready, 38 too short, 2 high-pose-missing;
  - ex2: 114/114 ready;
  - ex3: 29 ready, 19 high-pose-missing.
- No source gesture/exercise labels were coerced into RehabAI product labels.

## Training protocol

1. Self-supervised contrastive pretraining on unlabeled datanew features.
2. Frozen pretrained encoder supplied to the upper-limb RehabMotionNet.
3. Fine-tuning used only target `REAL_VERIFIED` records.
4. Evaluation used unchanged ten-fold subject-wise LOSO test manifests (387 samples).
5. Checkpoints and reports remain research-only; production artifacts were not modified.

## Strict LOSO results

| Candidate | Exercise Macro-F1 | Exercise accuracy | Completion Macro-F1 | Completion accuracy |
|---|---:|---:|---:|---:|
| Existing upper-limb v2 | 0.3544 | 0.4379 | 0.4828 | 0.5024 |
| AVI-only SSL + full model | 0.3575 | 0.4494 | 0.4900 | 0.5201 |
| Combined 619-video SSL + full model | 0.3518 | 0.4489 | 0.5377 | 0.5612 |
| AVI-only frozen adapter | 0.1589 | 0.2124 | 0.5594 | 0.6059 |

## Decision

- Do not replace the existing exercise classifier: the combined candidate is slightly worse in exercise Macro-F1, and the AVI-only gain is too small for promotion.
- The completion gains are exploratory. The frozen adapter improves completion metrics but severely damages exercise recognition.
- Before promotion, repeat completion experiments over multiple seeds and on fresh subjects, then design separate exercise and completion model-selection gates.
- The environment was `torch 2.5.1+cu121`, not the canonical project profile (`torch 2.7.0+cu126`), so these results remain exploratory.
