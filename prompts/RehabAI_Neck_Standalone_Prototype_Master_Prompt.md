# RehabAI — Standalone Neck Prototype Master Prompt
## `NECK_LATERAL_STRETCH` độc lập hoàn toàn
## Không sửa project chính • Không train model • Có test đầy đủ • Chỉ tích hợp sau khi prototype đạt

> Mục tiêu của prompt này:
>
> Tạo một project prototype hoàn toàn độc lập cho bài:
>
> ```text
> NECK_LATERAL_STRETCH
> ```
>
> Prototype này KHÔNG được sửa bất kỳ file nào trong project RehabAI chính.
>
> Project chính hiện tại:
>
> ```text
> D:\PhucHoiChucNangTay
> ```
>
> phải được coi là:
>
> ```text
> READ-ONLY / DO NOT MODIFY
> ```
>
> Prototype mới phải được tạo ở thư mục riêng, ví dụ:
>
> ```text
> D:\RehabAI_Neck_Prototype
> ```
>
> Nếu prototype không tốt:
>
> ```text
> xóa prototype
> ```
>
> Project chính vẫn nguyên vẹn.
>
> Nếu prototype tốt:
>
> ```text
> validate
> → review
> → chỉ mang engine neck cần thiết sang RehabAI sau
> ```
>
> Không tích hợp vào project chính trong task này.

---

# 0. NGUYÊN TẮC AN TOÀN TỐI CAO

1. Không sửa bất kỳ file nào trong:
   ```text
   D:\PhucHoiChucNangTay
   ```
2. Không copy toàn bộ project 170GB.
3. Không copy dataset.
4. Không copy model weights.
5. Không copy video.
6. Không copy uploads.
7. Không copy `node_modules`.
8. Không copy `.venv` / `venv`.
9. Không sửa database project chính.
10. Không sửa checkpoint/model hiện có.
11. Không train model mới.
12. Không cần Git.
13. Không cần branch.
14. Không cần worktree.
15. Không cần Ollama để prototype hoạt động.
16. Không kết nối backend production.
17. Không ghi dữ liệu vào project chính.
18. Không import code trực tiếp bằng absolute path từ project chính nếu điều đó tạo coupling.
19. Không dùng symlink/junction sang project chính cho các file có khả năng ghi.
20. Nếu cần tham khảo kiến trúc project chính:
    - chỉ đọc;
    - không sửa.
21. Prototype phải có thể chạy độc lập.
22. Prototype phải có tests độc lập.
23. Prototype phải có config riêng.
24. Prototype phải có README riêng.
25. Không báo `PASS` nếu chưa chạy test thật.
26. Nếu camera thật chưa test:
    ```text
    BLOCKED_BY_REAL_CAMERA_VALIDATION
    ```

---

# 1. MỤC TIÊU PROTOTYPE

Prototype chỉ cần chứng minh các chức năng sau:

```text
Camera
↓
MediaPipe Pose
↓
Landmark Quality
↓
Center Calibration
↓
Head Tilt Angle
↓
Shoulder Stability
↓
Optional Torso Stability
↓
Smoothing
↓
Hysteresis
↓
State Machine
↓
Hold Detection
↓
Return To Center
↓
Rep Counting
```

Không cần:

```text
login
register
full dashboard
history production
PostgreSQL production
Ollama
RAG
knowledge crawler
hand model
elbow model
deep-breathing module
full RehabAI UI
```

---

# 2. MỤC TIÊU THÀNH CÔNG

Prototype được coi là có giá trị khi:

```text
1. Camera mở ổn định.
2. MediaPipe nhận được tai + vai.
3. Calibration center ổn định.
4. Phân biệt được nghiêng trái/phải.
5. Không đếm khi người dùng ngồi yên.
6. Không đếm khi mới chạm target.
7. Chỉ đếm khi:
   CENTER
   → MOVING
   → TARGET
   → HOLD_OK
   → RETURNING
   → CENTER.
8. Không đếm trùng.
9. Tracking loss không tạo rep giả.
10. Whole-body tilt được phát hiện hoặc ít nhất không tạo false rep dễ dàng.
11. Có debug overlay để quan sát angle/state.
12. Có metric thực tế từ camera test.
```

---

