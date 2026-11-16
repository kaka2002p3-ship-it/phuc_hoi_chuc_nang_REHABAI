# RehabAI — NECK_LATERAL_STRETCH WITHOUT TRAINING

## Master implementation prompt
**Mục tiêu:** triển khai bài thư giãn cổ-vai/`NECK_LATERAL_STRETCH` ổn định mà **không cần dataset, không train model, không checkpoint**.

Kiến trúc mục tiêu:

```text
Camera
→ MediaPipe Pose
→ Landmark Quality Gate
→ Per-User Calibration
→ Head Tilt Angle Relative to Shoulder Line
→ Shoulder/Torso Stability
→ Smoothing + Outlier Filter
→ Hysteresis
→ Rule-Based State Machine
→ Hold Validation
→ Return-To-Center Validation
→ Rep Counting
→ Session Result
```

---

# 0. QUY TẮC BẮT BUỘC

1. Không train deep learning cho bài này.
2. Không thêm classifier chỉ để nhận diện rep.
3. Không dùng một threshold đơn lẻ kiểu `angle > X => rep++`.
4. Rep chỉ được tính khi đi đủ chu trình state machine.
5. Mọi threshold phải nằm trong config, không magic number rải rác.
6. Threshold mặc định chỉ là **starting defaults để test**, không phải chuẩn y khoa.
7. Tracking loss không được gán thành user làm sai.
8. Nếu evidence không đủ, dùng `TRACKING_INSUFFICIENT` hoặc `UNKNOWN`.
9. Không nói “đúng về lâm sàng”, “cổ khỏe”, “an toàn tuyệt đối”, “góc chuẩn cho mọi người”.
10. Public website tuyệt đối không được chạy camera/MediaPipe/session.
11. Chỉ authenticated `/app/*` mới chạy bài.
12. Ollama không được tính góc, đổi state, đếm rep hay override CV engine.
13. Nếu Ollama lỗi, exercise vẫn phải chạy.
14. Không phá `HAND_OPENING`, `ELBOW_EXTENSION`, `DEEP_BREATHING`, auth, history, AI Coach.
15. Audit repo trước khi code.
16. Không báo `PASS` hay `production-ready` nếu chưa test thật.

---

# 1. AUDIT REPO TRƯỚC KHI TRIỂN KHAI

Trước khi sửa code, ghi rõ:

```text
CURRENT_CAMERA_COMPONENT:
CURRENT_MEDIAPIPE_PIPELINE:
CURRENT_EXERCISE_ROUTES:
CURRENT_SESSION_API:
CURRENT_WEBSOCKET:
CURRENT_AUTH:
CURRENT_HISTORY:
CURRENT_CONFIG_PATTERN:
CURRENT_TEST_FRAMEWORK:
REUSE_PLAN:
RISK_AREAS:
```

Không refactor lớn trước audit.

---

# 2. ROUTE / AUTH BOUNDARY

Public:

```text
/exercises/neck-lateral-stretch
```

chỉ hiển thị:
- giới thiệu;
- mục tiêu;
- hình/video;
- hướng dẫn;
- CTA login/register.

Không:
- request camera;
- start MediaPipe;
- realtime angle;
- rep count;
- session.

Protected:

```text
/app/exercises/neck-lateral-stretch
```

hoặc:

```text
/app/session/neck-lateral-stretch
```

mới được chạy bài.

Nếu chưa login:
```text
redirect → /login?redirect=/app/exercises/neck-lateral-stretch
```

---

# 3. LANDMARKS

Ưu tiên MediaPipe Pose.

Bắt buộc:
```text
LEFT_EAR
RIGHT_EAR
LEFT_SHOULDER
RIGHT_SHOULDER
```

Khuyến nghị thêm:
```text
NOSE
LEFT_HIP
RIGHT_HIP
```

Mục đích:
- tai: ước lượng tilt đầu;
- vai: shoulder line;
- hông: torso stability;
- nose: sanity check/rotation heuristic nếu cần.

---

# 4. QUALITY GATE

Mỗi frame kiểm tra:
```text
left_ear_visibility
right_ear_visibility
left_shoulder_visibility
right_shoulder_visibility
```

Config khởi đầu:
```json
{
  "min_landmark_visibility": 0.60,
  "min_good_frames_ratio": 0.70
}
```

