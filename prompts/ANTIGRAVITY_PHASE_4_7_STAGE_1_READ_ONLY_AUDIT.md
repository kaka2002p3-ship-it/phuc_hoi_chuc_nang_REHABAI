# RehabAI Phase 4.7 — Stage 1 Read-Only Audit

## Mission

Audit the actual state of the RehabAI data and evaluation pipeline before any repair, extraction, preprocessing, training, or model improvement.

Workspace root:

`D:\PhucHoiChucNangTay`

This stage is evidence gathering and planning only. Do not implement fixes.

## Mandatory safety and scope rules

1. Operate in strict read-only mode.
2. Do not create, edit, format, rename, move, delete, or overwrite any workspace file.
3. Do not run Python or any project program.
4. Do not run tests, extraction, preprocessing, training, evaluation, inference, backend, frontend, npm, or Docker.
5. Do not modify or load checkpoints through project code.
6. Do not use `git checkout`, `git reset`, `git clean`, `git restore`, `git stash`, or `git commit`.
7. Do not continue to Stage 2.
8. Treat existing reports as claims that must be checked against repository evidence.
9. Do not present old metrics as scientifically valid results.
10. Mark conclusions `UNKNOWN` when repository evidence is insufficient.
11. Do not inspect the binary contents of every video, checkpoint, or feature file. Use filesystem metadata and existing manifests for this inventory stage.
12. Return the report in the Antigravity conversation or an Antigravity Artifact. Do not save the report inside the repository.

Permitted operations are read-only searches and inspection, including `rg`, `rg --files`, `Get-Content`, `Get-ChildItem`, `Measure-Object`, `Import-Csv`, `Select-Object`, `Group-Object`, `git status`, `git diff`, and `git log`.

## Read these files first

1. `Prompt Phase 4.7 – Verify Real Data + True LOSO.md`
2. `Prompt Phase 4.6 – Full 491 Video Extraction & LOSO Training.md`
3. `rehabai/reports/evaluation/PHASE_4_7_FINAL_REPORT.md`
4. `rehabai/reports/data_provenance/mock_data_audit.md`
5. `rehabai/scripts/mock_extraction.py`
6. `rehabai/scripts/extract_keypoints.py`
7. `rehabai/scripts/process_features.py`
8. `rehabai/scripts/split_dataset.py`
9. `rehabai/scripts/evaluate_baselines.py`
10. `rehabai/scripts/audit_dataset.py`
11. `rehabai/training/datasets/rehab_dataset.py`
12. `rehabai/training/datasets/ssl_dataset.py`
13. `rehabai/training/baseline_trainer.py`
14. `rehabai/training/proposed_trainer.py`
15. `rehabai/training/train.py`
16. `rehabai/training/configs/split.yaml`
17. `rehabai/data/indexes/extraction_quality.csv`
18. `rehabai/data/indexes/upper_limb_master.csv`
19. `rehabai/data/indexes/splits/split_manifest.csv`
20. `rehabai/shared/normalization_schema.json`
21. Tests and documents directly related to splitting, preprocessing, and Phase 4.7.

Exclude `node_modules`, generated dependency files, frontend code unrelated to Phase 4.7, and large binary contents.

## Audit tasks

### 1. Data inventory

Report:

- Number of Upper Limb Stroke source videos.
- Number of subjects and videos per subject.
- Number of videos per exercise.
- Number of interim `.npz` files.
- Number of processed `.npz` files.
- Number of `.h5` files, if any.
- Rows in `extraction_quality.csv`, grouped by `extractor_version` and `status`.
- Samples in train, validation, and test.
- Subjects assigned to each split.
- Existing checkpoints, metrics, confusion matrices, and Phase 4.7 reports.

Keep these states separate:

- Source video exists.
- Extraction log exists.
- Interim feature exists.
- Processed feature exists.
- Feature is proven to originate from real video.
- Feature provenance is unknown.

Do not treat one state as proof of another.

### 2. Mock and synthetic data audit

Search relevant project sources for:

- `random`
- `np.random`
- `torch.rand`
- `torch.randn`
- `synthetic`
- `mock`
- `dummy`
- `placeholder`
- `fake`
- `simulated`

Classify every relevant occurrence as one of:

1. Synthetic input data generation.
2. Legitimate train-only augmentation.
3. Model weight initialization.
4. Dummy input used only for export or latency measurement.
5. Random split or behavior that may cause leakage.

Do not classify all features as synthetic merely because `mock_extraction.py` exists. Use the extraction log, feature inventory, naming, and traceability evidence. The final data-status classification must be one of `REAL`, `SYNTHETIC`, `MIXED`, or `UNKNOWN`, with its evidence and limitations.

### 3. Provenance gaps

Check whether the repository contains and actually populates:

- `reports/data_provenance/h5_provenance.csv`
- `reports/data_provenance/label_provenance.csv`
- Per-subject video/feature/valid/invalid statistics.
- Source video hashes.
- Feature generation timestamps.
- Generation script and version.
- Feature-to-source-video mapping.
- Feature shape and frame count.
- Per-sample `data_status`.

Explicitly report the mismatch if Phase 4.7 requests `.h5` while the implementation uses `.npz`.

