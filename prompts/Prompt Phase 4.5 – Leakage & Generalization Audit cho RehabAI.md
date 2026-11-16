# REHABAI — PHASE 4.5
# LEAKAGE & GENERALIZATION AUDIT
## Mục tiêu: xác minh nghiêm túc nguyên nhân Accuracy = 100%

Bạn đang tiếp tục dự án RehabAI/RehabLSTM.

Đây là một nghiên cứu AI về phân tích động tác phục hồi chức năng chi trên bằng video/skeleton.

## 1. BỐI CẢNH HIỆN TẠI

Mô hình hiện tại cho kết quả rất cao:

- Accuracy = 1.00
- Macro-F1 = 1.00
- Một số thí nghiệm có Completion Score RMSE ≈ 0.81
- RehabMotionNet có khoảng 452K parameters
- Dataset Upper Limb Stroke Rehabilitation Exercise Video Dataset có khoảng 491 video
- Dataset này có 10 volunteers/subjects
- Có 4 bài tập:
  - E1 — Lifting an Object
  - E2 — Extending the Elbow
  - E3 — Lifting the Wrist
  - E4 — Opening the Hand
- Label của dataset này là Complete / Incomplete.

Kết quả Accuracy = 100% hiện tại KHÔNG được mặc định coi là overfitting.

Agent phải xác minh xem nguyên nhân là:

1. Data leakage
2. Subject leakage
3. Sequence/window leakage
4. Duplicate hoặc near-duplicate data
5. Preprocessing leakage
6. Task quá dễ
7. Dataset có sự khác biệt quá rõ giữa các exercise
8. Model thực sự generalize tốt
9. Hoặc kết hợp nhiều nguyên nhân.

KHÔNG được cố tình làm Accuracy giảm.

KHÔNG được sửa label.

KHÔNG được xóa dữ liệu chỉ vì dữ liệu làm Accuracy cao.

KHÔNG được thay đổi kết quả experiment để phù hợp với giả thuyết overfitting.

Mọi kết luận phải dựa trên evidence.

---

# 2. QUY TẮC QUAN TRỌNG

## RULE 1 — KHÔNG TRAIN LẠI NGAY

Trước tiên phải audit pipeline hiện tại.

Không được bắt đầu retrain model ngay khi chưa hoàn thành leakage audit.

---

## RULE 2 — KHÔNG ĐƯỢC SPLIT SAU KHI TẠO WINDOW

Kiểm tra pipeline hiện tại.

Thứ tự ĐÚNG phải là:

RAW VIDEOS
    ↓
DATASET AUDIT
    ↓
SUBJECT IDENTIFICATION
    ↓
TRAIN / VALIDATION / TEST SPLIT
    ↓
WINDOW / SEQUENCE GENERATION
    ↓
AUGMENTATION
    ↓
TRAINING

Không được:

RAW VIDEO
    ↓
WINDOWING
    ↓
RANDOM SPLIT

Nếu pipeline hiện tại đang window trước rồi random split, phải đánh dấu:

CRITICAL DATA LEAKAGE RISK

---

# 3. AUDIT #1 — SUBJECT OVERLAP

Đây là bước bắt buộc.

Đọc metadata/index của dataset.

Xác định:

- subject_id
- video_id
- exercise_id
- split
- label

Tạo bảng:

subject_id | train | validation | test

Ví dụ:

subject_01 | YES | NO | NO
subject_02 | YES | NO | YES

Nếu cùng một subject xuất hiện ở train và test:

→ SUBJECT LEAKAGE RISK

Tính:

- số subject train
- số subject validation
- số subject test
- số subject overlap train/test
- số subject overlap train/validation
- số subject overlap validation/test

Output bắt buộc:

reports/leakage/subject_overlap_report.csv

và:

reports/leakage/subject_overlap_report.md

---

# 4. AUDIT #2 — VIDEO OVERLAP

Kiểm tra xem cùng một video có xuất hiện ở nhiều split hay không.

Kiểm tra:

- filename
- filepath
- video_id
- source_id
- hash