# 3. TECHNOLOGY STACK

Ưu tiên web prototype đơn giản.

Đề xuất:

```text
Frontend:
Vite + React + TypeScript

Computer Vision:
MediaPipe Tasks Vision
Pose Landmarker

Optional:
Face Landmarker

Testing:
Vitest
React Testing Library
Playwright (nếu phù hợp)
```

Nếu môi trường hiện tại hợp với plain HTML/TypeScript hơn:
- có thể dùng;
- nhưng phải giữ code modular.

Không dựng backend nếu không cần.

---

# 4. PROJECT STRUCTURE

Tạo:

```text
D:\RehabAI_Neck_Prototype
```

Cấu trúc gợi ý:

```text
RehabAI_Neck_Prototype/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── camera/
│   │   ├── CameraController.ts
│   │   └── cameraTypes.ts
│   │
│   ├── mediapipe/
│   │   ├── PoseService.ts
│   │   ├── landmarkTypes.ts
│   │   └── poseUtils.ts
│   │
│   ├── neck/
│   │   ├── config.ts
│   │   ├── types.ts
│   │   ├── geometry.ts
│   │   ├── calibration.ts
│   │   ├── smoothing.ts
│   │   ├── quality.ts
│   │   ├── compensation.ts
│   │   ├── stateMachine.ts
│   │   ├── repCounter.ts
│   │   └── neckEngine.ts
│   │
│   ├── ui/
│   │   ├── CameraPanel.tsx
│   │   ├── CalibrationPanel.tsx
│   │   ├── ExercisePanel.tsx
│   │   ├── DebugPanel.tsx
│   │   └── ResultPanel.tsx
│   │
│   └── styles/
│
├── tests/
│   ├── geometry.test.ts
│   ├── smoothing.test.ts
│   ├── calibration.test.ts
│   ├── stateMachine.test.ts
│   ├── repCounter.test.ts
│   └── compensation.test.ts
│
├── public/
├── reports/
├── README.md
├── package.json
├── tsconfig.json
└── vite.config.ts
```

Nếu toolchain khác:
- giữ tinh thần modular;
- không dồn toàn bộ logic vào một component.

---

# 5. EXERCISE DEFINITION

Exercise ID:

```text
NECK_LATERAL_STRETCH
```

Prototype chỉ đánh giá:

```text
CENTER
LEFT_TILT
RIGHT_TILT
TARGET_REACHED
HOLD
RETURN_CENTER
REP_COUNT
TRACKING_QUALITY
COMPENSATION_FLAG
```

Không đánh giá:

```text
clinical correctness
injury risk
diagnosis
medical ROM
muscle health
```

---

# 6. MEDIAPIPE LANDMARKS

Bắt buộc:

```text
LEFT_EAR
RIGHT_EAR
LEFT_SHOULDER
RIGHT_SHOULDER
```

Khuyến nghị:

```text
NOSE
LEFT_HIP
RIGHT_HIP
```

Optional:

```text
Face Landmarker
```

Face chỉ dùng để:
- sanity check head orientation;
- rotation heuristic.

Không bắt buộc cho phiên bản đầu.

---

# 7. CAMERA SETUP

Yêu cầu UI:

```text
- Start Camera
- Stop Camera
- Camera status
- Permission error
- Framing guide
```

Người dùng:
- ngồi/đứng nhìn tương đối chính diện;
- đầu và hai vai phải thấy rõ;
- ánh sáng đủ.

Không cần full body nếu không dùng hips.

---

# 8. LANDMARK QUALITY GATE

Mỗi frame kiểm tra:

```text
leftEarVisibility
rightEarVisibility
leftShoulderVisibility
rightShoulderVisibility
```

Config starting defaults:

```ts
minLandmarkVisibility = 0.60
minGoodFramesRatio = 0.70
```

Nếu không đủ:

```text
TRACKING_INSUFFICIENT
```

Không dùng stale landmarks.

---

# 9. CENTER CALIBRATION

Có nút:

```text
Calibrate Center
```

Flow:

```text
User nhìn thẳng
→ collect 2–5 seconds
→ reject bad frames
→ median baseline
```

Tính:

```text
baselineHeadAngle
baselineShoulderAngle
baselineTorsoAngle
baselineNoise
```