### 4. Split and windowing audit

Verify:

- Actual train, validation, and test subjects.
- Whether the current split is fixed subject-wise or True LOSO.
- Whether exactly 10 outer folds exist.
- Whether each fold has one held-out test subject.
- Whether validation is selected only from training subjects.
- Whether windows from one video can cross partitions.
- Whether the current dataset creates sliding windows or resamples an entire video.

If there are not 10 outer folds, state exactly:

`This is a fixed subject-wise split, NOT True LOSO.`

### 5. Preprocessing and pretraining leakage audit

Verify:

- Which samples are used to fit mean, standard deviation, scalers, or other learned preprocessing.
- Whether normalization is calculated before or after subject split.
- Whether each LOSO fold has train-only statistics.
- Whether self-supervised pretraining can see the outer test subject.
- Where augmentation is enabled for train, validation, and test.
- Whether any fallback `random_split` can break subject separation.
- Whether validation or test information influences model selection or feature preparation.

### 6. Label and subject provenance audit

Verify:

- Whether `subject_id` comes from official metadata or filename inference.
- Whether exercise labels come from official metadata or path inference.
- Whether completion labels come from official metadata or path inference.
- Whether any labels are random or generated.
- Missing and invalid labels.
- Whether there are exactly 10 subjects.
- Inconsistencies between values such as `07`, `7`, integer IDs, and string IDs.

### 7. Evaluation audit

Verify:

- Which split `evaluate_baselines.py` actually evaluates.
- Whether a Majority Class baseline exists.
- Whether Random Forest or SVM exists.
- Whether a deliberately simple LSTM exists.
- Whether the current RehabMotionNet has been evaluated with True LOSO.
- Whether per-fold and per-subject metrics exist.
- Whether mean, standard deviation, minimum, and maximum exist.
- Whether the generalization gap exists.
- Whether an aggregated out-of-fold confusion matrix exists.
- Whether multiple seeds exist.
- Whether the test set affects epoch, threshold, architecture, or hyperparameter selection.
- Whether existing metrics and checkpoints originate from real, synthetic, mixed, or unknown data.

### 8. Independently verify these suspected observations

Do not assume these are correct:

- Approximately 491 source videos.
- Approximately 469 Mock-success log rows.
- Approximately 12 non-Mock MediaPipe-success rows.
- Approximately 10 non-Mock MediaPipe-rejected rows.
- Approximately 481 interim `.npz` files.
- Approximately 471 processed `.npz` files.
- Approximately 411 train, 40 validation, and 40 test manifest rows.
- No `.h5` files under `rehabai/data`.
- `process_features.py` may calculate mean/std from all available features.
- `ssl_dataset.py` may load all processed `.npz` files.
- `evaluate_baselines.py` may use `split="val"` while calling it the test set.
- The existing Phase 4.7 report may overstate that all current data is synthetic.

Use independently measured values. Explain every discrepancy.

## Required report format

# Phase 4.7 Stage 1 Read-Only Audit

## 1. Executive conclusion

State:

- Whether Phase 4.7 currently passes.
- Data status: `REAL`, `SYNTHETIC`, `MIXED`, or `UNKNOWN`.
- Actual split type.
- Whether model evaluation is currently allowed.

## 2. Commands executed

List every command executed.

## 3. Files inspected

List the important files inspected.

## 4. Data inventory

Provide tables for video, subject, exercise, interim features, processed features, extraction logs, and split assignments.

## 5. Acceptance-criteria matrix

Create one row for every acceptance criterion in Phase 4.7 with:

- Criterion.
- Status: `PASS`, `PARTIAL`, `FAIL`, or `UNKNOWN`.
- Evidence.
- Exact file and line where applicable.
- Required remediation.

## 6. Confirmed defects

For every defect provide:

- Severity: `Critical`, `High`, `Medium`, or `Low`.
- Evidence with file and line.
- Impact.
- Proposed remediation.

## 7. Existing-report inconsistencies

Compare `PHASE_4_7_FINAL_REPORT.md` with repository evidence. Classify each important claim as:

- Correct.
- Insufficient evidence.
- Incorrect.
- Outdated.

## 8. Actual pipeline diagram

Describe only the pipeline implemented by the current code:

`video → extraction → interim → processing → split → dataset → training → evaluation`

## 9. Leakage and shortcut risks

Rank all confirmed and suspected leakage or shortcut-learning risks by severity.

## 10. Stage 2 implementation plan

Plan repairs without implementing them. Include:

- Files expected to be created or modified.
- Exact intended change to each file.
- Tests to add or update.
- Commands that would be run in Stage 2.
- Rollback conditions.
- Stop conditions.
- Priority order.

## 11. Questions and unknowns

List anything that cannot be established through repository inspection alone.

## 12. Compliance statement

Explicitly confirm:

- No workspace file was created or modified.
- No project code was executed.
- No extraction, preprocessing, training, evaluation, or inference was executed.
- Stage 2 was not started.

## Stop condition

After delivering the report, stop completely. Wait for the user to send the report to an independent reviewer. Do not repair any discovered problem and do not begin Stage 2.
