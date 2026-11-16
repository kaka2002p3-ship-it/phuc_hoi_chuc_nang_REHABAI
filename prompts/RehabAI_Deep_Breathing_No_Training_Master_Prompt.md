# RehabAI — DEEP_BREATHING WITHOUT TRAINING
## Master Implementation Prompt
## Rule-Based + Guided Timer + MediaPipe Visibility + Motion Signal
## Mục tiêu: triển khai bài tập hít thở sâu KHÔNG cần train model

> Đây là prompt triển khai hoàn chỉnh cho bài `DEEP_BREATHING` trong RehabAI.
>
> Mục tiêu chính:
>
> ```text
> KHÔNG cần dataset
> KHÔNG cần huấn luyện deep learning
> KHÔNG cần classifier Complete/Incomplete kiểu mô hình học máy
> KHÔNG được tuyên bố “đúng về mặt lâm sàng”
> ```
>
> Thay vào đó, hệ thống dùng:
>
> ```text
> Guided Breathing Timer
> +
> Camera Visibility Check
> +
> MediaPipe Pose
> +
> Shoulder / Upper-Chest Motion Signal
> +
> Signal Smoothing
> +
> Rule-Based State Machine
> +
> Cycle Counting
> ```
>
> Mục tiêu sản phẩm:
> - hướng dẫn người dùng hít vào / thở ra;
> - xác định sơ bộ các phase thở dựa trên chuyển động camera;
> - đếm chu kỳ;
> - phát hiện session bị gián đoạn;
> - phát hiện tracking không đủ;
> - tuyệt đối không chẩn đoán hoặc kết luận “thở đúng về mặt y khoa”.

---

# 0. NGUYÊN TẮC TỐI CAO

BẮT BUỘC:

1. Không train model.
2. Không thêm deep learning mới cho bài DEEP_BREATHING.
3. Không dùng synthetic/pseudo-label để giả vờ có model.
4. Không dùng `Complete / Incomplete` theo nghĩa “đúng/sai về y khoa”.
5. Không đưa threshold tùy tiện vào production mà không expose config.
6. Không hard-code giá trị magic number rải rác.
7. Mọi threshold phải nằm trong config.
8. Nếu signal không đủ rõ:
   - trả `TRACKING_INSUFFICIENT`
   - không suy diễn.
9. Nếu phase không xác định:
   - dùng `UNKNOWN`
   - không đoán.
10. Nếu người dùng rời khung:
   - pause / mark interruption theo rule
   - không gán lỗi người tập.
11. Public website không được chạy bài này.
12. Chỉ `/app/*` sau login mới được request camera.
13. Nếu Ollama lỗi:
   - bài tập vẫn phải hoạt động.
14. Nếu camera/MediaPipe lỗi:
   - guided timer vẫn có thể fallback nếu product cho phép
   - nhưng phải ghi rõ tracking unavailable.
15. Không báo “đã hoàn thành đúng bài thở” nếu chỉ có timer mà không có camera evidence.
16. Không nói “phổi hoạt động tốt”, “hô hấp bình thường”, “thở đúng”, “không có vấn đề”.
17. Không suy ra bệnh lý, lo âu, SpO2, dung tích phổi, hô hấp sâu thật sự chỉ từ camera.

---

# 1. VAI TRÒ CỦA CODING AGENT

Bạn là:

- Senior Computer Vision Engineer
- Senior Frontend Engineer
- Senior Backend Engineer
- Signal Processing Engineer
- QA Engineer
- Product Safety Engineer

Nhiệm vụ:

1. audit codebase hiện tại trước khi code;
2. xác định frontend/backend hiện tại;
3. xác định MediaPipe implementation hiện có;
4. tái sử dụng camera component hiện có nếu ổn;
5. không phá các exercise khác;
6. không phá auth;
7. không phá session/history;
8. triển khai DEEP_BREATHING như một module độc lập;
9. viết test;
10. benchmark runtime;
11. báo rõ phần nào `PASS / FAIL / BLOCKED / NOT_TESTED`.