Effective tilt:

```text
effectiveTilt =
currentRelativeTilt
- baselineHeadAngle
```

Nếu calibration fail:
- không cho Start Exercise;
- hiển thị lý do.

---

# 10. HEAD TILT GEOMETRY

Primary method:

```text
earAngle =
atan2(
  rightEar.y - leftEar.y,
  rightEar.x - leftEar.x
)

shoulderAngle =
atan2(
  rightShoulder.y - leftShoulder.y,
  rightShoulder.x - leftShoulder.x
)

relativeHeadTilt =
normalizeAngle(
  earAngle - shoulderAngle
)
```

Sau calibration:

```text
effectiveTilt =
normalizeAngle(
  relativeHeadTilt - baselineHeadAngle
)
```

---

# 11. ANGLE NORMALIZATION

Viết function riêng:

```text
normalizeAngle(angle)
```

Output nhất quán trong:
```text
[-180°, +180°)
```

Có unit test quanh:
```text
179
180
181
-179
-180
-181
```

---

# 12. LEFT / RIGHT SIGN

Xác định một convention duy nhất.

Ví dụ:

```text
negative = LEFT
positive = RIGHT
```

Bắt buộc test với camera preview mirrored.

CSS/video mirror không được đổi sign tính toán.

---

# 13. FALLBACK METHOD

Nếu ear pair không đủ nhưng có thể tính midpoint ổn:

```text
earMidpoint
shoulderMidpoint

neckVector = earMidpoint - shoulderMidpoint

fallbackAngle = atan2(dx, -dy)
```

Chỉ dùng nếu:
- confidence tốt;
- đã test.

Nếu không:
```text
TRACKING_INSUFFICIENT
```

---

# 14. SHOULDER COMPENSATION

Theo dõi:

```text
shoulderAngleDelta
shoulderMidpointXDelta
shoulderMidpointYDelta
```

Normalize translation bằng:
```text
shoulderWidth
```

Nếu vượt threshold:

```text
COMPENSATION_DETECTED
```

Không count frame đó.

UI:

```text
"Hãy thử giữ hai vai tương đối ổn định."
```

---

# 15. TORSO COMPENSATION

Nếu hip visibility đủ:

```text
midShoulder
midHip
torsoVector
torsoTilt
```

So với baseline.

Nếu torso tilt quá lớn:
```text
COMPENSATION_DETECTED
```

---

# 16. OPTIONAL ROTATION HEURISTIC

Nếu Face Landmarker được bật:

```text
head rotation
vs
lateral tilt
```

Nếu nghi người dùng quay đầu:

```text
ROTATION_SUSPECTED
```

Phiên bản đầu chỉ nên:
- debug/flag;
- không hard reject trừ khi test đủ.

---

# 17. SMOOTHING

Không dùng raw angle trực tiếp.

EMA:

```text
smoothed =
alpha * current
+ (1-alpha) * previous
```

Config:

```ts
angleEmaAlpha = 0.25
```

Optional:
```text
moving median
→ EMA
```

---

# 18. OUTLIER FILTER

Nếu:

```text
abs(angle_t - angle_t_minus_1)
> maxAngleJumpDeg
```

thì:
```text
OUTLIER
```

Không trigger state.

Starting config:

```ts
maxAngleJumpDeg = 12
```

---

# 19. MISSING LANDMARK POLICY

Short gap:

```text
<= 3 frames
```

→ giữ state ngắn.

Long gap:

```text
> 10 frames
```

→

```text
TRACKING_INSUFFICIENT
```

Không nội suy gap dài.

---

# 20. CONFIG FILE

Tạo config tập trung:

```ts
export const neckConfig = {
  centerEnterDeg: 6,
  centerExitDeg: 8,

  targetEnterDeg: 15,
  targetExitDeg: 13,
  targetMaxDeg: 30,

  returnToleranceDeg: 7,

  holdSeconds: 3.0,
  minPhaseMs: 250,
  repCooldownMs: 800,

  minLandmarkVisibility: 0.60,
  minGoodFramesRatio: 0.70,

  maxShoulderTiltDeg: 8,
  maxTorsoTiltDeg: 8,
  maxNormalizedShoulderShift: 0.12,

  angleEmaAlpha: 0.25,
  maxAngleJumpDeg: 12,

  shortGapFrames: 3,
  longGapFrames: 10,

  maxMovingSeconds: 8,
  maxHoldSeconds: 10,
  maxReturnSeconds: 8
}
```

