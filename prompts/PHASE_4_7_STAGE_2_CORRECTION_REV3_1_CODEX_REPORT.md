# PHASE 4.7  STAGE 2 CORRECTION REV3.1 CODEX COMPLETION REPORT

## 1. Executive conclusion

- Implementation status: **PASS**
- Stage 2 strict-pipeline code readiness: **READY**
- Stage 3 data-verification readiness: **READY WITH REQUIRED VERIFICATION KEY**
- Model training/evaluation on research data: **NOT YET AUTHORIZED**
- Dataset status was not changed by this work.

The remaining REV3.1 implementation defects were corrected. The research pipeline now requires a secret HMAC verification key before a record can receive or retain REAL_VERIFIED. All supervised/SSL dataset paths perform logical, signed-provenance, physical-file, checksum, fold, split, normalization and exact-shape checks.

## 2. Files created

- rehabai/training/datasets/feature_validation.py
- rehabai/scripts/verify_provenance.py
- rehabai/tests/test_rev31_completion.py
- PHASE_4_7_STAGE_2_CORRECTION_REV3_1_CODEX_REPORT.md

## 3. Files modified

- rehabai/shared/provenance.py
- rehabai/training/datasets/rehab_dataset.py
- rehabai/training/datasets/ssl_dataset.py
- rehabai/training/normalization.py
- rehabai/training/checkpoint_utils.py
- rehabai/training/model_registry.py
- rehabai/training/baseline_trainer.py
- rehabai/training/proposed_trainer.py
- rehabai/scripts/generate_loso.py
- rehabai/scripts/evaluate.py
- rehabai/scripts/export_model.py
- rehabai/tests/test_strict_pipeline.py
- rehabai/shared/tests/test_correction_stage2.py
- rehabai/shared/tests/test_evaluation.py
- rehabai/shared/tests/test_loso.py
- rehabai/shared/tests/test_normalization.py
- rehabai/shared/tests/test_provenance.py

Temporary .rev31 edit scripts and patch files were removed after verification.

## 4. Acceptance matrix

| Group | Status | Evidence |
|---|---|---|
| Training call-site compatibility | PASS | train.py, baseline_trainer.py, pretrain.py, and proposed_trainer.py pass source_dir and manifests explicitly. Proposed trainer strict bootstrap is exercised with epochs=0. |
| REAL_VERIFIED authority and physical containment | PASS | provenance.py requires REHABAI_PROVENANCE_HMAC_KEY, signs canonical record plus evidence, uses resolved-path containment, retains dataset-relative identities, requires both roots and verifies both SHA-256 values. |
| Exact feature shape contract | PASS | Shared validator enforces pose (T,33,4), each hand (T,21,3), kinematics (T,12), common nonzero frame count, real numeric dtype and finite values. |
| Strict trainer/checkpoint loading | PASS | Proposed contrastive encoder uses strict checkpoint metadata; checkpoint loading uses weights_only=True; metadata mismatch tests pass. |
| Real model registry | PASS | Registry validates per-model config and real forward passes succeed for MLP, LSTM, BiLSTM, TCN, ST-GCN, RehabModel, RehabMotionNetEncoder and RehabMotionNet. |
| Evaluator preflight and atomic output | PASS | Every job's checkpoint, normalization, fold, manifest, physical files and dataset shapes are preflighted before inference. JSON output uses a same-directory temporary file plus os.replace. |
| Strict atomic exporter | PASS | Export requires explicit model-config and class-mapping JSON, verifies them against the checkpoint, builds in a staging directory, preserves an existing bundle on failure and publishes with rollback. |
| Test quality and coverage | PASS | No empty pass tests, no mocked model constructors, physical fixtures use real files and SHA-256, and boundary monkeypatches only observe inference or inject export failure. |

## 5. Verification commands

Python compilation:

    python -m py_compile shared\provenance.py training\datasets\feature_validation.py training\datasets\rehab_dataset.py training\datasets\ssl_dataset.py training\normalization.py training\checkpoint_utils.py training\model_registry.py training\train.py training\baseline_trainer.py training\pretrain.py training\proposed_trainer.py scripts\generate_loso.py scripts\verify_provenance.py scripts\evaluate.py scripts\export_model.py

Exit code: 0.

Test collection:

    python -m pytest shared\tests tests --collect-only -q

Result: **109 tests collected**. Exit code: 0.

Full relevant Python test suite:

    python -m pytest shared\tests tests -q

Result: **108 passed, 1 skipped, 1 warning**. Exit code: 0.

The skipped test is the Windows symlink-escape case when the host does not grant permission to create a symlink. Resolved-path containment and sibling-prefix escape are covered and passed. The warning is PyTorch's Transformer nested-tensor performance warning; it is not a correctness or leakage failure.

Unsafe-pattern scan:

    rg -n --glob '*.py' "expected_architecture_signature=None|from unittest.mock|unittest.mock|pass" shared\tests tests training scripts

No matching unsafe pattern was found.

## 6. Required operational step before Stage 3

Generate and securely retain a random secret with at least 32 characters and expose it to verification, LOSO generation, normalization, datasets, evaluation and training through the environment variable REHABAI_PROVENANCE_HMAC_KEY.

Do not store the real key in source control or in the provenance CSV. The same key must verify the signed manifest throughout one research lineage. If it is missing or different, the pipeline fails closed.

Use scripts/verify_provenance.py to promote physically verified REAL_CANDIDATE records. This command was implemented and tested with temporary physical files, but it was not run against the real dataset in this task.

## 7. Compliance statement

- No MediaPipe extraction was run.
- No real dataset file was deleted, moved or overwritten.
- No baseline, pretraining, RehabMotionNet or LOSO research training was run.
- No real checkpoint evaluation was run.
- Tests used temporary local fixtures only.
- Existing mock/synthetic research artifacts were not promoted to REAL_VERIFIED.