---

# 2. ROUTE / AUTH BOUNDARY

Public:

```text
/exercises/deep-breathing
```

chỉ để:
- giới thiệu;
- hướng dẫn;
- video/hình minh họa;
- CTA login.

Không camera.

Protected:

```text
/app/exercises/deep-breathing
```

hoặc:

```text
/app/session/deep-breathing
```

mới được:
- request camera;
- MediaPipe;
- motion signal;
- breathing state machine;
- cycle count;
- session save.

---

# 3. HIGH-LEVEL ARCHITECTURE

```text
Authenticated User
↓
Deep Breathing Exercise Screen
↓
Camera Setup
↓
MediaPipe Pose
↓
Visibility Quality Gate
↓
Shoulder / Upper-Chest Signal
↓
Normalize
↓
Smooth
↓
Derivative / Trend
↓
Breathing Phase Estimator
↓
Rule-Based State Machine
↓
Cycle Counter
↓
Session Summary
```

Song song:

```text
Guided Timer
↓
INHALE / HOLD / EXHALE prompts
```

Kết hợp:

```text
Guided Timer
+
Observed Motion Signal
+
Tracking Quality
```

---

# 4. MVP PRODUCT MODE

Triển khai mode đầu tiên:

```text
GUIDED_BREATHING
```

Không phải:

```text
DIAGNOSTIC_BREATHING_ANALYSIS
```

Default protocol đề xuất:

```text
INHALE: 4s
HOLD: 0s hoặc optional
EXHALE: 6s
REST: optional
```

Nhưng KHÔNG hard-code.

Config:

```json
{
  "inhale_seconds": 4,
  "hold_seconds": 0,
  "exhale_seconds": 6,
  "rest_seconds": 0,
  "target_cycles": 6
}
```

---

# 5. PHASES

Enum:

```text
IDLE
READY
INHALE
HOLD
EXHALE
REST
UNKNOWN
TRACKING_INSUFFICIENT
PAUSED
COMPLETED
```

Không dùng `COMPLETE/INCOMPLETE` làm phase.

---

# 6. SESSION RESULT VOCABULARY

Dùng:

```text
cycle_completed
cycle_interrupted
tracking_insufficient
session_completed
session_interrupted
```

Không dùng:

```text
breathing_correct
breathing_incorrect
clinically_normal
abnormal_breathing
```

---

# 7. MEDIAPIPE LANDMARKS

MVP dùng MediaPipe Pose.

Tối thiểu:

```text
LEFT_SHOULDER
RIGHT_SHOULDER
```

Có thể thêm:

```text
LEFT_HIP
RIGHT_HIP
NOSE
```

Mục tiêu:
- xác định shoulder line;
- kiểm tra người dùng có ở trong frame;
- chuẩn hóa scale;
- phát hiện chuyển động thân trên quá lớn.

Không suy ra chuyển động cơ hoành trực tiếp từ pose landmarks.

---

# 8. VISIBILITY QUALITY GATE

Mỗi frame phải kiểm tra:

```text
left_shoulder_visibility
right_shoulder_visibility
```

Config:

```json
{
  "min_landmark_visibility": 0.6,
  "min_good_frames_ratio": 0.7
}
```

Không coi các số trên là chuẩn y khoa.
Chúng chỉ là starting defaults và phải configurable.

Nếu visibility thấp:

```text
tracking_quality = POOR
```

Nếu kéo dài:

```text
phase = TRACKING_INSUFFICIENT
```

---

# 9. CAMERA FRAMING CHECK

Yêu cầu người dùng:

```text
ngồi/đứng đối diện camera
vai và phần thân trên nằm rõ trong khung
không quá xa
không quá gần
ánh sáng đủ
```

Không cần full body.

Có thể dùng heuristic:

```text
shoulder_distance_px
shoulder_center
visibility
```

Nếu:

```text
shoulders outside frame
```

→ hiện message:

```text
"Hãy điều chỉnh để hai vai nằm rõ trong khung hình."
```

---