Đây chỉ là starting defaults để test.

---

# 21. STATE MACHINE

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
ERROR
```

---

# 22. LEFT FLOW

```text
CENTER
→ MOVING_LEFT
→ TARGET_LEFT
→ HOLD_LEFT
→ RETURNING_FROM_LEFT
→ CENTER
→ leftRep + 1
```

---

# 23. RIGHT FLOW

```text
CENTER
→ MOVING_RIGHT
→ TARGET_RIGHT
→ HOLD_RIGHT
→ RETURNING_FROM_RIGHT
→ CENTER
→ rightRep + 1
```

---

# 24. HYSTERESIS

Không dùng cùng threshold cho enter/exit.

Ví dụ:

```text
CENTER enter <= 6°
CENTER exit  > 8°

TARGET enter >= 15°
TARGET exit  < 13°
```

Mục tiêu:
- chống jitter;
- chống state flipping;
- chống double count.

---

# 25. HOLD VALIDATION

Khi vào target:

```text
start hold timer
```

Nếu user ở target đủ:

```text
holdSeconds
```

→ `HOLD_OK`.

Nếu rời target quá lâu:
- reset hold;
- quay lại MOVING/TARGET.

---

# 26. RETURN VALIDATION

Sau HOLD_OK:

```text
angle magnitude decreases
toward center
```

→ `RETURNING`.

Rep chỉ count khi:

```text
abs(angle)
<= returnToleranceDeg
```

và center ổn định.

---

# 27. REP COUNT

Một rep hợp lệ:

```text
CENTER
→ MOVING
→ TARGET
→ HOLD_OK
→ RETURNING
→ CENTER
```

Không count:
- target only;
- hold only;
- return missing;
- tracking poor;
- compensation excessive;
- jitter.

---

# 28. DUPLICATE PREVENTION

Dùng:

```text
repId
lastRepTimestamp
cooldown
state lock
center reset requirement
```

Một motion không được tạo 2 rep.

---

# 29. SESSION STATS

Prototype lưu local memory hoặc local JSON export.

Ví dụ:

```json
{
  "exercise": "NECK_LATERAL_STRETCH",
  "engine": "RULE_BASED_GEOMETRY",
  "left_reps": 3,
  "right_reps": 3,
  "total_reps": 6,
  "interrupted_reps": 1,
  "tracking_quality": "GOOD",
  "tracking_coverage": 0.94,
  "average_hold_seconds": 3.1
}
```

Không cần database production.

---

# 30. DEBUG OVERLAY — BẮT BUỘC

Hiển thị developer overlay:

```text
raw angle
smoothed angle
baseline
shoulder angle
torso angle
visibility
tracking quality
current state
hold timer
left reps
right reps
compensation
```

Có toggle:

```text
Debug ON/OFF
```

---

# 31. VISUAL FEEDBACK

UI nên hiển thị:

```text
CENTER
MOVE LEFT
MOVE RIGHT
TARGET REACHED
HOLD
RETURN TO CENTER
TRACKING LOST
KEEP SHOULDERS STABLE
```

Dùng text + visual.

Không dựa chỉ vào màu.

---

# 32. PROTOTYPE UI

Tạo một trang duy nhất gồm:

```text
Title
Camera Panel
Tracking Status
Calibration Button
Start/Pause/Stop
Current State
Angle Meter
Target Zone
Hold Timer
Rep Counter
Debug Toggle
Session Result
```

Không cần làm full RehabAI design.

Nhưng UI phải:
- rõ;
- responsive;
- dễ debug.

---

# 33. PRIVACY

Prototype mặc định:

```text
DO NOT RECORD VIDEO
DO NOT SAVE RAW FRAMES
```

Không upload camera data.

Mọi xử lý local trong browser nếu stack cho phép.

---

# 34. ERROR STATES

```text
CAMERA_DENIED
CAMERA_UNAVAILABLE
POSE_MODEL_LOAD_FAILED
POSE_NOT_FOUND
EAR_NOT_VISIBLE
SHOULDERS_NOT_VISIBLE
TRACKING_POOR
CALIBRATION_FAILED
COMPENSATION_EXCESSIVE
UNKNOWN_ERROR
```

Mỗi error:
- message;
- retry action;
- debug log.

---

# 35. UNIT TEST — GEOMETRY

Bắt buộc:

```text
G01 center = near 0
G02 left tilt sign
G03 right tilt sign
G04 shoulder-relative correction
G05 camera tilt compensation
G06 angle normalization
G07 mirrored preview safety
G08 fallback geometry
```

---

# 36. UNIT TEST — SMOOTHING

```text
SM01 constant signal
SM02 noisy signal
SM03 step response
SM04 outlier spike
SM05 missing short gap
SM06 long gap
```

---

# 37. UNIT TEST — STATE MACHINE

```text
ST01 valid left flow
ST02 valid right flow
ST03 CENTER→HOLD invalid
ST04 TARGET without hold
ST05 HOLD without return
ST06 tracking lost mid-rep
ST07 compensation
ST08 timeout
ST09 cooldown
ST10 reset
```

---

# 38. UNIT TEST — REP COUNT

```text
RC01 one left = 1
RC02 one right = 1
RC03 six alternating = 6
RC04 partial = 0
RC05 target no hold = 0
RC06 hold no return = 0
RC07 jitter = no duplicate
RC08 tracking loss = no fake rep
RC09 compensation = no rep
RC10 restart resets correctly
```

---

# 39. SYNTHETIC TEST SEQUENCES

Chỉ dùng cho unit testing:

```text
clean left
clean right
partial tilt
slow rep
fast rep
noise near center
noise near target
outlier jump
missing frames
whole-body tilt
camera baseline offset
```

Không dùng synthetic test để claim real-world accuracy.

---

# 40. REAL CAMERA TESTS — BẮT BUỘC

```text
CAM01 ngồi yên → 0 rep

