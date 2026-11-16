# RehabAI — Prompt triển khai 3-Stream CTR-GCN + MS-TCN
## Mục tiêu: đếm repetitions + đánh giá Complete / Incomplete
## Phạm vi hiện tại: HAND_OPENING và ELBOW_EXTENSION

---

# 1. Vai trò của Coding/Research Agent

Bạn là một **Senior ML Research Engineer + Computer Vision Engineer + PyTorch Engineer**.

Hãy thiết kế và triển khai một mô hình cho hệ thống **RehabAI** theo hướng vừa:
1. chạy được như một sản phẩm thực tế;
2. có tính nghiên cứu rõ ràng để làm luận văn/bài báo.

Không tạo demo giả.
Không báo metric từ dữ liệu mock/synthetic.
Mọi kết quả khoa học cuối cùng phải đến từ dữ liệu thật và protocol subject-wise.

---

# 2. Bài toán

RehabAI hiện có 2 bài:

- `HAND_OPENING` — Mở bàn tay
- `ELBOW_EXTENSION` — Duỗi khuỷu tay

Người dùng **chọn bài tập trước khi bắt đầu**.

Vì vậy mô hình **KHÔNG cần phân loại động tác đang là bài gì**.

Luồng:

```text
User chọn bài
↓
Hệ thống route tới checkpoint tương ứng
↓
Camera realtime
↓
MediaPipe
↓
Model
↓
Đếm repetitions
↓
Mỗi rep: Complete / Incomplete
```

Ví dụ:

```text
HAND_OPENING
→ hand_opening/best.pt

ELBOW_EXTENSION
→ elbow_extension/best.pt
```

---

# 3. Mục tiêu mô hình

Mô hình phải giải quyết 2 nhiệm vụ:

## Task A — Rep Counting

Trong một session liên tục:

```text
video/camera stream
↓
phát hiện từng repetition
↓
xác định start / action phase / end
↓
Rep 1, Rep 2, Rep 3, ...
```

Output ví dụ:

```json
{
  "rep_count": 8,
  "repetitions": [
    {
      "rep_id": 1,
      "start_frame": 40,
      "end_frame": 102
    }
  ]
}
```

## Task B — Correctness Classification

Với mỗi rep đã hoàn thành:

```text
rep sequence
↓
classifier
↓
Complete / Incomplete
```

Output:

```json
{
  "rep_id": 5,
  "completion": "incomplete",
  "confidence": 0.81
}
```

Không được tự suy diễn lỗi cụ thể nếu dataset không có nhãn tương ứng.

---

# 4. Kiến trúc bắt buộc

```text
RGB
↓
MediaPipe Pose + Hands
↓
Normalization
↓
Joint / Bone / Motion Features
↓
3-Stream CTR-GCN
↓
Feature Fusion
↓
MS-TCN Temporal Refinement
↓
Rep Segmentation / Rep Counting
↓
Attention Pooling
↓
Classifier
↓
Complete / Incomplete
```

Kiến trúc đầy đủ:

```text
                    RGB CAMERA / VIDEO
                           │
                           ↓
                  MediaPipe Extraction
                    Pose + Hands
                           │
                           ↓
                   Quality Control
                           │
                           ↓
                    Normalization
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ↓             ↓             ↓
          JOINT          BONE          MOTION
          STREAM         STREAM         STREAM
             │             │             │
             ↓             ↓             ↓
          CTR-GCN        CTR-GCN       CTR-GCN
             │             │             │
             └─────────────┼─────────────┘
                           ↓
                     Feature Fusion
                           ↓
                         MS-TCN
                           ↓
              Temporal Phase Refinement
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ↓                           ↓
       Rep Segmentation             Rep Features
             │                           │
             ↓                           ↓
        Rep Counting               Attention Pooling
                                         │
                                         ↓
                                    Classifier
                                         │
                                  ┌──────┴──────┐
                                  ↓             ↓
                              Complete      Incomplete
```

---

# 5. Thiết kế phù hợp dataset vừa phải

Dataset không lớn, vì vậy:

- không dùng backbone quá sâu;
- không dùng channel quá lớn;
- không thêm Transformer lớn ngay từ đầu;
- không thêm nhiều attention module;
- ưu tiên regularization;
- dùng early stopping;
- train-only augmentation;
- dùng subject-wise validation;
- giữ architecture đủ đơn giản để ablation.

Khuyến nghị giai đoạn đầu:

```text
Model A:
HAND_OPENING

Model B:
ELBOW_EXTENSION
```

Cùng kiến trúc nhưng checkpoint riêng.

---

# 6. Input — HAND_OPENING

Ưu tiên:

```text
MediaPipe Hands
21 landmarks
```

Shape:

```text
N × C × T × V
```

Trong đó:

```text
N = batch
C = channels
T = temporal length
V = 21
```

Graph dùng topology 21 điểm của MediaPipe Hands.

---

# 7. Input — ELBOW_EXTENSION

Không bắt buộc dùng toàn bộ 33 pose landmarks.

Ưu tiên subset:

```text
Shoulder
Elbow
Wrist
Hand reference
```

Có thể mở rộng:

```text
Shoulder
Elbow
Wrist
Thumb
Index
Pinky
```

Mục tiêu:

```text
V ≈ 4–8 joints
```

để giảm overfitting và giữ model tập trung vào upper limb.

---

# 8. Normalization

## Hand Opening

Origin:

```text
wrist
```

Translation:

```text
X' = X - X_wrist
```

Scale:

```text
palm_size
```

Ví dụ:

```text
distance(wrist, middle_MCP)
```

Sau đó:

```text
X_norm = X' / palm_size
```

## Elbow Extension

Origin:

```text
shoulder
```

Scale:

```text
upper_arm_length
```

hoặc:

```text
shoulder_to_wrist_distance
```

Không dùng statistic từ test subject.

---

# 9. 3-Stream Features

Ba stream bắt buộc:

```text
Joint
Bone
Motion
```

## 9.1 Joint Stream

```text
J(t, v) = [x, y, z]
```

Có thể thêm visibility nếu extractor ổn định.

Mục tiêu:

```text
học posture / geometry
```

## 9.2 Bone Stream

```text
B(t, v)
=
J(t, v) - J(t, parent(v))
```

Ví dụ elbow:

```text
upper_arm = elbow - shoulder
forearm = wrist - elbow
```

Ví dụ hand:

```text
MCP - wrist
PIP - MCP
DIP - PIP
TIP - DIP
```

Mục tiêu:

```text
học relative skeleton structure
```

## 9.3 Motion Stream

```text
M(t, v)
=
J(t, v) - J(t-1, v)
```

Mục tiêu:

```text
học dynamics của movement
```

Không thêm acceleration ngay bản đầu; có thể dùng cho ablation sau.

---

# 10. 3-Stream CTR-GCN

Tạo 3 branch:

```text
Joint CTR-GCN
Bone CTR-GCN
Motion CTR-GCN
```

Starting configuration gợi ý:

```text
64
64
128
128
```

Ví dụ:

```text
Input
↓
CTR-GCN Block 64
↓
CTR-GCN Block 64
↓
CTR-GCN Block 128
↓
CTR-GCN Block 128
↓
Temporal Feature Map
```

Phải configurable:

```text
depth
channels
dropout
```

---

# 11. Graph Definition

## Hand Graph

Nodes:

```text
0 wrist

1-4 thumb
5-8 index
9-12 middle
13-16 ring
17-20 little
```

Edges dùng topology tự nhiên của MediaPipe Hands.

## Elbow Graph

Ví dụ:

```text
shoulder ↔ elbow
elbow ↔ wrist
wrist ↔ hand
```

Nếu dùng finger refs:

```text
wrist ↔ thumb
wrist ↔ index
wrist ↔ pinky
```

Không thêm node chỉ để làm graph lớn hơn.

---

# 12. Feature Fusion

Input:

```text
F_joint
F_bone
F_motion
```

Bản đầu dùng:

```text
Concatenate
```

Sau đó:

```text
Linear Projection
+
BatchNorm
+
ReLU/GELU
+
Dropout
```

Output:

```text
T × D
```

để đưa vào MS-TCN.

Không dùng cross-attention phức tạp ở phiên bản đầu.

---

# 13. MS-TCN Temporal Refinement

Vai trò:

```text
CTR-GCN
→ học spatial + temporal skeleton relations

MS-TCN
→ refine temporal progression
```

MS-TCN phải hỗ trợ:

1. temporal phase;
2. rep boundary;
3. smoothing;
4. rep segmentation;
5. rep counting.

Starting configuration:

```text
2–3 stages
channels khoảng 128
```

Không mặc định dùng quá nhiều stage.

---

# 14. Temporal States cho Rep Counting

Mô hình không phân loại exercise.