Nếu landmark không đủ:
```text
TRACKING_INSUFFICIENT
```

Không dùng stale landmark để tiếp tục tính góc.

---

# 5. CAMERA SETUP

Khuyến nghị:
- camera nhìn tương đối chính diện;
- đầu và hai vai nằm rõ trong frame;
- ánh sáng đủ;
- camera không quá thấp/cao;
- không đặt chéo mạnh.

UI guidance:
```text
"Hãy giữ đầu và hai vai nằm rõ trong khung hình."
```

---

# 6. CENTER CALIBRATION — BẮT BUỘC

Trước session, user nhìn thẳng và giữ tư thế thoải mái 2–5 giây.

Tính median:
```text
baseline_head_angle
baseline_shoulder_angle
baseline_torso_angle
baseline_noise
```

Trong session:
```text
relative_head_angle =
current_head_angle - baseline_head_angle
```

Nếu calibration tracking kém:
- không start;
- yêu cầu chỉnh camera/posture.

Mục tiêu:
- giảm bias do camera hơi nghiêng;
- giảm bias do posture ban đầu khác nhau.

---

# 7. CÁCH TÍNH HEAD TILT — ƯU TIÊN

## Ear line relative to shoulder line

```text
ear_line_angle =
atan2(
    right_ear_y - left_ear_y,
    right_ear_x - left_ear_x
)

shoulder_line_angle =
atan2(
    right_shoulder_y - left_shoulder_y,
    right_shoulder_x - left_shoulder_x
)

head_tilt_relative =
normalize_angle(
    ear_line_angle - shoulder_line_angle
)
```

Ưu điểm:
- ít phụ thuộc camera hơi nghiêng;
- đầu được đo tương đối với vai.

Viết helper normalize angle rõ ràng, tránh lỗi quanh ±180°.

---

# 8. FALLBACK ANGLE

Nếu ear pair không đủ ổn, chỉ fallback khi đã test:

```text
ear_midpoint
shoulder_midpoint

neck_vector = ear_midpoint - shoulder_midpoint

angle = atan2(dx, -dy)
```

Nếu confidence thấp:
```text
TRACKING_INSUFFICIENT
```

Không đoán.

---

# 9. SIGN CONVENTION

Định nghĩa rõ trong code, ví dụ:

```text
negative = LEFT_TILT
positive = RIGHT_TILT
```

Bắt buộc unit test:
- left không thành right;
- right không thành left;
- selfie mirror không đảo raw geometry.

Không để CSS mirror làm sai logic.

---

# 10. SHOULDER / TORSO COMPENSATION

Theo dõi:

```text
shoulder_line_angle
shoulder_midpoint displacement
torso_tilt
```

Nếu người dùng nghiêng cả thân:

```text
compensation_detected = true
```

Ví dụ:

```text
abs(current_shoulder_angle - baseline_shoulder_angle)
> max_shoulder_tilt_deg
```

Nếu hips rõ:
```text
mid_shoulder
mid_hip
torso_vector = mid_shoulder - mid_hip
```

Tính torso tilt tương đối baseline.

Nếu compensation quá lớn:
- không dùng frame để trigger target;
- không count rep;
- đưa guidance nhẹ.

UI:
```text
"Hãy cố giữ vai tương đối ổn định khi nghiêng đầu."
```

Không nói:
```text
"Bạn đang tập sai."
```

---

# 11. NORMALIZATION

Angle tự nhiên gần như scale-invariant.

Nếu dùng displacement:
```text
normalized_shift =
delta_position / shoulder_width
```

Không threshold raw pixel.

---

# 12. SMOOTHING

Không dùng raw angle từng frame.

Ưu tiên EMA:

```text
smoothed_t =
alpha * current + (1-alpha) * previous
```

Config:
```json
{
  "angle_ema_alpha": 0.25,
  "shoulder_ema_alpha": 0.25
}
```

Có thể thêm median filter nhẹ trước EMA nếu jitter.

Không filter quá mạnh gây delay.

---

# 13. OUTLIER FILTER

Nếu:
```text
abs(angle_t - angle_t-1) > max_angle_jump_deg
```

→ mark outlier.

Config khởi đầu:
```json
{
  "max_angle_jump_deg": 12
}
```

Không trigger state từ outlier frame.

---

# 14. MISSING LANDMARK