# 10. SIGNAL DEFINITION

Signal cơ bản:

```text
y_left  = normalized y of LEFT_SHOULDER
y_right = normalized y of RIGHT_SHOULDER

shoulder_y = (y_left + y_right) / 2
```

Lưu ý:

MediaPipe image coordinates thường:

```text
y tăng xuống dưới
```

Do đó:

```text
vai nâng lên
→ y giảm
```

Nếu muốn trực quan:

```text
motion_signal = -shoulder_y
```

để:

```text
signal tăng
→ vai nâng lên
```

---

# 11. BODY NORMALIZATION

Không dùng raw pixel trực tiếp.

Normalize scale bằng một trong:

```text
shoulder_width
torso_height
shoulder-to-hip distance
```

Ưu tiên:

```text
torso_scale = distance(mid_shoulder, mid_hip)
```

Nếu hip visibility kém:

```text
fallback shoulder_width
```

Ví dụ:

```text
normalized_signal =
(shoulder_y - baseline_y) / torso_scale
```

---

# 12. BASELINE CALIBRATION

Trước session:

```text
CALIBRATION_WINDOW = 2–5 seconds
```

Lấy:

```text
median shoulder_y
median torso_scale
noise estimate
```

Dùng median, không chỉ mean.

Tạo:

```text
baseline_y
baseline_noise
baseline_scale
```

Nếu calibration có tracking kém:

```text
do not start
```

Message:

```text
"Chưa thấy rõ phần vai. Hãy điều chỉnh vị trí trước khi bắt đầu."
```

---

# 13. FILTERING / SMOOTHING

Không dùng raw signal.

Pipeline:

```text
raw signal
↓
missing-frame handling
↓
outlier rejection
↓
smoothing
```

Có thể dùng:

```text
EMA
moving average
Savitzky-Golay
```

MVP ưu tiên EMA đơn giản.

Config:

```json
{
  "ema_alpha": 0.2
}
```

Không filter quá mạnh gây delay lớn.

---

# 14. OUTLIER HANDLING

Nếu frame jump quá lớn:

```text
abs(signal_t - signal_t-1) > max_jump
```

→ mark outlier.

Không dùng frame đó để trigger phase.

Config:

```json
{
  "max_normalized_jump": 0.08
}
```

Default chỉ là starting point.

---

# 15. MISSING FRAME HANDLING

Nếu mất landmark ngắn:

```text
<= short_gap_frames
```

có thể giữ previous/smooth interpolation nhẹ.

Nếu mất dài:

```text
> long_gap_frames
```

→ `TRACKING_INSUFFICIENT`

Không interpolate gap dài rồi giả dữ liệu.

---

# 16. DERIVATIVE / TREND

Tính:

```text
velocity_t = signal_t - signal_t-k
```

Có smoothing.

Interpretation:

```text
positive trend
→ shoulders rising
negative trend
→ shoulders lowering
```

Nhưng không dùng 1 frame để quyết định phase.

---

# 17. HYSTERESIS

Bắt buộc để tránh phase flipping.

Ví dụ config:

```json
{
  "rise_threshold": 0.01,
  "fall_threshold": -0.01,
  "neutral_threshold": 0.004,
  "min_phase_frames": 5
}
```

Tất cả phải configurable.

---

# 18. STATE MACHINE

State flow:

```text
READY
→ INHALE
→ HOLD(optional)
→ EXHALE
→ REST(optional)
→ READY
```

Cho cycle mới.

Không cho transition tùy ý.

Valid transitions:

```text
READY -> INHALE
INHALE -> HOLD
INHALE -> EXHALE
HOLD -> EXHALE
EXHALE -> REST
EXHALE -> READY
REST -> READY
```

Invalid transition:
```text
EXHALE -> INHALE
```

chỉ được nếu previous cycle đã closed theo configured rule.

---

# 19. TIMER-DRIVEN VS MOTION-DRIVEN

MVP nên dùng:

```text
timer-guided
+
motion-observed
```