Mỗi selected exercise có phase protocol riêng.

## HAND_OPENING

Có thể dùng:

```text
REST/CLOSED
↓
OPENING
↓
OPEN
↓
RETURN/CLOSING
```

## ELBOW_EXTENSION

Có thể dùng:

```text
REST/FLEXED
↓
EXTENDING
↓
EXTENDED
↓
RETURNING
```

Chỉ sử dụng phase labels nếu annotation đáng tin cậy.

Nếu dataset chưa có phase labels:
- xây annotation protocol;
- annotate subset trước;
- không coi pseudo-label là ground truth thật.

---

# 15. Rep Counting Logic

Một rep chỉ được tính khi chu kỳ hợp lệ hoàn thành.

Ví dụ:

```text
REST
→ MOVING_OUT
→ PEAK
→ MOVING_BACK
→ REST
```

Khi hoàn thành:

```text
rep_count += 1
```

Phải có:

```text
minimum_duration
maximum_duration
minimum_peak_persistence
minimum_confidence
cooldown
```

Tất cả threshold chỉ tune bằng train/validation.

Không tuning bằng test.

---

# 16. MS-TCN Output

Frame-wise output:

```text
phase_logits
T × num_phases
```

Tùy experiment có thể thêm:

```text
boundary_score
T × 1
```

Sau đó:

```text
phase probabilities
↓
state decoder
↓
rep segments
```

Output:

```text
[
  [start_1, end_1],
  [start_2, end_2],
  ...
]
```

---

# 17. Rep-Level Features

Sau khi có:

```text
start_frame
end_frame
```

Trích feature từ:

```text
MS-TCN output feature map
```

trong đoạn:

```text
[start:end]
```

Sau đó đưa qua Attention Pooling.

---

# 18. Attention Pooling

Dùng lightweight temporal attention.

Cho:

```text
H = [h1, h2, ..., hT]
```

Tính:

```text
score_t = W2(tanh(W1 h_t))
```

```text
alpha = softmax(score)
```

```text
R = sum(alpha_t * h_t)
```

Mục tiêu:

```text
tập trung vào các frame quan trọng của rep
```

Không dùng Transformer encoder lớn.

---

# 19. Correctness Classifier

Classifier nhẹ:

```text
R
↓
Linear D → 128
↓
ReLU
↓
Dropout
↓
Linear 128 → 2
↓
Complete / Incomplete
```

Loss:

```text
CrossEntropyLoss
```

Nếu imbalance:
- class weighting;
- weighted sampler;
- focal loss chỉ khi cần.

---

# 20. Multi-Task Loss

Nếu có phase labels:

```text
L_total
=
lambda_phase * L_phase
+
lambda_cls * L_cls
```

Nếu có boundary head:

```text
+
lambda_boundary * L_boundary
```

Các lambda phải configurable.

Không hard-code rồi coi là tối ưu.

---

# 21. Two-Step Training nếu dataset quá nhỏ

Có thể thử:

## Stage 1

```text
CTR-GCN + MS-TCN
→ temporal representation
```

## Stage 2

```text
freeze một phần backbone
→ train attention + classifier
```

Sau đó:

```text
end-to-end fine-tune nhẹ
```

Đây là experiment, không bắt buộc mặc định.

---

# 22. Split dữ liệu

Bắt buộc:

```text
split by subject
```

TRƯỚC:

```text
windowing
augmentation
oversampling
```

Không để frame/video cùng subject xuất hiện ở cả train và test.

---

# 23. LOSO

Nếu có 10 subjects:

```text
Fold 1: Test S01
Fold 2: Test S02
...
Fold 10: Test S10
```

Mỗi fold:

```text
Train subjects
Validation subjects
Test subject
```

Không dùng test để:
- chọn checkpoint;
- chọn threshold;
- chọn augmentation;
- chọn architecture;
- chọn loss weights.

---

# 24. Augmentation

Chỉ áp dụng trên train.

Có thể dùng:

```text
small coordinate jitter
small translation
small scaling
short landmark dropout
short frame dropout
missing-mask simulation
```

Có thể thử temporal resampling nhẹ nếu không đổi nhãn.

Không dùng:

```text
frame reversal
extreme speed changes
arbitrary ROM distortion
crop mất phần cuối động tác
```

Nếu thay đổi coordinates, phải recompute:

```text
bone
motion
velocity
acceleration nếu có
```

---

# 25. Missing Landmarks

Phải giữ:

```text
original_missing_mask
```

Pipeline:

```text
raw landmarks
↓
missing mask
↓
quality check
↓
short-gap interpolation
↓
normalized landmarks
```

Không impute các gap quá dài mà không ghi nhận.

---

# 26. Baselines bắt buộc

Để bài có tính nghiên cứu, so sánh:

```text
Baseline 0
Majority Class

Baseline 1
MLP / simple features

Baseline 2
LSTM hoặc BiLSTM

Baseline 3
TCN

Baseline 4
Joint-only CTR-GCN

Baseline 5
3-Stream CTR-GCN
```

Proposed:

```text
3-Stream CTR-GCN
+
MS-TCN
+
Attention Pooling
```

---

# 27. Ablation Study

Bắt buộc:

```text
A0
Joint CTR-GCN

A1
Joint + Bone CTR-GCN

A2
Joint + Bone + Motion CTR-GCN

A3
3-Stream CTR-GCN + MS-TCN

A4
3-Stream CTR-GCN + MS-TCN + Attention
```

Có thể thêm:

```text
A5
without normalization

A6
without motion stream
```

nếu thời gian cho phép.

---

# 28. Metrics — Correctness

Báo cáo riêng cho từng bài:

```text
Accuracy
Macro Precision
Macro Recall
Macro F1
Weighted F1
Confusion Matrix
```

Nếu LOSO:

```text
mean ± std
```

Không chỉ báo Accuracy.

---

# 29. Metrics — Rep Counting

Báo cáo:

```text
MAE
RMSE
Exact Count Accuracy
Count Error Distribution
```

Ví dụ:

```text
true = 10
pred = 9
absolute error = 1
```

---

# 30. Metrics — Rep Segmentation

Nếu có ground-truth boundaries:

```text
Boundary Precision
Boundary Recall
Boundary F1
Temporal IoU
```

Phải định nghĩa tolerance rõ ràng.

---

# 31. Product / Realtime Metrics

Đo thật:

```text
MediaPipe FPS
model inference latency
end-to-end latency
memory
CPU/GPU usage
rep event delay
```

Không bịa FPS hoặc latency.

---

# 32. Realtime Inference

```text
Camera
↓
MediaPipe
↓
rolling landmark buffer
↓
Normalization
↓
Joint/Bone/Motion
↓
3-Stream CTR-GCN
↓
MS-TCN
↓
state decoder
↓
rep completed event
↓
Attention Pooling
↓
Complete/Incomplete
↓
UI
```

Ví dụ event:

```json
{
  "type": "rep_completed",
  "exercise": "HAND_OPENING",
  "rep_id": 6,
  "completion": "complete",
  "confidence": 0.89,
  "start_time": 12.31,
  "end_time": 14.05
}
```

---

# 33. Sliding Window

Realtime dùng:

```text
rolling temporal buffer
```

Các tham số:

```text
window_size
stride
```

phải configurable.

State decoder phải tránh:

```text
double-count
```

---

# 34. Confidence Handling

Nếu confidence thấp, không ép output.

Có thể dùng internal state:

```text
UNCERTAIN
```

UI:

> Hệ thống chưa đủ chắc chắn để đánh giá lần này.

---

# 35. Exercise Selection Contract

Frontend gửi:

```json
{
  "exercise_type": "HAND_OPENING"
}
```

hoặc:

```json
{
  "exercise_type": "ELBOW_EXTENSION"
}
```

Backend route tới model tương ứng.

Không có exercise classification head.

---

# 36. Repo Structure

```text
rehabai_ml/
├── configs/
│   ├── hand_opening.yaml
│   └── elbow_extension.yaml
├── data/
│   ├── loaders/
│   ├── preprocessing/
│   ├── augmentation/
│   └── graphs/
├── models/
│   ├── ctr_gcn/
│   ├── ms_tcn/
│   ├── attention/
│   ├── fusion/
│   └── rehab_ctr_tcn.py
├── training/
│   ├── train.py
│   ├── losses.py
│   ├── scheduler.py
│   └── checkpoint.py
├── evaluation/
│   ├── classification_metrics.py
│   ├── rep_count_metrics.py
│   ├── segmentation_metrics.py
│   └── loso.py
├── inference/
│   ├── offline.py
│   ├── realtime.py
│   └── state_decoder.py
├── scripts/
│   ├── extract_landmarks.py
│   ├── build_features.py
│   ├── train_loso.py
│   ├── run_ablation.py
│   └── benchmark_realtime.py
└── tests/
```

