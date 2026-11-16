# RehabAI Phase 4.7 — Stage 1 Correction Request

## Required action

The Stage 1 report was reviewed and was not accepted. Revise the audit report through read-only inspection only. Do not start Stage 2.

## Mandatory restrictions

1. Do not create, edit, rename, move, delete, format, or overwrite workspace files.
2. Do not run Python or any project program.
3. Do not run tests, extraction, preprocessing, training, evaluation, inference, frontend, backend, npm, or Docker.
4. Do not execute destructive commands.
5. Do not use `rm`, `Remove-Item`, `git checkout`, `git reset`, `git clean`, `git restore`, `git stash`, or `git commit`.
6. Return the revised report in the Antigravity conversation or an Antigravity Artifact. Do not save the report in the repository.
7. Stop after delivering Revision 2.

## Documents that must be read

Read the original task specification again:

@ANTIGRAVITY_PHASE_4_7_STAGE_1_READ_ONLY_AUDIT.md

Also read every previously omitted required file, including:

- `Prompt Phase 4.6 – Full 491 Video Extraction & LOSO Training.md`
- `rehabai/scripts/audit_dataset.py`
- `rehabai/scripts/evaluate_baselines.py`
- `rehabai/training/datasets/ssl_dataset.py`
- `rehabai/training/baseline_trainer.py`
- `rehabai/training/proposed_trainer.py`
- `rehabai/training/train.py`
- `rehabai/shared/normalization_schema.json`
- `rehabai/shared/tests/test_splits.py`
- `rehabai/shared/tests/test_preprocessing.py`

## Corrections required

### 1. Correct the data-status conclusion

Do not classify the complete dataset as `SYNTHETIC` solely because `mock_extraction.py` exists or because most extraction-log rows are Mock.

Report separate status for source videos, extraction-log records, interim features, and processed features.

Create a read-only reconciliation table with:

- `extractor_version`
- `status`
- `log_rows`
- `interim_exists`
- `processed_exists`
- `missing_interim`
- `missing_processed`

Match `extraction_quality.csv.output` to actual filenames. If individual processed features cannot be traced conclusively, classify the processed-feature set as `MIXED` or `UNKNOWN`, with the exact reason.

Distinguish 12 non-Mock MediaPipe success records from 10 non-Mock MediaPipe rejected records. Do not describe all 22 as successful real extractions.

### 2. Reconcile manifest rows with loadable samples

For each `train`, `val`, and `test` split, report:

- Rows in `split_manifest.csv`.
- Rows whose `sample_id` exists in `data/processed/keypoints`.
- Rows whose processed feature is missing.
- Subjects and exercise classes among the loadable rows.

Explain that manifest size is not automatically equal to the number of samples loaded by `RehabDataset`.

Check whether `split_dataset.py` includes rejected extraction rows merely because the `output` field is non-null.

### 3. Correct preprocessing status

If `process_features.py` collects kinematics from every success record and calculates one global mean/std before subject-wise folds, mark `Preprocessing train-only` as `FAIL`, not `UNKNOWN`.

Identify every consumer of the global normalization schema.

### 4. Correct the validation-leakage conclusion

Do not call Subjects 07 and 08 a validation leakage merely because they are excluded from training in the current fixed split.

Explain separately:

- The current fixed train/validation/test split may use Subjects 07–08 for validation and Subjects 09–10 for final testing.
- This split is still not True LOSO.
- A future outer LOSO fold must create validation only from the nine non-test subjects.

Only claim test leakage when there is evidence that the outer test subject or its derived information influences training, preprocessing, pretraining, threshold selection, early stopping, or model selection.

### 5. Correct label and subject provenance status

Check both `audit_dataset.py` and `split_dataset.py`.

Determine whether subject ID, exercise ID, and completion labels are read from official metadata or parsed from filenames and directory names. Determine whether existing master CSV files are independently sourced metadata or generated indexes based on paths.

Do not mark label or subject provenance `PASS` when it is inferred from paths and no independent provenance manifest exists. Use `PARTIAL`, `FAIL`, or `UNKNOWN` according to the evidence.

### 6. Describe the mock shortcut accurately

Inspect how `mock_extraction.py` calculates `base_val`.

Explain that if `base_val` depends directly on `exercise_id`, the model can learn an artificial label-correlated shortcut. Do not describe this merely as learning random noise.

### 7. Complete the pretraining and augmentation audit

Inspect `ssl_dataset.py`, `pretrain.py`, `rehab_dataset.py`, and every trainer.

Report:

- Whether self-supervised pretraining loads all processed feature files.
- Whether an outer test subject can enter pretraining.
- Whether pretrained weights are used by RehabMotionNet.
- Which supervised training paths enable augmentation.
- Whether augmentation is disabled for validation and test in every path.

Do not mark `Augmentation train-only` as `PASS` without checking all training paths.

### 8. Complete the evaluation audit

Inspect `evaluate_baselines.py` and report whether:

- It loads `split="val"` while naming the operation as test evaluation.
- It continues with untrained weights when a checkpoint is missing.
- `classification_report` excludes absent classes from macro metrics.
- Confusion matrices use all expected class labels.
- Completion predictions receive the correct transformation before MAE/RMSE.
- Existing results can represent only a subset of expected classes.

Inspect `train.py` and report whether its default index argument is compatible with the columns expected by `RehabDataset`.

### 9. Correct unsupported acceptance decisions

Reassess at least these rows:

- Data status.
- Label provenance.
- Subject provenance.
- Preprocessing train-only.
- Augmentation train-only.
- No test-set tuning.
- No metric manipulation.
- Final report generated.

Use `PASS` only when direct evidence proves the criterion. Absence of discovered evidence is not sufficient proof.

### 10. Expand leakage and shortcut risks

Include all confirmed or plausible risks found in:

- Global normalization.
- Self-supervised pretraining.
- Mock features correlated with labels.
- Path-derived labels and subject IDs.
- Missing processed samples and resulting class imbalance.
- Validation being reported as test.
- Absent classes being omitted from macro metrics.
- Evaluation with missing checkpoints or untrained weights.
- Random fallback splits.

Rank each as `Critical`, `High`, `Medium`, or `Low`, and distinguish confirmed defects from risks requiring further verification.

### 11. Replace the Stage 2 plan

The revised Stage 2 plan must follow these boundaries:

- Do not delete old feature files.
- Do not delete `mock_extraction.py`.
- Do not propose `rm` or `Remove-Item` commands.
- Preserve existing data in place or plan a versioned/quarantine strategy.
- Stage 2 is limited to implementing and testing safe provenance, dataset-selection, fold-generation, and train-only preprocessing infrastructure.
- Do not run full extraction in Stage 2.
- Do not run full training or evaluation in Stage 2.
- Separate later extraction, verification, one-seed LOSO, and multi-seed evaluation into later stages.
- Every future destructive operation must require explicit user approval and an exact target inventory.

### 12. List commands exactly

The `Commands executed` section must contain each complete command. Do not use `...` placeholders.

## Required revised report

Use the title:

`# Phase 4.7 Stage 1 Read-Only Audit — Revision 2`

Retain all 12 sections required by the original Stage 1 specification. Replace inaccurate conclusions rather than appending a short correction note.

The final compliance statement must explicitly confirm:

- No workspace file was created or modified.
- No project code was executed.
- No extraction, preprocessing, training, evaluation, or inference was executed.
- No destructive command was executed.
- Stage 2 was not started.

After delivering Revision 2, stop completely and wait for independent review.