Short gap:
```text
<= short_gap_frames
```
→ giữ state rất ngắn nếu hợp lý.

Long gap:
```text
> long_gap_frames
```
→ `TRACKING_INSUFFICIENT`.

Không interpolate gap dài để giả signal.

---

# 15. PER-USER TARGET CALIBRATION — KHUYẾN NGHỊ

Ngoài center calibration, có thể cho user nghiêng **thoải mái**, không phải tối đa:

```text
CENTER CALIBRATION
→ LEFT COMFORTABLE TILT
→ RIGHT COMFORTABLE TILT
```

Lưu:
```text
comfortable_left_angle
comfortable_right_angle
```

Tạo target theo tỷ lệ cấu hình, ví dụ:
```text
70–90% vùng nghiêng thoải mái
```

Không coi đó là clinical ROM.

Hỗ trợ:
```text
FIXED_CONFIG
PERSONALIZED_CALIBRATION
```

Khuyến nghị ưu tiên:
```text
PERSONALIZED_CALIBRATION
```
nếu UX calibration ổn.

---

# 16. CONFIG KHỞI ĐẦU

Tạo một file config tập trung:

```json
{
  "center_tolerance_deg": 6,
  "target_min_deg": 15,
  "target_max_deg": 30,
  "return_tolerance_deg": 7,

  "hold_seconds": 3.0,
  "min_phase_ms": 250,
  "rep_cooldown_ms": 800,

  "min_landmark_visibility": 0.60,
  "min_good_frames_ratio": 0.70,

  "max_shoulder_tilt_deg": 8,
  "max_torso_tilt_deg": 8,
  "max_normalized_shoulder_shift": 0.12,

  "angle_ema_alpha": 0.25,
  "max_angle_jump_deg": 12,

  "short_gap_frames": 3,
  "long_gap_frames": 10,

  "target_mode": "PERSONALIZED_CALIBRATION"
}
```

Tất cả chỉ là starting defaults để test và tuning.

---

# 17. STATE MACHINE

States:

```text
IDLE
CALIBRATING
CENTER
MOVING_LEFT
MOVING_RIGHT
TARGET_LEFT
TARGET_RIGHT
HOLD_LEFT
HOLD_RIGHT
RETURNING_FROM_LEFT
RETURNING_FROM_RIGHT
TRACKING_INSUFFICIENT
PAUSED
COMPLETED
```

Left flow:
```text
CENTER
→ MOVING_LEFT
→ TARGET_LEFT
→ HOLD_LEFT
→ RETURNING_FROM_LEFT
→ CENTER
```

Right flow:
```text
CENTER
→ MOVING_RIGHT
→ TARGET_RIGHT
→ HOLD_RIGHT
→ RETURNING_FROM_RIGHT
→ CENTER
```

Không cho transition tùy ý.

---

# 18. CENTER

CENTER khi:
```text
abs(relative_head_angle)
<= center_tolerance_deg
```

và:
```text
tracking good
compensation false
```

Phải giữ đủ `center_confirm_ms` hoặc tương đương để tránh jitter.

---

# 19. MOVING

Khi angle rời center theo hướng ổn định:

```text
LEFT:
angle < -center_tolerance_deg

RIGHT:
angle > center_tolerance_deg
```

Phải tồn tại ít nhất:
```text
min_phase_ms
```

---

# 20. TARGET

Target đạt khi:
```text
target_min_deg
<= abs(relative_head_angle)
<= target_max_deg
```

và:
- landmark quality tốt;
- compensation trong giới hạn.

Không dùng một frame duy nhất để xác nhận.

---

# 21. HYSTERESIS — BẮT BUỘC

Ví dụ:
```text
enter_target = 15°
exit_target = 13°

enter_center = 6°
exit_center = 8°
```

Mục tiêu:
- tránh state flip quanh threshold;
- tránh duplicate rep.

Nếu cần, tách các giá trị này thành config riêng.

---

# 22. HOLD

Khi đã ở target ổn định:

```text
start hold timer
```

Nếu giữ trong target đủ:
```text
hold_seconds
```

→ `HOLD_OK`.

Nếu ra khỏi target quá lâu:
- reset hold;
- hoặc quay lại MOVING theo rule.

---

# 23. RETURNING

Sau `HOLD_OK`, khi angle magnitude giảm về center:

```text
RETURNING
```

Rep chỉ được count khi:
```text
abs(angle) <= return_tolerance_deg
```

và center được xác nhận ổn định.

---

# 24. REP COUNT RULE

**Một rep hợp lệ duy nhất khi:**

```text
CENTER
→ MOVING
→ TARGET
→ HOLD_OK
→ RETURNING
→ CENTER
```

Sau đó:
```text
rep_count += 1
```

Không count:
- khi vừa chạm target;
- khi chỉ hold;
- khi chưa quay lại center.

---

# 25. DUPLICATE PREVENTION

Bắt buộc có:
```text
rep_id
last_completed_side
last_rep_timestamp
cooldown
state lock
```

Sau count:
- áp `rep_cooldown_ms`;
- hoặc yêu cầu CENTER ổn định trước rep mới.

---

# 26. LEFT / RIGHT COUNT

Lưu riêng:
```text
left_reps
right_reps
total_reps
```

Ví dụ:
```json
{
  "left_reps": 3,
  "right_reps": 3,
  "total_reps": 6
}
```

---

# 27. INTERRUPTED REP

Rep interrupted nếu:
- tracking mất dài;
- user stop;
- camera lỗi;
- phase timeout;
- compensation quá lớn;
- user rời frame.

Lưu:
```text
interrupted_reps += 1
```

Không gán `INCOMPLETE` nếu nguyên nhân là tracking.

---

# 28. ROTATION VS LATERAL FLEXION

Optional heuristic:
- nose displacement;
- ear visibility asymmetry;
- face orientation nếu project đã có Face/Pose phù hợp.

Nếu nghi user đang quay đầu:
```text
ROTATION_SUSPECTED
```

Chỉ dùng để flag nếu chưa validate.
Không biến thành medical classification.

---

# 29. PHASE TIMEOUT

Config:
```json
{
  "max_moving_seconds": 8,
  "max_hold_seconds": 10,
  "max_return_seconds": 8
}
```

Nếu timeout:
- mark interrupted;
- reset state;
- không để state machine treo.

---

# 30. SESSION FLOW

```text
Authenticated User
→ Exercise Instructions
→ Camera Setup
→ Center Calibration
→ Optional Personalized Range Calibration
→ READY
→ START
→ Realtime Tracking
→ Rep Counting
→ Finish
→ Result
→ History / Progress
```

---

# 31. SESSION RESULT

Ví dụ:

```json
{
  "exercise": "NECK_LATERAL_STRETCH",
  "protocol_version": "v1",
  "algorithm_version": "rule_based_v1",
  "target_mode": "PERSONALIZED_CALIBRATION",

  "left_reps": 3,
  "right_reps": 3,
  "total_reps": 6,
  "interrupted_reps": 1,

  "average_hold_seconds": 3.2,

  "tracking_quality": "GOOD",
  "tracking_coverage": 0.94,

  "session_status": "COMPLETED"
}
```

Không lưu field như:
```text
clinical_correctness
injury_risk
diagnosis
medical_ROM
```
nếu chưa được chuyên môn xác nhận.

---

# 32. REP EVENT

```json
{
  "rep_index": 2,
  "side": "LEFT",
  "target_reached": true,
  "hold_completed": true,
  "returned_to_center": true,
  "tracking_quality": "GOOD",
  "compensation_detected": false,
  "duration_seconds": 6.4
}
```

---

# 33. FRONTEND

Frontend nên có:
- camera preview;
- framing guide;
- calibration progress;
- current phase;
- left/right direction;
- target indicator;
- hold countdown;
- rep count;
- tracking quality;
- compensation guidance;
- pause/stop.

Debug-only panel:
```text
raw_head_angle
smoothed_head_angle
shoulder_angle
torso_angle
visibility
state
hold_timer
compensation
```

Không hiển thị debug production mặc định.

---

# 34. BACKEND

Backend chịu trách nhiệm:
- auth;
- ownership;
- session persistence;
- rep events;
- history;
- progress;
- config/version metadata.

Nếu CV đang chạy client-side, không bắt buộc backend tính angle.

---

# 35. OLLAMA

Ollama chỉ:
- giải thích;
- động viên;
- diễn đạt kết quả engine;
- trả lời câu hỏi chung.

Ollama không:
- tính góc;
- đổi phase;
- count rep;
- override tracking;
- bịa nguyên nhân movement.