Tạo SHA256 hoặc MD5 cho mỗi video nếu cần.

Tạo:

reports/leakage/video_overlap_report.csv

Nếu phát hiện cùng video ở train và test:

→ CRITICAL LEAKAGE

---

# 5. AUDIT #3 — DUPLICATE / NEAR-DUPLICATE

Không chỉ kiểm tra filename.

Phải kiểm tra duplicate bằng:

- file hash
- video metadata
- duration
- frame count
- resolution
- FPS

Nếu khả thi, kiểm tra perceptual similarity bằng sampling frame.

Mục tiêu:

phát hiện trường hợp:

video_A ≠ video_B

nhưng:

video_A và video_B gần như cùng nội dung.

Nếu phát hiện:

- exact duplicate
- near duplicate
- same recording với tên khác
- same sequence được cắt thành nhiều file

phải ghi rõ.

Output:

reports/leakage/duplicate_report.csv

---

# 6. AUDIT #4 — WINDOW / SEQUENCE LEAKAGE

Đây là bước cực kỳ quan trọng.

Kiểm tra code tạo sequence/window.

Ví dụ:

Một video có:

1000 frames

window_size = 30
stride = 5

Nếu tạo:

window 1 = frames 1–30
window 2 = frames 6–35
window 3 = frames 11–40

rồi random split:

window 1 → train
window 2 → test

thì đây là leakage.

Hai sample gần như chứa cùng thông tin.

Agent phải xác định:

- window được tạo ở phase nào
- split được thực hiện ở phase nào
- split dựa trên video hay sequence
- sequence_id có giữ source_video_id không
- cùng video có thể xuất hiện nhiều split hay không

Output:

reports/leakage/sequence_leakage_report.md

---

# 7. AUDIT #5 — PREPROCESSING LEAKAGE

Kiểm tra toàn bộ preprocessing.

Đặc biệt:

- normalization
- scaler
- mean/std
- PCA
- feature selection
- dimensionality reduction
- coordinate normalization
- angle normalization
- velocity normalization

Kiểm tra xem preprocessing có được fit trên toàn bộ dataset trước khi split không.

SAI:

ALL DATA
    ↓
FIT SCALER
    ↓
SPLIT

ĐÚNG:

TRAIN
    ↓
FIT SCALER

VALIDATION / TEST
    ↓
TRANSFORM USING TRAIN SCALER

Nếu phát hiện leakage:

→ ghi rõ file/code gây ra leakage.

---

# 8. AUDIT #6 — AUGMENTATION LEAKAGE

Kiểm tra augmentation.

Augmentation phải được áp dụng SAU split.

Đúng:

RAW
 ↓
SPLIT
 ↓
TRAIN AUGMENTATION

Sai:

RAW
 ↓
AUGMENT
 ↓
SPLIT

Đặc biệt kiểm tra:

- rotation
- scaling
- jitter
- temporal augmentation
- mirroring
- noise
- random crop

Không được để augmented version của cùng sample xuất hiện trong test.

---

# 9. AUDIT #7 — LABEL / EXERCISE LEAKAGE

Kiểm tra xem model có đang học một "shortcut" quá dễ hay không.

Đặc biệt với 4 exercise:

E1 — Lifting an Object
E2 — Extending the Elbow
E3 — Lifting the Wrist
E4 — Opening the Hand

Phân tích:

- joint usage
- sequence length
- motion amplitude
- camera/background
- body position
- subject
- recording environment

Kiểm tra xem model có thể phân biệt exercise chỉ bằng:

- static pose
- background
- camera angle
- recording setup
- subject identity

thay vì học rehabilitation movement.

Nếu có dấu hiệu shortcut learning:

phải ghi rõ.

---

# 10. BASELINE EXPERIMENT

Không được chỉ đánh giá RehabMotionNet.

Tạo ít nhất các baseline đơn giản nếu pipeline hiện tại cho phép:

1. Majority Class
2. Random Forest / XGBoost nếu feature phù hợp
3. MLP
4. LSTM đơn giản

