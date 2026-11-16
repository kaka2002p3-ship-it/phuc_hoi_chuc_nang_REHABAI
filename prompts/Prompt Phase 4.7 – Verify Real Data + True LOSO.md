# REHABAI — PHASE 4.7
# REAL DATA VERIFICATION + TRUE LOSO VALIDATION

Phase 4.6 đã hoàn thành extraction và training nhưng Final Report có các điểm cần VERIFY trước khi tiếp tục phát triển model.

## MỤC TIÊU

Không được cải tiến model ngay.

Trước tiên phải xác minh:

1. 491 samples có thực sự được tạo từ 491 videos thật hay không.
2. Feature `.h5` có phải dữ liệu thực hay mock/synthetic/random hay không.
3. Split hiện tại có thực sự là LOSO hay chỉ là fixed subject-wise split.
4. Xây dựng TRUE LOSO 10-fold.
5. Chạy baseline.
6. Chạy RehabMotionNet.
7. Chỉ sau khi có kết quả thật mới quyết định có cần ST-GCN, augmentation hoặc giảm model hay không.

---

# 1. CRITICAL DATA VERIFICATION

Kiểm tra nguồn gốc của từng `.h5`.

Phải trace:

`.h5`
→ source `.mp4`
→ video_id
→ subject_id
→ exercise_id
→ original dataset record

Tạo:

`reports/data_provenance/h5_provenance.csv`

Các cột:

h5_path
source_video_path
video_exists
video_size
video_hash
subject_id
exercise_id
label
feature_shape
frame_count
generation_timestamp
generation_script
data_status

---

# 2. DETECT MOCK / SYNTHETIC DATA

Đọc extraction/preprocessing code.

Tìm tất cả:

- random
- np.random
- torch.rand
- torch.randn
- synthetic
- mock
- dummy
- placeholder
- fake data
- simulated data

Đặc biệt xác định xem feature có được tạo bằng:

random coordinates

hoặc:

random labels

hay không.

Nếu phát hiện synthetic/mock data:

STOP MODEL EVALUATION.

Không được dùng metric hiện tại làm kết quả khoa học.

Tạo:

`reports/data_provenance/mock_data_audit.md`

Kết luận rõ:

REAL
hoặc
SYNTHETIC
hoặc
MIXED
hoặc
UNKNOWN

Không được đoán.

---

# 3. VERIFY FEATURE VALUES

Randomly sample ít nhất 20 `.h5`.

Kiểm tra:

- shape
- min
- max
- mean
- std
- NaN
- Inf
- zero ratio
- frame count

So sánh với source video.

Nếu feature sequence không thay đổi hợp lý theo frame:

→ investigate.

Không được chỉ kiểm tra file có tồn tại.

---

# 4. VERIFY LABEL PROVENANCE

Label phải được lấy từ:

`upper_limb_master.csv`

hoặc metadata chính thức của dataset.

Không được:

- random label
- inferred label
- generated label

Tạo:

`reports/data_provenance/label_provenance.csv`

---

# 5. VERIFY SUBJECT PROVENANCE

Mỗi sample phải có subject_id rõ ràng.

Không được suy luận subject từ filename nếu metadata chính thức có subject_id.

Tạo thống kê:

subject_id
video_count
feature_count
valid_count
invalid_count

---

# 6. CURRENT SPLIT AUDIT

Kiểm tra split hiện tại:

TRAIN = 1–6
VAL = 7–8
TEST = 9–10

Nếu đúng, ghi rõ:

"This is a fixed subject-wise split, NOT LOSO."

Không được gọi nó là LOSO.

---

# 7. IMPLEMENT TRUE LOSO

Implement exactly:

N subjects = 10

N folds = 10

Fold i:

TEST = subject i

TRAIN = all subjects except i

Validation:

Validation must be created ONLY from the training subjects.

Do not use the test subject for:

- model selection
- hyperparameter tuning
- early stopping
- threshold selection
- feature selection

---

# 8. IMPORTANT — WINDOWING

Split subject FIRST.

Then generate windows.

Correct:

SUBJECT SPLIT
↓
VIDEO
↓
WINDOW

Incorrect:

VIDEO
↓
WINDOW
↓
RANDOM SPLIT

Ensure no windows from the same source video appear in different folds.

---

# 9. PREPROCESSING

All learned preprocessing statistics must be fitted only on training subjects.

Examples:

- mean
- std
- scaler
- PCA
- feature normalization

Validation/test only use the transformation fitted on TRAIN.

---

# 10. AUGMENTATION

Augmentation only on TRAIN.

Never augment validation/test.

Never place an augmented copy of a test sample into training.

---

# 11. BASELINE

Before modifying RehabMotionNet, run at least:

### Baseline 1
Majority Class

### Baseline 2
Simple classical ML model

Use:

Random Forest or SVM depending on feature format.

### Baseline 3
Simple LSTM