---

# 37. Config mẫu

```yaml
exercise: HAND_OPENING

input:
  joints: 21
  coords: 3
  use_visibility: false

features:
  joint: true
  bone: true
  motion: true

ctr_gcn:
  channels: [64, 64, 128, 128]
  dropout: 0.3

fusion:
  type: concat
  output_dim: 128

ms_tcn:
  stages: 2
  channels: 128
  kernel_size: 3

attention:
  enabled: true
  hidden_dim: 64

classifier:
  hidden_dim: 64
  num_classes: 2

training:
  batch_size: 16
  optimizer: adamw
  early_stopping: true

evaluation:
  subject_wise: true
  loso: true
```

Các số trên là **starting configuration**, không phải kết luận tối ưu.

---

# 38. Training Strategy

```text
1. Verify real landmarks
2. Train LSTM/TCN baselines
3. Train Joint CTR-GCN
4. Train 3-Stream CTR-GCN
5. Add MS-TCN
6. Add Attention Pooling
7. Run ablation
8. Run LOSO
9. Benchmark realtime
```

Không nhảy thẳng vào full model mà không có baseline.

---

# 39. Regularization

Dùng:

```text
Dropout
Weight Decay
Early Stopping
Train-only Augmentation
Learning-rate Scheduler
Gradient Clipping nếu cần
```

Theo dõi:

```text
train loss
validation loss
macro F1
rep MAE
```

---

# 40. Research Questions

Có thể đặt:

> Liệu việc kết hợp 3-stream CTR-GCN với MS-TCN temporal refinement có cải thiện đồng thời khả năng đếm repetitions và đánh giá Complete/Incomplete trong các bài phục hồi chi trên từ landmark sequences hay không?

Sub-questions:

```text
RQ1:
Joint/Bone/Motion có tốt hơn Joint-only?

RQ2:
MS-TCN có cải thiện rep segmentation và rep counting?

RQ3:
Attention Pooling có cải thiện Complete/Incomplete?

RQ4:
Mô hình có đạt latency đủ cho realtime RehabAI không?
```

---

# 41. Tên mô hình đề xuất

Có thể dùng:

```text
RehabCTR-TCN
```

Tên đầy đủ:

```text
RehabCTR-TCN:
A Three-Stream CTR-GCN with Multi-Stage Temporal Refinement
for Repetition Counting and Exercise Correctness Assessment
```

Không tuyên bố kiến trúc hoàn toàn mới nếu chỉ kết hợp các thành phần đã tồn tại.

Novelty nên tập trung vào:
- ứng dụng rehabilitation;
- 3-stream skeletal features;
- rep segmentation + correctness joint pipeline;
- exercise-specific routing;
- realtime deployment;
- protocol đánh giá.

---

# 42. Product Flow

```text
User Login
↓
Select Exercise
↓
HAND_OPENING / ELBOW_EXTENSION
↓
Camera Setup
↓
Realtime Tracking
↓
Rep Detection
↓
Rep Count +1
↓
Complete / Incomplete
↓
Timeline
↓
Session Summary
```

---

# 43. Session Output

```json
{
  "exercise": "ELBOW_EXTENSION",
  "total_reps": 10,
  "complete_reps": 8,
  "incomplete_reps": 2,
  "repetitions": [
    {
      "rep": 1,
      "start": 1.25,
      "end": 3.10,
      "completion": "complete",
      "confidence": 0.91
    }
  ]
}
```

---

# 44. Không dùng LLM để quyết định movement correctness

```text
Camera
↓
MediaPipe
↓
RehabCTR-TCN
↓
Structured Result
↓
Backend
↓
Optional Ollama explanation
```

Ollama chỉ giải thích.

Không dùng Ollama để:
- đếm rep;
- quyết định Complete/Incomplete;
- tạo movement ground truth.

---

# 45. Unit Tests

Phải test:

```text
graph edges
bone calculation
motion calculation
normalization
tensor shapes
fusion
MS-TCN output
attention pooling
state decoder
rep counter
no double count
checkpoint loading
exercise routing
```

---

# 46. Integration Tests

Test pipeline:

```text
video
↓
MediaPipe
↓
model
↓
rep events
↓
session summary
```

cho cả 2 bài.

---

# 47. Bảng kết quả cuối

