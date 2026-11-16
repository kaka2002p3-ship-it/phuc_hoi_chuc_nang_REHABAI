# REHABAI — PHASE 4.6
# FULL DATA EXTRACTION + SUBJECT-INDEPENDENT TRAINING

## MỤC TIÊU

Phase 4.5 đã phát hiện rằng:

- `upper_limb_master.csv` có 491 videos
- Có 10 subjects
- Nhưng Phase 2 hiện mới tạo được 14 `.npz`
- `split_manifest.csv` hiện chỉ có:
  - Train: 2 videos — Subject 1
  - Validation: 9 videos — Subject 7
  - Test: 0 videos

Do đó Accuracy = 100% hiện tại KHÔNG được sử dụng làm kết quả cuối cùng.

Mục tiêu Phase 4.6:

1. Trích xuất landmark cho toàn bộ 491 videos.
2. Kiểm tra chất lượng toàn bộ `.npz`.
3. Xác nhận đủ dữ liệu trước khi training.
4. Xây dựng LOSO 10-fold đúng cấp subject.
5. Train/evaluate RehabMotionNet trên từng fold.
6. So sánh với baseline.
7. Báo cáo Mean ± Std.
8. Không được làm giả hoặc điều chỉnh metric.

---

# RULE 1 — KHÔNG ĐƯỢC TRAIN KHI CHƯA ĐỦ DATA

Trước tiên đọc:

- `upper_limb_master.csv`
- `split_manifest.csv`
- extraction code hiện tại
- `exercise_registry.json`
- config/model hiện tại

Xác định chính xác:

- 491 videos có tồn tại trên disk không
- filepath
- subject_id
- exercise_id
- label
- source metadata

KHÔNG được bắt đầu training nếu extraction chưa hoàn thành.

---

# RULE 2 — FULL EXTRACTION

Viết hoặc sửa extraction script để xử lý TOÀN BỘ 491 videos.

Ưu tiên:

Python + MediaPipe

Nếu project hiện tại đã có extraction pipeline thì tái sử dụng thay vì viết lại toàn bộ.

Output mỗi video:

`.npz`

Mỗi `.npz` phải giữ metadata tối thiểu:

- video_id
- subject_id
- exercise_id
- label
- frame_count
- fps
- landmark shape
- extraction status

Không được đưa label vào feature tensor theo cách khiến model có thể học trực tiếp label.

---

# RULE 3 — RESUME

Extraction phải hỗ trợ resume.

Nếu:

video_001.mp4
→ video_001.npz

đã tồn tại và hợp lệ:

SKIP

Không extract lại.

Nếu `.npz` tồn tại nhưng corrupt/incomplete:

REPROCESS

Nếu máy bị:

- mất điện
- crash
- đóng terminal
- restart

thì lần chạy sau phải tiếp tục từ file chưa hoàn thành.

---

# RULE 4 — KHÔNG XÓA RAW DATA

Tuyệt đối không:

- delete raw videos
- rename raw videos
- modify raw videos

Raw dataset phải được giữ nguyên.

Nếu video lỗi:

status = corrupted

Nếu MediaPipe không detect được đủ landmark:

status = insufficient_landmarks

Không được âm thầm bỏ file.

---

# RULE 5 — EXTRACTION LOG

Tạo:

`reports/extraction/extraction_manifest.csv`

Các cột:

video_id
subject_id
exercise_id
label
source_path
output_path
status
frame_count
fps
resolution
valid_frames
invalid_frames
landmark_detection_rate
error_message

Status có thể:

SUCCESS
SKIPPED
REPROCESSED
CORRUPTED
INSUFFICIENT_LANDMARKS
FAILED

---

# RULE 6 — QUALITY CONTROL

Sau extraction, tính:

Total videos = 491

Expected NPZ = 491

Successful NPZ = ?

Failed = ?

Corrupted = ?

Insufficient landmarks = ?

Missing = ?

Detection rate mean/std/min/max

Phải tạo:

`reports/extraction/extraction_summary.md`

và:

`reports/extraction/extraction_summary.csv`

---

# RULE 7 — KHÔNG ĐƯỢC TỰ Ý DROP DATA

Nếu một video landmark detection thấp:

KHÔNG tự ý xóa.

Đánh dấu và báo cáo.

Chỉ exclude khỏi training nếu có một criterion rõ ràng được định nghĩa trước.

Ví dụ:

landmark_detection_rate < predefined_threshold

Nếu threshold chưa tồn tại:

KHÔNG tự ý đặt threshold chỉ để cải thiện model.

Đề xuất threshold và chờ approval logic trong config.

---

# RULE 8 — SUBJECT-WISE DATA INDEX

Sau extraction tạo:

`data/indexes/upper_limb_npz_master.csv`

Mỗi dòng = một video/sample source.

Cột tối thiểu:

video_id
subject_id
exercise_id
label
npz_path
quality_status
detection_rate

Kiểm tra:

10 subjects

và thống kê số video mỗi subject.

---

# RULE 9 — LOADING DATA

Dataset loader phải sử dụng:

`upper_limb_npz_master.csv`

Không được hard-code:

Subject 1
Subject 7

Không được hard-code:

2 train
9 validation

---

# RULE 10 — LOSO

Implement:

Leave-One-Subject-Out Cross Validation.

Có 10 subjects → 10 folds.

Fold i:

TEST = Subject i

TRAIN = all other subjects

Validation:

Validation phải được tạo từ TRAIN SUBJECTS.

TUYỆT ĐỐI KHÔNG sử dụng test subject để tune model.

Ví dụ:

Fold 1:

TEST:
Subject 1

TRAIN:
Subject 2–10

VALIDATION:
subset từ Subject 2–10

Sau đó:

Fold 2:

TEST:
Subject 2

TRAIN:
Subject 1,3–10

...

Fold 10:

TEST:
Subject 10

TRAIN:
Subject 1–9

---

# RULE 11 — SPLIT TRƯỚC WINDOWING

Nếu model sử dụng temporal windows:

ĐÚNG:

SUBJECT SPLIT
↓
VIDEO SPLIT
↓
WINDOW GENERATION

SAI:

VIDEO
↓
WINDOW
↓
RANDOM SPLIT

Một video không được tạo window rồi phân tán sang nhiều folds.

---

# RULE 12 — AUGMENTATION

Augmentation chỉ được áp dụng cho TRAIN.

Không augmentation:

Validation

Test

Nếu video Test có augmented copy trong Train:

→ DATA LEAKAGE

---

# RULE 13 — PREPROCESSING

Scaler/statistics/normalization phải được fit từ TRAIN.

Không được fit trên:

TRAIN + VAL + TEST

Đặc biệt kiểm tra:

- mean/std
- coordinate normalization
- PCA
- feature normalization
- temporal normalization

---

# RULE 14 — FIRST EXPERIMENT: CURRENT MODEL

Sau khi pipeline được xác nhận:

Train RehabMotionNet.

Giữ nguyên architecture/config hiện tại.

Không giảm model trước.

Mục tiêu:

đo khả năng generalization của architecture hiện tại.

---

# RULE 15 — BASELINE

Chạy baseline đơn giản trước hoặc song song:

- Majority Class
- Logistic Regression / SVM nếu phù hợp
- Random Forest
- Simple MLP
- Simple LSTM

Không cần chạy tất cả nếu feature representation không phù hợp.

Ít nhất phải có:

1 simple non-deep-learning baseline

và:

1 simple neural baseline.

---

# RULE 16 — METRICS

Mỗi fold report:

Accuracy
Precision
Recall
Macro-F1
Weighted-F1

Nếu classification:

Confusion Matrix

Nếu completion score regression:

MAE
RMSE
R² nếu phù hợp.

---

# RULE 17 — FINAL LOSO METRICS

Không được chỉ lấy fold tốt nhất.

Tính:

Mean
Standard Deviation
Minimum
Maximum

Ví dụ:

Accuracy = mean ± std

Macro-F1 = mean ± std

Report cả 10 folds.

---

# RULE 18 — GENERALIZATION GAP

Mỗi fold lưu:

Train Accuracy
Validation Accuracy
Test Accuracy

Tính:

Train − Test

Không được chỉ báo cáo test accuracy.

---

# RULE 19 — PER-SUBJECT RESULT

Tạo:

`reports/evaluation/loso_subject_results.csv`

Ví dụ:

subject_01 | accuracy | f1 | ...
subject_02 | accuracy | f1 | ...
...
subject_10 | accuracy | f1 | ...

Mục tiêu:

xác định subject nào khó.

Không được bỏ subject có kết quả thấp.

---

# RULE 20 — CONFUSION MATRIX

Tạo:

`reports/evaluation/loso_confusion_matrix.csv`

và hình ảnh:

`reports/evaluation/loso_confusion_matrix.png`

Có thể tạo:

- aggregated confusion matrix
- per-fold confusion matrix

---

# RULE 21 — EXPERIMENT REGISTRY

Mỗi fold phải được ghi vào:

`experiments/experiment_registry.csv`

Các field:

experiment_id
fold
test_subject
train_subjects
validation_subjects
model
parameters
features
augmentation
seed
epochs
learning_rate
batch_size
accuracy
macro_f1
precision
recall
rmse
mae

---