CAM02 nghiêng trái đủ + hold + return
→ 1 left

CAM03 nghiêng phải đủ + hold + return
→ 1 right

CAM04 6 alternating
→ 6 total

CAM05 chưa đạt target
→ 0

CAM06 đạt target nhưng hold thiếu
→ 0

CAM07 hold đủ nhưng không return
→ 0

CAM08 nghiêng cả thân
→ compensation / no false rep

CAM09 che tai
→ tracking warning

CAM10 ánh sáng yếu
→ tracking degrades gracefully

CAM11 camera hơi lệch
→ calibration reduces bias

CAM12 ra khỏi frame
→ tracking insufficient

CAM13 quay lại frame
→ recover safely

CAM14 nhanh/chậm khác nhau
→ no duplicate
```

---

# 41. METRICS

Đo:

```text
Rep Count MAE
Exact Count Accuracy
False Positive Reps
False Negative Reps
Tracking Failure Rate
Average Rep Detection Delay
```

Không ghi:
```text
100% accurate
production-ready
clinically valid
```

nếu chưa có dữ liệu thực nghiệm.

---

# 42. MANUAL VALIDATION SHEET

Tạo:

```text
reports/manual_camera_validation.csv
```

Columns:

```text
test_id
subject_id
lighting
camera_position
expected_left
expected_right
observed_left
observed_right
false_positive
false_negative
tracking_failures
notes
```

---

# 43. README

README phải có:

```text
What this prototype is
What it is NOT
Installation
Run commands
Camera requirements
Calibration instructions
State machine
Config
Test commands
Known limitations
How to manually validate
How to delete prototype safely
```

---

# 44. DO NOT INTEGRATE INTO MAIN PROJECT

Trong task này tuyệt đối không:

```text
copy module into D:\PhucHoiChucNangTay
edit main project routes
edit main package.json
edit main backend
edit main DB
edit main models
```

Task kết thúc ở prototype.

---

# 45. INTEGRATION PACKAGE — CHỈ CHUẨN BỊ

Nếu prototype đạt, chỉ chuẩn bị thư mục:

```text
integration_candidate/
```

chứa:

```text
neck engine source
config
types
unit tests
integration notes
API/interface contract
```

Không tự copy sang project chính.

---

# 46. INTEGRATION NOTES

Tạo:

```text
reports/integration_plan.md
```

Nội dung:

```text
What files would be portable
What dependencies are required
What interfaces RehabAI needs
What shared code should NOT be changed
How to add feature flag
How to add protected route
How to add session adapter
Regression tests required
Rollback plan
```

---

# 47. FAILURE POLICY

Nếu prototype không đạt:

```text
FINAL_STATUS = PROTOTYPE_NOT_READY
```

Không sửa project chính.

Không cố “cứ tích hợp rồi tính sau”.

---

# 48. SUCCESS POLICY

Nếu:

```text
unit tests PASS
real camera tests PASS
false positives acceptable
false negatives acceptable
tracking stable
cleanup works
```

thì:

```text
FINAL_STATUS = READY_FOR_INTEGRATION_REVIEW
```

Không có nghĩa là tự động tích hợp.

---

# 49. TEST STATUS

Chỉ dùng:

```text
PASS
FAIL
BLOCKED
NOT_TESTED
```

Không dùng:

```text
looks good
probably works
should be fine
```

---

# 50. FINAL REPORT

Tạo:

```text
reports/final_report.md
```

Format:

```text
PROTOTYPE_PATH:

PROJECT_MAIN_TOUCHED:
MUST_BE NO

STACK:

MEDIAPIPE:

FACE_LANDMARKER:
ENABLED / DISABLED

IMPLEMENTED:

CALIBRATION:

GEOMETRY:

SMOOTHING:

HYSTERESIS:

STATE_MACHINE:

COMPENSATION:

REP_COUNTING:

UNIT_TESTS:

REAL_CAMERA_TESTS:

METRICS:

FAILURES:

BLOCKED:

KNOWN_LIMITATIONS:

INTEGRATION_CANDIDATE_CREATED:
YES / NO

MAIN_PROJECT_FILES_MODIFIED:
MUST_BE NONE

FINAL_STATUS:
PROTOTYPE_NOT_READY
or
READY_FOR_INTEGRATION_REVIEW
```

---

# 51. FINAL EXECUTION INSTRUCTION

```text
Tạo một project mới hoàn toàn độc lập tại:

D:\RehabAI_Neck_Prototype

Tuyệt đối không sửa:

D:\PhucHoiChucNangTay

Project chính phải được coi là READ-ONLY.

Không cần Git.
Không cần branch.
Không train model.
Không dùng dataset.
Không copy project 170GB.

Prototype chỉ tập trung vào:
NECK_LATERAL_STRETCH.

Dùng:
MediaPipe Pose
+ optional Face Landmarker
+ Center Calibration
+ Head Tilt Relative to Shoulder Line
+ Shoulder/Torso Compensation
+ Smoothing
+ Hysteresis
+ Rule-Based State Machine
+ Hold Validation
+ Return-To-Center
+ Rep Counting.

Rep chỉ được tính khi:

CENTER
→ MOVING
→ TARGET
→ HOLD_OK
→ RETURNING
→ CENTER.

Không count khi chỉ chạm target.

Không dùng magic numbers rải rác.
Mọi threshold vào config.

Bắt buộc tạo:
- modular source;
- debug overlay;
- unit tests;
- synthetic signal tests;
- real camera checklist;
- manual validation CSV;
- README;
- final report;
- integration plan.

Không ghi raw video.
Không upload camera.

Không kết nối DB production.
Không sửa auth production.
Không sửa model hiện có.
Không tích hợp vào RehabAI trong task này.

Nếu real-camera chưa test:
→ BLOCKED_BY_REAL_CAMERA_VALIDATION.

Nếu prototype chưa ổn:
→ PROTOTYPE_NOT_READY.

Nếu prototype đạt test:
→ READY_FOR_INTEGRATION_REVIEW.

Cuối task phải xác nhận:

MAIN_PROJECT_FILES_MODIFIED = NONE.
```

---

# 52. NGUYÊN TẮC CUỐI

```text
Prototype độc lập
= nơi được phép thử nghiệm.
```

```text
Project RehabAI chính
= tuyệt đối không được đụng trong giai đoạn này.
```

```text
Chỉ sau khi prototype được validate
mới lập kế hoạch tích hợp.
```