| Model | Hand Macro-F1 | Elbow Macro-F1 | Rep MAE | Params | Latency |
|---|---:|---:|---:|---:|---:|
| LSTM | | | | | |
| TCN | | | | | |
| Joint CTR-GCN | | | | | |
| 3-Stream CTR-GCN | | | | | |
| CTR-GCN + MS-TCN | | | | | |
| Full Proposed | | | | | |

Không điền số giả.

---

# 48. Bảng Ablation

| Variant | Joint | Bone | Motion | MS-TCN | Attention | Macro-F1 | Rep MAE |
|---|---|---|---|---|---|---:|---:|
| A0 | ✓ | | | | | | |
| A1 | ✓ | ✓ | | | | | |
| A2 | ✓ | ✓ | ✓ | | | | |
| A3 | ✓ | ✓ | ✓ | ✓ | | | |
| A4 | ✓ | ✓ | ✓ | ✓ | ✓ | | |

---

# 49. Tiêu chí product-ready

Model chỉ được coi là product-ready khi:

- rep counting hoạt động trên video thật;
- không double-count;
- correctness có confidence;
- xử lý tracking lost;
- không crash khi landmark thiếu;
- latency được benchmark;
- inference chạy trên target backend;
- không phụ thuộc LLM;
- session summary lưu được;
- UI nhận rep event realtime.

Không tự đặt metric target giả.

---

# 50. Prompt thực thi ngắn gọn cho Agent

```text
Hãy triển khai RehabAI theo kiến trúc:

RGB
→ MediaPipe Pose + Hands
→ Normalization
→ Joint / Bone / Motion Features
→ 3-Stream CTR-GCN
→ Feature Fusion
→ MS-TCN Temporal Refinement
→ Rep Segmentation / Rep Counting
→ Attention Pooling
→ Complete / Incomplete Classifier.

Hệ thống chỉ có 2 bài:
HAND_OPENING và ELBOW_EXTENSION.

Người dùng chọn bài trước nên KHÔNG cần exercise classification.

Mỗi bài dùng checkpoint riêng ở giai đoạn đầu.

Mục tiêu sản phẩm:
1. camera realtime;
2. tự đếm repetitions trong một session;
3. mỗi repetition trả Complete / Incomplete;
4. có confidence;
5. không double-count;
6. không phụ thuộc Ollama để quyết định movement correctness.

Mục tiêu nghiên cứu:
1. so sánh LSTM, TCN, Joint CTR-GCN, 3-Stream CTR-GCN;
2. đánh giá CTR-GCN + MS-TCN;
3. đánh giá Attention Pooling;
4. chạy ablation Joint/Bone/Motion;
5. đánh giá subject-wise LOSO;
6. báo Macro-F1 và rep-count MAE;
7. đo latency/FPS thật;
8. không dùng test để tuning;
9. không báo kết quả từ mock/synthetic data.

Vì dataset vừa phải:
- dùng CTR-GCN nhẹ;
- MS-TCN 2–3 stage;
- regularization;
- early stopping;
- train-only augmentation;
- không thêm Transformer lớn;
- không thêm module không cần thiết.

Trước khi code:
- xác nhận landmarks là MediaPipe thật;
- xác nhận subject_id;
- xác nhận split subject-wise;
- kiểm tra missing landmarks;
- xác nhận nhãn Complete/Incomplete;
- kiểm tra protocol rep boundary.

Sau khi code:
- chạy unit tests;
- integration tests;
- LOSO;
- ablation;
- realtime benchmark.

Không tự bịa metric.
Không kết luận proposed model tốt hơn trước khi thực nghiệm thật.
```

---

# 51. Kiến trúc cuối cùng cần giữ

```text
RGB
↓
MediaPipe Pose + Hands
↓
Normalization
↓
Joint / Bone / Motion Features
↓
┌───────────────────────────────────────┐
│         3-STREAM CTR-GCN              │
│                                       │
│ Joint CTR-GCN                         │
│ Bone CTR-GCN                          │
│ Motion CTR-GCN                        │
└───────────────────────────────────────┘
↓
Feature Fusion
↓
MS-TCN Temporal Refinement
↓
Temporal Phase / Boundary Decoder
↓
Rep Segmentation
↓
Rep Counting
↓
Rep-Level Feature Sequence
↓
Attention Pooling
↓
Classifier
↓
Complete / Incomplete
```

Đây là kiến trúc trung tâm của dự án.

Mọi thay đổi lớn phải được thực hiện dưới dạng experiment/ablation thay vì âm thầm đổi architecture.
