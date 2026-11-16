# RehabAI Phase 4.7 — Stage 2 Pipeline Hardening

## Mission

Implement and test the infrastructure required for trustworthy real-data provenance and True LOSO evaluation.

Workspace root:

`D:\PhucHoiChucNangTay`

Stage 1 has been accepted with reviewer corrections. Phase 4.7 itself still fails. Stage 2 must make the pipeline fail closed against mock, rejected, missing, unverified, or leaked data.

This stage permits focused source-code and test changes. It does not permit full extraction, model training, scientific evaluation, or deletion of existing data.

## Accepted Stage 1 facts

Treat these as the current baseline, but verify affected code before editing:

- 491 Upper Limb Stroke source-video records across 10 subjects.
- Extraction log: 469 Mock success, 12 non-Mock MediaPipe success, and 10 non-Mock MediaPipe rejected.
- Interim features: 469 Mock plus 12 non-Mock MediaPipe candidates.
- Processed features: 469 Mock plus only 2 non-Mock MediaPipe candidates.
- Ten successful non-Mock interim features do not currently have processed counterparts.
- Split manifest: 411 train, 40 validation, and 40 test rows.
- Loadable processed samples: 401 train, 40 validation, and 40 test.
- Current split is fixed subject-wise, not True LOSO.
- Existing global normalization and self-supervised pretraining can see held-out subjects.
- Existing metrics and checkpoints are not valid scientific results.

Do not classify a non-Mock extraction as scientifically verified real data merely from its extractor name. Use `REAL_CANDIDATE` until Stage 3 validates feature contents and source linkage.

## Absolute prohibitions

1. Do not delete, move, rename, overwrite, or clean existing data.
2. Do not alter anything under `RehabAI_Datasets_FULL_VERIFIED`.
3. Do not alter existing files under:
   - `rehabai/data/interim/keypoints`
   - `rehabai/data/processed/keypoints`
   - `rehabai/training/checkpoints`
   - `rehabai/training/runs`
   - `rehabai/results`
   - `rehabai/artifacts`
4. Do not delete or repurpose `mock_extraction.py`. It may remain for development, but research selection must reject its outputs.
5. Do not run `extract_keypoints.py`, `mock_extraction.py`, or `process_features.py` on the real dataset.
6. Do not run pretraining, baseline training, RehabMotionNet training, evaluation, inference, backend, frontend, npm, or Docker.
7. Do not install or update dependencies.
8. Do not access the network.
9. Do not change model architecture.
10. Do not change or report scientific metrics.
11. Do not use `rm`, `Remove-Item`, `git reset`, `git clean`, `git checkout`, `git restore`, or another destructive command.
12. Do not generate research LOSO folds from the current mixed dataset.
13. Do not continue to Stage 3.

If a required operation would violate these rules, stop and report the blocker.

## Required workflow

1. Read all relevant Stage 1 specifications, source files, tests, manifests, and schemas.
2. Inspect `git status` and existing diffs before editing. Preserve all unrelated user changes.
3. Write a short implementation plan in the conversation or Antigravity Artifact.
4. Implement only the bounded Stage 2 work below.
5. Run targeted unit tests using temporary fixture data only.
6. Inspect the final diff and verify that protected data directories were unchanged.
7. Produce the required Stage 2 report and stop.

Do not pause for approval after the plan unless the work requires destructive action, network access, dependency installation, or a material scope change.

## 1. Canonical provenance infrastructure

Add a deterministic provenance builder for `.npz` features. Prefer a new script or module rather than replacing the legacy extraction scripts.

The canonical output schema must support at least:

- `sample_id`
- `dataset`
- `source_record_id`
- `source_video_path`
- `source_video_exists`
- `source_video_size`
- `source_video_sha256`
- `subject_id`
- `exercise_id`
- `completion_label`
- `label_source`
- `subject_source`
- `extraction_log_present`
- `extraction_status`
- `extractor_version`
- `generation_script`
- `generation_timestamp`
- `interim_path`
- `interim_exists`
- `processed_path`
- `processed_exists`
- `feature_format`
- `feature_shape`
- `frame_count`
- `quality_gate_passed`
- `data_status`
- `exclusion_reasons`

Use explicit status values:

- `MOCK`
- `REJECTED`
- `REAL_CANDIDATE`
- `REAL_VERIFIED`
- `UNKNOWN`

Stage 2 must not promote any current sample to `REAL_VERIFIED`. That promotion belongs to Stage 3 after source and feature verification.

Minimum fail-closed classification rules:

- Extractor or generation script containing Mock/synthetic markers → `MOCK`.
- Extraction status other than success → `REJECTED`.
- Non-Mock success with source video and expected feature present → `REAL_CANDIDATE`.
- Missing, contradictory, or untraceable evidence → `UNKNOWN`.

Hash computation must be optional. The builder may support a `--compute-video-hashes` option, but Stage 2 tests must use tiny fixtures and must not hash all 491 videos.