---

# 36. ERROR STATES

Tạo:
```text
CAMERA_DENIED
CAMERA_UNAVAILABLE
POSE_NOT_FOUND
EAR_NOT_VISIBLE
SHOULDERS_NOT_VISIBLE
TRACKING_POOR
CALIBRATION_FAILED
COMPENSATION_EXCESSIVE
SESSION_SAVE_FAILED
WEBSOCKET_DISCONNECTED
UNKNOWN_ERROR
```

Mỗi error phải có:
- user message;
- retry action;
- technical log.

---

# 37. PRIVACY

Mặc định:
```text
do not store raw video
```

Ưu tiên lưu:
- derived angles;
- state events;
- rep stats;
- tracking metadata.

Không thêm video recording chỉ để debug nếu không cần.

---

# 38. PERFORMANCE

Đo thực tế:
```text
camera FPS
MediaPipe FPS
angle pipeline latency
rep event latency
CPU
memory
```

Không bịa benchmark.

---

# 39. UNIT TEST — GEOMETRY

Bắt buộc:
- horizontal shoulder;
- left tilt;
- right tilt;
- camera/shoulder baseline tilt;
- relative angle;
- ±180 normalization;
- selfie mirror.

---

# 40. UNIT TEST — FILTERING

Test:
- EMA;
- outlier;
- noise near center;
- noise near target;
- short missing gap;
- long missing gap.

---

# 41. UNIT TEST — STATE MACHINE

Test tất cả valid transitions.

Invalid transitions phải bị reject.

Ví dụ:
```text
CENTER → TARGET → CENTER
```
không được count nếu protocol yêu cầu hold.

---

# 42. UNIT TEST — REP COUNT

```text
T01 CENTER → LEFT TARGET → HOLD → CENTER = 1 left
T02 CENTER → RIGHT TARGET → HOLD → CENTER = 1 right
T03 target nhưng hold thiếu = 0
T04 hold đủ nhưng không return = 0
T05 jitter quanh threshold = không duplicate
T06 tracking lost = không fake rep
T07 compensation vượt limit = không count
T08 reset session = count về đúng trạng thái
```

---

# 43. SYNTHETIC TEST

Synthetic sequences chỉ dùng unit test:
- clean left;
- clean right;
- partial;
- threshold jitter;
- noise;
- gaps;
- whole-body tilt;
- camera offset;
- fast;
- slow.

Không dùng synthetic để chứng minh real-world accuracy.

---

# 44. REAL CAMERA TEST — BẮT BUỘC

```text
R01 ngồi yên → 0 rep
R02 1 left rep → 1
R03 1 right rep → 1
R04 6 alternating reps → expected exact count
R05 chưa đạt target → 0
R06 target nhưng hold thiếu → 0
R07 hold đủ nhưng chưa return → 0
R08 nghiêng cả thân → compensation/no false rep
R09 che tai → tracking degradation
R10 low light → quality warning
R11 camera hơi nghiêng → calibration giảm bias
R12 rời frame → tracking insufficient/interruption
```

---

# 45. MULTI-PERSON

Nếu nhiều người:
- dùng subject selection policy nếu đã có;
- nếu chưa đủ robust, yêu cầu chỉ một người trong frame.

Không âm thầm đổi subject.

---

# 46. VALIDATION METRICS

Không tuyên bố “đếm chuẩn” chỉ từ demo.

Đo:
```text
Rep Count MAE
Exact Count Accuracy
False Positive Rep Rate
False Negative Rep Rate
Tracking Failure Rate
Average Rep Detection Delay
```

Nếu có GT boundary:
```text
Boundary Precision
Boundary Recall
Boundary F1
```

---

# 47. VALIDATION PROTOCOL

Khuyến nghị ban đầu:
```text
10–20 participants
```

Bao gồm:
- trái/phải;
- chậm/nhanh;
- partial;
- target reached;
- insufficient hold;
- compensation;
- tracking loss;
- ánh sáng khác nhau;
- camera heights khác nhau.

Không tune threshold trên final test set.

Flow:
```text
pilot/dev users
→ tune config

held-out users
→ final evaluation
```

---

# 48. VERSIONING

Lưu:
```text
protocol_version
config_version
algorithm_version
MediaPipe_version
```