# RULE 22 — RANDOM SEED

LOSO không nên chỉ chạy một seed nếu tài nguyên cho phép.

Ưu tiên:

3 seeds / fold

Nếu quá tốn thời gian:

ít nhất 1 seed/fold trước.

Không được giả vờ statistical robustness nếu chỉ chạy một seed.

Nếu chỉ chạy 1 seed:

ghi rõ limitation.

---

# RULE 23 — GPU

Trước training:

verify CUDA.

Nếu GPU available:

use GPU.

Không được silently fallback CPU.

Log:

GPU
CUDA
PyTorch
VRAM

---

# RULE 24 — CHECKPOINT

Mỗi fold phải có checkpoint:

`checkpoints/loso/fold_XX/`

Có:

best model
training config
metrics
seed

Nếu training crash:

có thể resume.

---

# RULE 25 — EARLY STOPPING

Không được tune trên test subject.

Early stopping chỉ dùng:

TRAIN / VALIDATION.

TEST chỉ được dùng cuối fold.

---

# RULE 26 — KHÔNG TỐI ƯU ĐỂ ĐẠT 100%

Đây là quy tắc quan trọng nhất.

KHÔNG được:

- thay đổi threshold để tăng accuracy
- xóa hard samples
- xóa subject khó
- bỏ class khó
- chọn checkpoint tốt nhất dựa trên TEST
- chạy nhiều model rồi chỉ báo cáo model tốt nhất
- thay đổi split sau khi xem test result

Mục tiêu:

GENERALIZATION

không phải:

100% ACCURACY.

---

# RULE 27 — AFTER FIRST FULL LOSO

Sau khi chạy xong baseline + RehabMotionNet:

KHÔNG tự động thay model.

Dừng lại và tạo:

`reports/evaluation/PHASE_4_6_DECISION.md`

Trong đó trả lời:

1. Có leakage không?
2. Full 491 extraction thành công bao nhiêu?
3. LOSO Accuracy?
4. LOSO Macro-F1?
5. Standard deviation?
6. Subject nào khó nhất?
7. Baseline đạt bao nhiêu?
8. RehabMotionNet tốt hơn baseline bao nhiêu?
9. Có generalization gap lớn không?
10. Có evidence overfitting không?
11. Có cần giảm model không?
12. Có cần thêm data không?

---

# DECISION LOGIC

## Nếu:

LOSO thấp hơn rất nhiều random split

→ investigate generalization / subject variability.

## Nếu:

baseline gần bằng RehabMotionNet

→ dataset/task có thể đơn giản.

## Nếu:

RehabMotionNet > baseline rõ rệt

→ architecture có evidence of useful representation.

## Nếu:

train ≫ test

→ investigate overfitting.

## Nếu:

LOSO vẫn ~98–100%

→ không được tự động nói model overfit.

Kiểm tra:

- dataset difficulty
- exercise separability
- shortcut learning
- camera/background
- subject independence
- baseline performance

---

# FINAL DELIVERABLE

Tạo:

reports/evaluation/PHASE_4_6_FINAL_REPORT.md

Cấu trúc:

# Phase 4.6 Final Report

## 1. Dataset
## 2. Extraction
## 3. Quality Control
## 4. Subject Distribution
## 5. LOSO Protocol
## 6. Baseline
## 7. RehabMotionNet
## 8. Per-Fold Results
## 9. Mean ± Std
## 10. Confusion Matrix
## 11. Generalization Gap
## 12. Overfitting Analysis
## 13. Failure Cases
## 14. Final Interpretation
## 15. Limitations
## 16. Recommended Next Phase

---

# ACCEPTANCE CRITERIA

Phase 4.6 = PASS khi:

[ ] 491 videos audited

[ ] Extraction attempted on all 491

[ ] Extraction manifest created

[ ] Missing/corrupt files identified

[ ] Landmark quality reported

[ ] NPZ master index created

[ ] 10 subjects verified

[ ] LOSO 10-fold implemented

[ ] Split happens before windowing

[ ] Augmentation only on train

[ ] Preprocessing fitted only on train

[ ] Test subjects never used for tuning

[ ] Baseline evaluated

[ ] RehabMotionNet evaluated

[ ] Per-fold metrics saved

[ ] Mean ± Std calculated

[ ] Confusion matrix generated

[ ] Generalization gap calculated

[ ] Experiment registry updated

[ ] Final report generated

[ ] No raw data deleted

[ ] No metric modified artificially

---

# IMPORTANT

Do not proceed to model architecture modification until this phase is completed.

The purpose of this phase is NOT to make the accuracy lower.

The purpose is to determine whether the model genuinely generalizes to unseen subjects.

Execute carefully and report actual measurements.