Use `feature_provenance.csv` or an equivalently format-neutral name. Do not pretend `.npz` files are `.h5`. Keep any legacy Phase 4.7 filename requirement documented as a schema migration issue.

The module must have no filesystem-writing side effects on import.

## 2. Research eligibility gate

Create one shared, reusable eligibility function or policy. Research training/evaluation must accept a sample only when all conditions hold:

```text
data_status == REAL_VERIFIED
extraction_status == success
quality_gate_passed == true
source_video_exists == true
processed_exists == true
subject_id is valid
exercise_id is valid
```

`status == success` alone is never sufficient because Mock rows also use success.

The gate must return explicit exclusion reasons and fail if zero eligible samples remain. It must never silently fall back to Mock, candidate, unknown, rejected, or missing samples.

Add tests proving that `MOCK`, `REJECTED`, `REAL_CANDIDATE`, `UNKNOWN`, missing-source, and missing-feature rows are excluded.

## 3. True LOSO manifest generator

Implement a new LOSO generator rather than silently changing the meaning of the legacy fixed-split output.

Input must be the canonical provenance table after the research eligibility gate.

Requirements:

- Normalize subject IDs consistently as strings, preserving stable two-digit IDs where applicable.
- Sort subjects and samples deterministically.
- Require unique `sample_id` and source-video identity.
- For `N` eligible subjects, generate exactly `N` outer folds.
- For the Phase 4.7 research profile, assert exactly 10 eligible subjects before producing official manifests.
- Outer fold `i`: one subject is TEST.
- Validation subject or subjects must be selected only from the remaining nine outer-training subjects.
- Actual model-fitting TRAIN subjects exclude both TEST and validation subjects.
- Use a deterministic documented validation strategy and seed. A rotating single validation subject is acceptable for the initial protocol if it is stable and never equals the test subject.
- Every subject appears as outer TEST exactly once.
- No subject appears in more than one split within a fold.
- No `sample_id`, source video, or source-video-derived group crosses splits within a fold.
- Generate video-level manifests only. Do not create windows in Stage 2.
- Include protocol version, seed, test subject, validation subjects, train subjects, input-provenance hash, and creation metadata in fold metadata.

Design output paths for future use, for example:

```text
rehabai/data/indexes/loso/fold_01/manifest.csv
rehabai/data/indexes/loso/fold_01/metadata.json
```

Do not generate these official outputs from the current mixed dataset. Unit tests must generate them in temporary directories using synthetic metadata fixtures clearly marked as test fixtures.

## 4. Split-before-windowing contract

Make the data-loading contract explicit:

```text
verified video-level provenance
→ outer subject split
→ train/validation/test video manifests
→ optional window generation inside each split
```

If no sliding windows currently exist, document that current code resamples a whole sequence. Add interfaces or guards so future windowing must receive an already selected fold and split.

Add a test showing that multiple windows or derived rows from one source video cannot cross train, validation, and test.

Do not implement large-scale window materialization in this stage.

## 5. Fold-specific train-only normalization

Remove research dependence on a single globally fitted normalization schema.

Implement fold-specific fitting with these properties:

- The fit operation receives only the current fold's TRAIN sample IDs or TRAIN manifest.
- Validation and TEST samples cannot be passed to the fit operation without raising an error.
- Store mean, standard deviation, feature count, sample count, frame count, fold ID, training subjects, seed, and provenance-manifest hash.
- Replace near-zero standard deviations safely.
- Validation and TEST use the stored TRAIN transformation without refitting.
- Preserve the existing global normalization file as legacy; do not overwrite or delete it.
- Future fold artifacts must have distinct paths.

Use tiny fixtures whose train and test distributions are deliberately different. Assert that fitted values equal TRAIN statistics only.

## 6. Dataset and SSL fail-closed loading

Harden `RehabDataset` and `SSLRehabDataset` or add strict research-mode replacements.

Research-mode requirements:

- Require an explicit fold manifest and split.
- Do not discover research samples through unrestricted `glob("*.npz")`.
- Do not silently skip missing files; raise a clear integrity error or return a preflight failure report before training.
- Reject samples that fail the research eligibility gate.
- Reject duplicate samples and conflicting source-video assignments.
- Augmentation may be enabled only for TRAIN.
- Requesting augmentation for validation or TEST must raise an error.
- SSL pretraining may load only current-fold TRAIN subjects.
- Outer TEST and validation subjects must not enter SSL pretraining.
- No fallback to the entire processed directory.

Preserve legacy/development behavior only when it is explicitly selected and clearly marked unsafe for research. Research mode must be the default for future Phase 4.7 scripts.

## 7. Training-entry guards

Without running training, correct or guard incompatible entry points:

- `train.py` must not pass `extraction_quality.csv` where `RehabDataset` expects a split manifest.
- Training entry points must require an explicit fold, manifest, and fold-normalization artifact for research runs.
- A test or preflight function must reject a missing fold, missing columns, missing files, mixed data, and a global legacy normalizer.
- Proposed and baseline trainers must enable augmentation only for TRAIN when augmentation is requested.
- Do not force augmentation to be enabled; disabling augmentation is valid.