Không nên để motion signal hoàn toàn điều khiển instructional phase.

Ví dụ:

```text
Timer says INHALE
Motion signal says rising
→ aligned

Timer says INHALE
Motion signal unclear
→ keep instruction
→ mark low-confidence observation
```

Không đổi prompt user chỉ vì một frame bất thường.

---

# 20. PHASE CONFIDENCE

Có thể tạo:

```text
HIGH
MEDIUM
LOW
UNKNOWN
```

Không hiển thị confidence số giả nếu chưa calibrate.

Ví dụ rule:

```text
HIGH:
good tracking + clear trend

MEDIUM:
good tracking + weak trend

LOW:
weak tracking or unstable signal

UNKNOWN:
insufficient evidence
```

---

# 21. CYCLE COUNT RULE

Một cycle chỉ count khi:

```text
INHALE observed/guided
→ EXHALE observed/guided
→ cycle closure
```

Nếu HOLD được bật:

```text
INHALE
→ HOLD
→ EXHALE
```

Không count tại đầu EXHALE.
Count khi EXHALE hoàn thành.

---

# 22. DUPLICATE COUNT PREVENTION

Bắt buộc:

```text
cycle_id
cycle_state
last_count_timestamp
cooldown
```

Không count lại cùng cycle.

Config:

```json
{
  "min_cycle_seconds": 4,
  "max_cycle_seconds": 20,
  "count_cooldown_seconds": 1.0
}
```

Defaults configurable.

---

# 23. INTERRUPTED CYCLE

Cycle bị interrupted khi:

```text
tracking lost too long
user exits
manual stop
phase timeout
large body movement invalidates observation
```

Result:

```text
cycle_interrupted += 1
```

Không gọi là `incorrect`.

---

# 24. BODY MOTION ARTIFACT DETECTION

Problem:
người dùng nghiêng người/lắc người có thể làm shoulder signal giống breathing.

Dùng heuristic:

```text
left-right shoulder asymmetry
mid-shoulder x displacement
nose x/y displacement
torso translation
```

Nếu body translation lớn:

```text
artifact_detected = true
```

Không trigger breathing phase từ frame đó.

---

# 25. OPTIONAL CHEST ROI MODE

Nếu project muốn tốt hơn mà vẫn không train:

```text
RGB frame
↓
upper chest ROI
↓
optical flow / average motion
↓
combine with shoulder signal
```

Nhưng đây là OPTIONAL PHASE 2.

Không triển khai nếu MVP chưa ổn.

---

# 26. GUIDED UI

UI gồm:

```text
current phase
large breathing circle
countdown
cycle count
tracking quality
pause/stop
```

Ví dụ:

```text
Hít vào
4
3
2
1
```

Sau đó:

```text
Thở ra
6
5
4
3
2
1
```

---

# 27. BREATHING ANIMATION

Animation:

```text
INHALE → circle expands
EXHALE → circle contracts
HOLD → stays
```

Không dùng animation quá nhanh.

Respect:

```text
prefers-reduced-motion
```

---

# 28. AUDIO / VOICE OPTIONAL

Optional:

```text
"Hít vào..."
"Thở ra..."
```

Không bắt buộc.

Nếu thêm:
- có mute;
- không overlap;
- không block session.

---

# 29. SESSION CONFIG

Object:

```json
{
  "exercise": "DEEP_BREATHING",
  "protocol_version": "v1",
  "inhale_seconds": 4,
  "hold_seconds": 0,
  "exhale_seconds": 6,
  "rest_seconds": 0,
  "target_cycles": 6,
  "tracking_mode": "POSE_SHOULDER",
  "guided": true
}
```

---

# 30. SESSION STATE

```json
{
  "session_id": "...",
  "current_phase": "INHALE",
  "cycle_index": 2,
  "completed_cycles": 1,
  "interrupted_cycles": 0,
  "tracking_quality": "GOOD",
  "signal_quality": "MEDIUM",
  "elapsed_seconds": 18.4
}
```

---

# 31. RESULT SCHEMA