Mỗi session biết version nào đã chạy.

---

# 49. REGRESSION

Sau mỗi thay đổi:
- geometry tests;
- filtering tests;
- state tests;
- rep tests;
- auth tests;
- session save;
- real-camera smoke;
- production build.

---

# 50. ACCEPTANCE CRITERIA

- [ ] Không train
- [ ] Không checkpoint
- [ ] Public không camera
- [ ] `/app` protected
- [ ] Center calibration
- [ ] Head angle relative shoulder
- [ ] Smoothing
- [ ] Hysteresis
- [ ] Visibility gate
- [ ] Hold validation
- [ ] Return-to-center validation
- [ ] Compensation detection
- [ ] Duplicate prevention
- [ ] Tracking-loss handling
- [ ] Left/right count
- [ ] Session persistence
- [ ] History integration
- [ ] Unit tests
- [ ] Real camera tests
- [ ] Metrics thực tế
- [ ] No clinical overclaim
- [ ] No fake PASS

---

# 51. IMPLEMENTATION ORDER

```text
Phase 0  Repository Audit
Phase 1  Protected route + UI shell
Phase 2  Camera reuse
Phase 3  Pose landmark quality
Phase 4  Center calibration
Phase 5  Head/shoulder geometry
Phase 6  Smoothing + outlier handling
Phase 7  State machine
Phase 8  Hold + return validation
Phase 9  Compensation detection
Phase 10 Rep counting
Phase 11 Persistence
Phase 12 Unit tests
Phase 13 Real camera QA
Phase 14 Validation metrics
Phase 15 Regression
```

Mỗi phase:
```text
implement → test → fix → retest
```

---

# 52. FINAL REPORT

```text
AUDIT:
IMPLEMENTED:
REUSED:
ROUTES:
CONFIG:
CALIBRATION:
ANGLE_METHOD:
STATE_MACHINE:
COMPENSATION:
REP_COUNTING:
PERSISTENCE:
UNIT_TESTS:
REAL_CAMERA_TESTS:
METRICS:
PERFORMANCE:
NOT_TESTED:
BLOCKED:
KNOWN_LIMITATIONS:
NEXT_STEPS:
FINAL_STATUS:
```

---

# 53. FINAL EXECUTION INSTRUCTION

```text
Hãy triển khai NECK_LATERAL_STRETCH cho RehabAI theo hướng KHÔNG TRAIN MODEL.

Không dùng classifier deep learning.

Dùng:
MediaPipe Pose
+ Per-User Calibration
+ Head Tilt Angle Relative to Shoulder Line
+ Shoulder/Torso Stability
+ Smoothing
+ Hysteresis
+ Rule-Based State Machine
+ Hold Validation
+ Return-To-Center Validation
+ Rep Counting.

Bắt đầu bằng audit codebase.

Tái sử dụng camera/auth/session/history/WebSocket hiện tại nếu đúng và ổn định.

PUBLIC WEBSITE không được camera.
Chỉ authenticated /app/* được chạy bài.

Rep chỉ count khi đi đủ:
CENTER
→ MOVING
→ TARGET
→ HOLD_OK
→ RETURNING
→ CENTER.

Không count khi chỉ chạm threshold.

Nếu tracking không đủ:
→ TRACKING_INSUFFICIENT / UNKNOWN.

Tracking loss không phải user error.
Target reached không đồng nghĩa clinical correctness.

Mọi threshold nằm trong config.
Không magic numbers rải rác.

Ollama không tham gia angle/state/rep counting.
Nếu Ollama down, exercise vẫn chạy.

Bắt buộc viết:
- geometry unit tests;
- filtering tests;
- state-machine tests;
- rep-count tests;
- auth/route tests;
- session persistence tests;
- real-camera tests;
- failure tests.

Không báo PASS/production-ready/accurate nếu chưa có real-camera validation và metric thực tế.

Cuối cùng xuất report đúng format.
```

---

# 54. NGUYÊN TẮC CUỐI

```text
Target reached ≠ clinically correct
Tracking lost ≠ incomplete movement
Compensation flag ≠ diagnosis
Rep counted ≠ medical assessment
```

Mục tiêu là:
```text
theo dõi hình học
+ xác nhận phase
+ đếm rep ổn định
+ lưu session
```

không phải thay thế đánh giá chuyên môn.