Do not alter model architecture or run a training batch.

## 8. Evaluation safety fixes

Harden evaluation code without performing evaluation:

- Require an explicit TEST split for final outer-fold evaluation.
- Do not silently evaluate validation while calling it test.
- Missing checkpoint must raise a clear error. Never evaluate untrained weights as a result.
- Calculate classification metrics with the complete expected class-label list so absent classes remain visible.
- Keep confusion-matrix label order explicit.
- Apply the correct transformation to completion logits before MAE/RMSE when the target is binary `[0,1]`.
- Record fold ID, test subject, checkpoint identity/hash, seed, and normalization artifact identity.
- Add a guard preventing repeated test use for model selection in the orchestration API or document the one-shot evaluation boundary clearly.

Test metric helpers with small in-memory arrays only. Do not load real checkpoints or datasets.

## 9. Required tests

Add focused tests covering at least:

1. Provenance reconciliation by output filename.
2. Fail-closed status classification.
3. Research eligibility exclusion reasons.
4. Ten subjects produce ten outer folds.
5. Each subject is TEST exactly once.
6. Train, validation, and TEST subjects are disjoint in every fold.
7. Sample and source-video groups never cross splits.
8. Invalid or missing subject IDs fail.
9. Mock, rejected, candidate, unknown, and missing features cannot enter research manifests.
10. Normalization fits TRAIN only.
11. SSL pretraining receives TRAIN only.
12. Validation/TEST augmentation is rejected.
13. Missing feature files cause a preflight failure.
14. Missing checkpoints cause evaluation failure.
15. Macro metrics include all expected classes.
16. Completion logits are transformed correctly.
17. Legacy `extraction_quality.csv` cannot be mistaken for a split manifest.

Tests must use temporary directories and tiny generated arrays/CSV fixtures. Do not read or modify the 491-video dataset during tests.

## 10. Permitted verification

Permitted:

- Targeted unit tests for new or changed Stage 2 modules.
- Read-only source searches.
- Static import or syntax checks that do not load models, checkpoints, or real datasets.
- Test fixtures in the test framework's temporary directory.
- `git status` and `git diff`.

Not permitted:

- Full test suites that start services or training.
- Extraction/preprocessing against real data.
- GPU model execution.
- Model export.
- Real evaluation.

If a dependency is missing, report it. Do not install it.

## 11. Stage 2 acceptance criteria

Stage 2 passes only when:

- Existing video, interim, processed, checkpoint, result, and artifact files are unchanged.
- Provenance code distinguishes Mock, rejected, candidate, verified, and unknown states.
- Current samples cannot become `REAL_VERIFIED` automatically.
- Research eligibility fails closed.
- LOSO generation uses verified video-level samples only.
- Ten-subject fixtures generate exactly ten valid outer folds.
- Test subjects never enter training, validation fitting, normalization, or SSL pretraining.
- Train-only normalization is proven by tests.
- Dataset loaders do not silently skip missing research files.
- Validation/TEST augmentation is blocked.
- Evaluation cannot use validation as test or untrained weights silently.
- Targeted tests pass.
- No extraction, training, or actual evaluation was run.

## Required final report

Return the report in the Antigravity conversation or an Artifact, not as a repository report.

Use exactly these sections:

# Phase 4.7 Stage 2 Pipeline Hardening Report

## 1. Outcome

State `PASS`, `PARTIAL`, or `FAIL` for Stage 2. Do not claim Phase 4.7 passes.

## 2. Initial repository state

Include git status and pre-existing changes.

## 3. Implementation summary

Explain the final behavior.

## 4. Files created or modified

List every file and why it changed.

## 5. Provenance and eligibility design

Document statuses, required columns, and fail-closed rules.

## 6. True LOSO protocol

Document subject selection, validation strategy, determinism, grouping, and metadata.

## 7. Train-only preprocessing and SSL isolation

Explain how outer test and validation subjects are excluded.

## 8. Training and evaluation guards

List every unsafe fallback removed or blocked.

## 9. Tests executed

Provide exact commands and complete pass/fail counts.

## 10. Protected-data verification

Confirm protected data directories were not changed.

## 11. Remaining limitations and blockers

Include missing dependencies or unresolved ambiguity.

## 12. Diff summary

Summarize the final git diff without including unrelated user changes.

## 13. Stage 3 readiness

State whether the pipeline is ready for controlled real extraction. Do not start it.

## 14. Compliance statement

Explicitly confirm:

- No existing dataset feature was deleted, moved, renamed, or overwritten.
- No full extraction or preprocessing was run.
- No pretraining, training, evaluation, inference, export, backend, frontend, npm, or Docker command was run.
- No dependency was installed.
- No network access was used.
- No model architecture was changed.
- Stage 3 was not started.

## Stop condition

After delivering the Stage 2 report, stop completely. Wait for independent review before Stage 3.