```json
{
  "exercise": "DEEP_BREATHING",
  "protocol_version": "v1",
  "target_cycles": 6,
  "completed_cycles": 5,
  "interrupted_cycles": 1,
  "average_cycle_duration": 9.8,
  "tracking_quality": "GOOD",
  "tracking_coverage": 0.94,
  "session_status": "COMPLETED"
}
```

Không lưu:

```text
clinical_correctness
lung_capacity
oxygenation
diagnosis
```

---

# 32. SESSION STATUS

Allowed:

```text
COMPLETED
INTERRUPTED
CANCELLED
TRACKING_INSUFFICIENT
ERROR
```

---

# 33. BACKEND API

Nếu backend đã có session API:
reuse.

Không tạo duplicate architecture.

Ví dụ:

```text
POST /api/sessions
PATCH /api/sessions/{id}
POST /api/sessions/{id}/finish
```

Payload DEEP_BREATHING phải dùng schema riêng nếu cần.

---

# 34. WEBSOCKET

Chỉ dùng nếu current RehabAI exercise flow đã dùng WebSocket.

Event examples:

```json
{
  "type": "BREATH_PHASE",
  "phase": "INHALE",
  "tracking_quality": "GOOD"
}
```

```json
{
  "type": "BREATH_CYCLE_COMPLETED",
  "cycle_index": 3
}
```

Không gửi raw frame qua WebSocket nếu không cần.

---

# 35. FRONTEND / BACKEND RESPONSIBILITY

Frontend:
- camera preview;
- instruction animation;
- countdown;
- local MediaPipe if architecture already supports it;
- local display state.

Backend:
- auth;
- session ownership;
- persistence;
- analytics;
- configuration;
- validated event storage.

Không để Ollama quyết định phase/cycle.

---

# 36. OLLAMA ROLE

Ollama chỉ được:
- giải thích;
- động viên tự nhiên;
- trả lời câu hỏi chung;
- mô tả kết quả đã được engine xác thực.

Không được:
- detect inhale/exhale;
- count cycle;
- override tracking;
- invent cause.

---

# 37. SAFETY MESSAGING

Nếu user báo:

```text
chóng mặt
khó thở bất thường
đau ngực
ngất
triệu chứng đáng lo
```

AI Coach/UI không được tiếp tục thúc bài tập.

Không dùng camera signal để phủ nhận triệu chứng user nói.

---

# 38. ERROR STATES

Phải có:

```text
CAMERA_DENIED
CAMERA_UNAVAILABLE
POSE_NOT_FOUND
TRACKING_POOR
SIGNAL_UNSTABLE
SESSION_SAVE_FAILED
WEBSOCKET_DISCONNECTED
UNKNOWN_ERROR
```

Mỗi error có:
- user message;
- retry action;
- technical log.

---

# 39. FALLBACK MODE

Nếu camera unavailable:

Option product:

```text
GUIDED_TIMER_ONLY
```

Nhưng phải ghi:

```text
tracking unavailable
```

Result:

```text
tracking_quality = UNAVAILABLE
```

Không nói:
```text
cycle observed
```

Chỉ:
```text
guided cycle completed by timer
```

---

# 40. CONFIG FILE

Tạo:

```text
deep_breathing_config.*
```

Không magic numbers trong component.

Config fields:

```text
inhale_seconds
hold_seconds
exhale_seconds
rest_seconds
target_cycles

min_landmark_visibility
min_good_frames_ratio

ema_alpha

rise_threshold
fall_threshold
neutral_threshold

min_phase_frames
short_gap_frames
long_gap_frames

max_normalized_jump

min_cycle_seconds
max_cycle_seconds
count_cooldown_seconds

body_motion_threshold
```

---

# 41. LOGGING

Log:

```text
session_id
phase transition
cycle completed
tracking quality change
camera state
signal quality
error code
```

Không log raw video trừ khi product explicitly requires and user consent exists.

---

# 42. PRIVACY

Default:

```text
do not store raw video
```

Nếu app hiện tại không cần raw video:
- không thêm recording.