Keep it intentionally simple.

Purpose:

determine whether the task itself is easy.

---

# 12. REHABMOTIONNET

Run the CURRENT RehabMotionNet architecture.

Do not add:

- ST-GCN
- new attention
- larger model
- new features

yet.

The first objective is to establish a clean baseline.

---

# 13. TRAINING

For every LOSO fold save:

fold_id
test_subject
train_subjects
validation_subjects
seed
epochs
best_epoch
train_loss
train_accuracy
val_loss
val_accuracy
test_accuracy
test_precision
test_recall
test_macro_f1

---

# 14. METRICS

Calculate:

Accuracy
Macro Precision
Macro Recall
Macro F1
Weighted F1

If applicable:

MAE
RMSE
R²

Do NOT select the best result based on TEST.

---

# 15. MULTIPLE SEEDS

If GPU/time allows:

3 seeds per fold.

Otherwise:

1 seed initially.

If only 1 seed:

clearly state this as a limitation.

---

# 16. FINAL LOSO SUMMARY

Calculate:

Mean
Std
Min
Max

Example:

Accuracy:
mean ± std

Macro-F1:
mean ± std

Do NOT report only the best fold.

---

# 17. PER-SUBJECT PERFORMANCE

Create:

`reports/evaluation/loso_per_subject.csv`

Columns:

subject
accuracy
precision
recall
macro_f1
sample_count

This is essential.

A model that performs:

Subject 1 = 95%
Subject 2 = 92%
Subject 3 = 40%

is not equivalent to a model consistently achieving 75%.

---

# 18. GENERALIZATION GAP

Calculate:

Train Accuracy
Validation Accuracy
Test Accuracy

and:

Train − Test

for each fold.

---

# 19. CONFUSION MATRIX

Create:

- aggregated LOSO confusion matrix
- per-fold confusion matrix if practical

Do not hide difficult classes.

---

# 20. DO NOT ASSUME 70–85%

The previous report mentioned that real data "will usually" achieve 70–85%.

This is NOT an experimental result.

Delete this assumption from scientific conclusions.

Only report actual measured performance.

Possible result:

20%

40%

60%

80%

95%

100%

All are acceptable if measured correctly.

---

# 21. DO NOT CLAIM MEDICAL-GRADE

Do NOT describe this pipeline as:

"medical-grade validation"

unless there is actual clinical validation supporting that statement.

Use:

"research evaluation"

or:

"subject-independent evaluation"

instead.

---

# 22. FINAL REPORT

Create:

`reports/evaluation/PHASE_4_7_FINAL_REPORT.md`

Sections:

# Phase 4.7 Final Report

## 1. Data Provenance

## 2. Real vs Synthetic Data Verification

## 3. Feature Verification

## 4. Label Verification

## 5. Subject Verification

## 6. Current Split Audit

## 7. True LOSO Protocol

## 8. Baseline Results

## 9. RehabMotionNet Results

## 10. Per-Fold Results

## 11. Mean ± Std

## 12. Per-Subject Results

## 13. Confusion Matrix

## 14. Generalization Gap

## 15. Overfitting Analysis

## 16. Failure Cases

## 17. Limitations

## 18. Recommended Next Step

---

# 23. FINAL DECISION

At the end, classify the current system into ONE of:

A. DATA PIPELINE NOT VALID

B. DATA VALID BUT MODEL UNDERFITTING

C. DATA VALID + MODEL OVERFITTING

D. DATA VALID + GOOD GENERALIZATION

E. DATASET TOO SMALL / INSUFFICIENT FOR STRONG CONCLUSION

If evidence is insufficient:

choose E.

Do NOT force a conclusion.

---

# 24. ACCEPTANCE CRITERIA

Phase 4.7 = PASS only when:

[ ] All 491 source videos verified

[ ] All feature files traced to source videos

[ ] Synthetic/mock data ruled out

[ ] Label provenance verified

[ ] Subject provenance verified

[ ] Current split correctly classified

[ ] True LOSO 10-fold implemented

[ ] Split before windowing

[ ] Preprocessing train-only

[ ] Augmentation train-only

[ ] Baselines completed

[ ] RehabMotionNet completed

[ ] Per-fold metrics saved

[ ] Mean ± Std calculated

[ ] Per-subject metrics calculated

[ ] Generalization gap calculated

[ ] Confusion matrix generated

[ ] No test-set tuning

[ ] No metric manipulation

[ ] Final report generated

---

# MOST IMPORTANT RULE

Do not improve the model yet.

First establish a TRUSTWORTHY experimental baseline.

Only after Phase 4.7 PASS may we decide whether to:

- add ST-GCN
- add temporal attention
- modify CNN/Transformer
- reduce parameters
- add augmentation
- add more subjects
- add another dataset

The objective is not 100% accuracy.

The objective is a reproducible model that genuinely generalizes to unseen subjects.