Mục tiêu:

Nếu baseline đơn giản cũng đạt gần 100%:

→ task/dataset có thể quá dễ.

Nếu chỉ RehabMotionNet đạt 100%:

→ cần kiểm tra model capacity/generalization kỹ hơn.

Không được dùng baseline để "làm xấu" kết quả.

---

# 11. BẮT BUỘC CHẠY SUBJECT-WISE EVALUATION

Sau leakage audit, tạo evaluation protocol mới.

## Ưu tiên:

LEAVE-ONE-SUBJECT-OUT (LOSO)

Dataset có khoảng 10 subjects.

Do đó:

Fold 1:
Test = Subject 1
Train = Subjects 2–10

Fold 2:
Test = Subject 2
Train = Subjects 1,3–10

...

Fold 10:
Test = Subject 10
Train = Subjects 1–9

Validation phải được tạo bên trong training subjects.

KHÔNG được sử dụng test subject để tune hyperparameters.

---

# 12. QUAN TRỌNG — SPLIT Ở CẤP SUBJECT

Không được:

video → random split

Phải:

subject → split

Sau đó mới:

video → sequence/window

Ví dụ:

SUBJECTS
 ↓
LOSO SPLIT
 ↓
TRAIN SUBJECTS / TEST SUBJECT
 ↓
VIDEO
 ↓
SEQUENCE
 ↓
MODEL

---

# 13. CHẠY LẠI REHABMOTIONNET

Sau khi pipeline LOSO được xác nhận đúng:

train lại RehabMotionNet.

Giữ nguyên:

- architecture
- labels
- preprocessing
- optimizer
- loss
- hyperparameters

trong experiment đầu tiên.

Mục tiêu là tạo comparison công bằng giữa:

CURRENT RANDOM/SOURCE SPLIT
vs
SUBJECT-WISE LOSO

---

# 14. KHÔNG ĐƯỢC CHỈ REPORT ACCURACY

Report:

- Accuracy
- Macro Precision
- Macro Recall
- Macro F1
- Weighted F1
- Confusion Matrix
- Per-class Precision
- Per-class Recall
- Per-class F1

Nếu có regression:

- MAE
- RMSE
- R² nếu phù hợp

Với LOSO:

report:

Mean ± Standard Deviation

Ví dụ:

Accuracy:
mean ± std

Macro-F1:
mean ± std

Không được chỉ report fold tốt nhất.

---

# 15. CONFUSION MATRIX

Tạo confusion matrix cho:

- current split
- LOSO

Lưu:

reports/evaluation/confusion_matrix_current.png
reports/evaluation/confusion_matrix_loso.png

Nếu có thể, tạo normalized confusion matrix.

---

# 16. ABLATION STUDY

Sau LOSO, chạy ablation.

Không cần chạy quá nhiều.

Ưu tiên:

A. Position only

B. Position + velocity

C. Position + velocity + angle

D. Full model

Mục tiêu:

xác định model thực sự cần feature nào.

Không được thêm feature chỉ để tăng accuracy.

---

# 17. MODEL CAPACITY ANALYSIS

RehabMotionNet hiện khoảng:

452K parameters

Không được kết luận:

"452K > 491 videos = overfitting"

vì parameter count không đủ để chứng minh overfitting.

Thay vào đó chạy:

Model A — reduced capacity
Model B — current model
Model C — larger capacity nếu cần

Ví dụ:

A = ~100K parameters
B = ~452K parameters

So sánh:

- train accuracy
- validation accuracy
- LOSO accuracy
- Macro-F1
- generalization gap

Nếu model nhỏ có kết quả tương đương model lớn:

→ ưu tiên model nhỏ hơn.

---

# 18. GENERALIZATION GAP

Tính:

Generalization Gap = Train Score − Test Score

Report:

- Train Accuracy
- Validation Accuracy
- LOSO Test Accuracy

Ví dụ:

Train = 100%
LOSO = 78%

→ strong generalization gap

Nhưng:

Train = 98%
LOSO = 96%