Chỉ lưu:
- derived stats;
- phase events;
- cycle counts;
- quality metadata.

---

# 43. PERFORMANCE

Target:
- MediaPipe real-time;
- signal processing lightweight;
- no deep model;
- low CPU overhead.

Đo thực tế:

```text
camera FPS
MediaPipe FPS
signal pipeline latency
phase event latency
CPU
memory
```

Không bịa benchmark.

---

# 44. THREADING / ASYNC

Không để signal processing block UI.

Nếu frontend JS:
- use requestAnimationFrame / worker if needed.

Nếu backend:
- async where appropriate.

Không create unbounded queue.

---

# 45. TEST SUITE — UNIT TESTS

## Signal

- normalize correct;
- EMA correct;
- outlier rejection;
- missing gap;
- derivative sign;
- hysteresis;
- threshold config.

## State Machine

Test all valid transitions.

Test invalid transitions blocked.

## Counting

- one cycle;
- multiple;
- no duplicate;
- interrupted;
- timeout;
- reset.

---

# 46. TEST SUITE — SYNTHETIC SIGNAL

Synthetic signals are allowed for UNIT TEST only.

Create:

```text
clean sinusoid-like breathing
flat signal
noise-only
rising-only
falling-only
signal with gaps
signal with spikes
body-shift artifact
```

Do not use synthetic signal as proof of real-world accuracy.

---

# 47. TEST SUITE — REAL CAMERA

Required:

## RC01 static sitting
Expected:
no fake cycles.

## RC02 guided inhale/exhale
Expected:
reasonable phase alignment.

## RC03 repeated cycles
Expected:
count stable.

## RC04 user moves whole torso
Expected:
artifact / low quality, not false cycle.

## RC05 low light
Expected:
tracking quality degrades.

## RC06 shoulders out of frame
Expected:
tracking insufficient.

## RC07 user leaves frame
Expected:
pause/interruption.

## RC08 camera denied
Expected:
clear error/fallback.

---

# 48. TEST SUITE — TIMER ONLY

If fallback enabled:

## TO01 camera unavailable
→ timer works.

## TO02 result labels tracking unavailable.

## TO03 no false claim of observed breathing.

---

# 49. TEST SUITE — SESSION

- create;
- stop;
- cancel;
- save;
- retry;
- duplicate finish;
- refresh;
- ownership;
- history integration.

---

# 50. TEST SUITE — PUBLIC/PRIVATE BOUNDARY

Unauthenticated:

```text
/exercises/deep-breathing
```

must:
- show info;
- not request camera;
- not start MediaPipe;
- not create session.

Unauthenticated:

```text
/app/exercises/deep-breathing
```

must:
- redirect login.

---

# 51. TEST SUITE — OLLAMA FAILURE

During breathing session:

```text
stop Ollama
```

Expected:
- guided timer continues;
- camera continues;
- MediaPipe continues;
- cycle logic continues;
- AI Coach alone unavailable.

---

# 52. TEST SUITE — EDGE CASES

- user starts mid-inhale;
- holds longer than configured;
- breathes faster;
- breathes slower;
- noisy shoulder movement;
- coughs;
- speaks;
- turns head;
- raises arm;
- adjusts sitting posture;
- camera frame drop;
- tab background;
- mobile orientation change.

System must not overclaim.

---

# 53. ACCEPTANCE CRITERIA

Must pass:

- [ ] no training required;
- [ ] no model checkpoint required;
- [ ] protected route only;
- [ ] camera optional fallback handled;
- [ ] MediaPipe visibility gate;
- [ ] calibration;
- [ ] normalization;
- [ ] smoothing;
- [ ] outlier handling;
- [ ] hysteresis;
- [ ] state machine;
- [ ] cycle count;
- [ ] duplicate prevention;
- [ ] interrupted cycle handling;
- [ ] session persistence;
- [ ] timer-only fallback truthful;
- [ ] no clinical claims;
- [ ] Ollama independence;
- [ ] unit tests;
- [ ] real-camera tests;
- [ ] production build.