→ much better generalization

Không được gọi overfitting chỉ dựa vào train accuracy.

---

# 19. CROSS-DATASET EVALUATION

Nếu ontology/label semantics thực sự tương thích, đánh giá khả năng generalization cross-dataset.

Không được ép các dataset khác ontology thành cùng label nếu không có cơ sở.

Đặc biệt:

Upper Limb Stroke dataset:

Complete / Incomplete

REHAB24-6:

Correctness / Incorrectness

MobiPhysio:

expert score / exercise-specific labels

Phải giữ raw label và canonical label riêng.

Không được tự ý giả định:

Complete = Correct

nếu metadata/paper không hỗ trợ.

Nếu không tương thích:

→ chỉ sử dụng dataset đó cho pretraining hoặc auxiliary experiment phù hợp.

---

# 20. DATASET STATISTICS

Tạo bảng:

Dataset
Subjects
Videos
Exercises
Labels
Camera views
FPS
Resolution
Duration
Train/Test protocol

Output:

reports/dataset_statistics_final.csv

Không được bịa số.

Nếu không biết:

ghi:

UNKNOWN

hoặc:

NOT AVAILABLE

---

# 21. EXPERIMENT TRACKING

Mỗi experiment phải có:

experiment_id
dataset
split_method
subjects_train
subjects_val
subjects_test
model
parameters
features
augmentation
seed
epochs
learning_rate
batch_size
train_metrics
validation_metrics
test_metrics

Lưu:

experiments/experiment_registry.csv

---

# 22. REPRODUCIBILITY

Mỗi experiment phải có:

- random seed
- git commit/hash nếu có
- requirements version
- CUDA version
- PyTorch version
- GPU
- model config
- dataset version
- preprocessing config

Không được để experiment không thể tái lập.

---

# 23. KHÔNG XÓA DATA

Tuyệt đối không xóa raw dataset.

Không overwrite raw dataset.

Nếu phát hiện dữ liệu lỗi:

đánh dấu:

status = corrupted

hoặc:

status = duplicate

hoặc:

status = excluded_with_reason

Raw data phải được giữ nguyên.

---

# 24. OUTPUT CUỐI CÙNG

Sau khi hoàn thành Phase 4.5 phải tạo:

reports/leakage/
├── subject_overlap_report.csv
├── subject_overlap_report.md
├── video_overlap_report.csv
├── duplicate_report.csv
├── sequence_leakage_report.md
├── preprocessing_leakage_report.md
├── augmentation_leakage_report.md
└── leakage_summary.md

reports/evaluation/
├── current_split_metrics.csv
├── loso_metrics.csv
├── loso_summary.csv
├── confusion_matrix_current.png
├── confusion_matrix_loso.png
└── generalization_gap.csv

reports/ablation/
└── ablation_results.csv

experiments/
└── experiment_registry.csv

---

# 25. TẠO FILE KẾT LUẬN

Tạo:

reports/PHASE_4_5_FINAL_REPORT.md

Report phải có cấu trúc:

# Phase 4.5 Final Report

## 1. Executive Summary

## 2. Current 100% Accuracy Result

## 3. Subject Leakage

## 4. Video Leakage

## 5. Duplicate / Near Duplicate

## 6. Sequence Leakage

## 7. Preprocessing Leakage

## 8. Augmentation Leakage

## 9. Shortcut Learning Analysis

## 10. Baseline Results

## 11. LOSO Results

## 12. Generalization Gap

## 13. Ablation Results

## 14. Model Capacity Analysis

## 15. Final Interpretation

## 16. Recommended Model

## 17. Limitations

## 18. Reproducibility Information

---

# 26. FINAL DECISION LOGIC

Sau khi hoàn thành toàn bộ audit:

### CASE A

Nếu phát hiện data leakage:

Kết luận:

"Current 100% accuracy is not considered reliable because leakage was identified."

Sau đó sửa pipeline và retrain.

---

### CASE B

Nếu không có leakage nhưng random split = 100%, LOSO thấp:

Ví dụ:

Random split = 100%
LOSO = 80%

Kết luận:

"Performance is highly dependent on subject identity / subject distribution."

Không được report 100% là main result.

LOSO trở thành primary result.

---

### CASE C

Nếu không có leakage và LOSO vẫn gần 100%:

Kiểm tra dataset difficulty.

Chạy baseline.

Nếu baseline cũng gần 100%:

Kết luận:

"The task may be intrinsically easy under the current dataset."

Không được giả tạo giảm accuracy.

---

### CASE D

Nếu không có leakage, baseline thấp, RehabMotionNet cao, LOSO cao:

Đây có thể là evidence rằng model thực sự học được movement representation tốt.

Tuy nhiên vẫn phải report:

- sample size
- subject count
- confidence/variation
- limitations
- external validation nếu có.

---

# 27. QUY TẮC KẾT LUẬN KHOA HỌC

KHÔNG viết:

"Accuracy 100% proves the model is excellent."

KHÔNG viết:

"Accuracy 100% definitely means overfitting."

Phải viết theo evidence.

Ví dụ:

"Although the initial evaluation achieved 100% accuracy, subject-independent evaluation was conducted to assess whether this performance generalizes to unseen participants."

Nếu LOSO thấp:

"The substantial performance reduction under subject-independent evaluation indicates limited subject-independent generalization."

Nếu LOSO vẫn cao:

"Performance remained high under subject-independent evaluation, reducing the likelihood that the initial result was solely caused by subject leakage."

---

# 28. ACCEPTANCE CRITERIA

Phase 4.5 chỉ được đánh dấu PASS khi:

[ ] Subject overlap audited

[ ] Video overlap audited

[ ] Duplicate audited

[ ] Sequence/window leakage audited

[ ] Preprocessing leakage audited

[ ] Augmentation leakage audited

[ ] Label semantics verified

[ ] Baselines evaluated

[ ] LOSO evaluated

[ ] Confusion matrix generated

[ ] Generalization gap calculated

[ ] Ablation completed

[ ] Model capacity comparison completed

[ ] Experiment registry updated

[ ] Final report generated

[ ] No raw data deleted

[ ] No metrics artificially modified

---

# 29. AGENT EXECUTION RULE

Thực hiện tuần tự.

Không được bỏ qua bước.

Không được nhảy sang Phase 5/6/7/8 nếu Phase 4.5 chưa PASS.

Sau mỗi nhóm audit:

1. Cho biết file/code nào đã kiểm tra.
2. Cho biết kết quả.
3. Cho biết có leakage hay không.
4. Cho biết evidence.
5. Tạo artifact tương ứng.
6. Chỉ tiếp tục khi bước trước đã hoàn thành.

Nếu gặp lỗi:

KHÔNG tự ý bỏ qua.

Ghi:

ERROR
ROOT CAUSE
FILE
LINE
PROPOSED FIX
STATUS

Nếu cần sửa code:

- backup/version trước khi sửa
- chỉ sửa phần cần thiết
- không thay đổi ontology/label
- không thay đổi raw data
- không thay đổi metric definition

---

# 30. ĐIỂM QUAN TRỌNG NHẤT

Mục tiêu của Phase 4.5 KHÔNG phải làm Accuracy từ 100% xuống thấp hơn.

Mục tiêu là trả lời chính xác câu hỏi:

"100% accuracy hiện tại có đáng tin cậy và có khả năng generalize sang người dùng mới hay không?"

Ưu tiên:

SCIENTIFIC VALIDITY
>
DATA LEAKAGE PREVENTION
>
SUBJECT-INDEPENDENT GENERALIZATION
>
REPRODUCIBILITY
>
MODEL COMPLEXITY
>
RAW ACCURACY

Chỉ sau khi Phase 4.5 hoàn thành mới quyết định:

- giữ nguyên RehabMotionNet
- giảm model
- thay feature
- thay split
- thay training strategy
- hoặc tiếp tục dataset expansion.

KHÔNG đưa ra quyết định trước khi có evidence.