---

# 54. FAILURE POLICY

Nếu:
- real camera chưa test;
- thresholds chưa tuned;
- signal quality kém;
- mobile chưa test;

thì:

```text
NOT_TESTED
```

hoặc:

```text
BLOCKED
```

Không nói:
```text
production-ready
```

---

# 55. IMPLEMENTATION ORDER

```text
Phase 0
Audit existing project

Phase 1
Route + UI shell

Phase 2
Camera reuse

Phase 3
MediaPipe shoulder visibility

Phase 4
Calibration + normalization

Phase 5
Signal smoothing

Phase 6
State machine

Phase 7
Guided timer integration

Phase 8
Cycle counting

Phase 9
Session persistence

Phase 10
Fallback mode

Phase 11
Unit tests

Phase 12
Real camera QA

Phase 13
Performance QA

Phase 14
Regression
```

Không làm tất cả một lần.

---

# 56. FILE / MODULE STRUCTURE GỢI Ý

Tùy repo thực tế, có thể:

```text
deep_breathing/
├── config
├── types
├── signal
├── calibration
├── quality
├── state_machine
├── counter
├── session
└── tests
```

Không ép nếu repo có convention khác.

---

# 57. REPORT FORMAT

Sau khi hoàn thành:

```text
AUDIT:
IMPLEMENTED:
REUSED:
NEW_FILES:
CONFIG:
ROUTES:
STATE_MACHINE:
SIGNAL_PIPELINE:
FALLBACK:
TESTS:
REAL_CAMERA_TESTS:
PERFORMANCE:
KNOWN_LIMITATIONS:
NOT_TESTED:
BLOCKED:
NEXT_STEPS:
FINAL_STATUS:
```

---

# 58. FINAL EXECUTION PROMPT

```text
Hãy triển khai DEEP_BREATHING cho RehabAI theo hướng KHÔNG TRAIN MODEL.

Không được thêm deep learning classifier.

Dùng:

Guided Timer
+
MediaPipe Pose
+
Shoulder Motion Signal
+
Normalization
+
Smoothing
+
Hysteresis
+
Rule-Based State Machine
+
Cycle Counter

Bắt đầu bằng audit repo.

Tái sử dụng camera/session/auth hiện có.

Không phá:
- HAND_OPENING
- ELBOW_EXTENSION
- NECK_LATERAL_STRETCH
- auth
- history
- AI Coach
- public/private architecture

PUBLIC WEBSITE không được request camera.

Chỉ authenticated /app mới chạy bài.

Không hard-code threshold rải rác.
Mọi threshold vào config.

Nếu signal không chắc:
→ UNKNOWN / TRACKING_INSUFFICIENT.

Không dùng Complete/Incomplete theo nghĩa y khoa.

Kết quả chỉ nên mô tả:
- completed cycles;
- interrupted cycles;
- cycle duration;
- tracking quality;
- session status.

Ollama không được tham gia detection/counting.

Nếu Ollama down:
bài tập vẫn chạy.

Nếu camera unavailable và timer-only fallback được bật:
- timer vẫn hoạt động;
- tracking phải ghi UNAVAILABLE;
- không được nói camera đã quan sát được chu kỳ.

Bắt buộc viết:
- unit tests;
- synthetic signal tests;
- real camera tests;
- route/auth tests;
- session persistence tests;
- failure tests.

Sau mỗi phase:
- test;
- fix;
- retest.

Không báo PASS nếu chưa test thật.
Không báo production-ready nếu chưa real-camera validation.
```

---

# 59. NGUYÊN TẮC CUỐI

```text
Guidance ≠ diagnosis
Motion signal ≠ clinical breathing measurement
Timer completion ≠ observed breathing completion
Tracking loss ≠ user error
```

Mục tiêu của module này là:

```text
hướng dẫn
+
quan sát chuyển động nhẹ
+
đếm chu kỳ
+
theo dõi session
```

không phải đo chức năng hô hấp lâm sàng.
