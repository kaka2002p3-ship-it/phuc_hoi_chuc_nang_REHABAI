# RehabAI — SAFE EXPERIMENTAL BRANCH MASTER PROMPT
## NECK_LATERAL_STRETCH — Không train model • Cô lập tuyệt đối • Không phá dự án hiện tại

> Mục tiêu của prompt này là cho AI coding agent triển khai thử nghiệm bài
> `NECK_LATERAL_STRETCH` trên **một Git branch riêng**, với nguyên tắc:
>
> ```text
> main / nhánh ổn định hiện tại
> = KHÔNG bị sửa trực tiếp
>
> experimental neck branch
> = nơi duy nhất được phép triển khai thử nghiệm
> ```
>
> Nếu thử nghiệm tốt:
>
> ```text
> giữ branch
> → review
> → test đầy đủ
> → chỉ merge khi người dùng quyết định
> ```
>
> Nếu thử nghiệm không tốt:
>
> ```text
> quay lại nhánh ổn định
> → project hiện tại vẫn nguyên vẹn
> ```
>
> **KHÔNG tự động merge.**
> **KHÔNG tự động xóa branch.**
> **KHÔNG dùng lệnh Git phá hủy dữ liệu.**

---

# 0. NGUYÊN TẮC AN TOÀN TỐI CAO

Đây là các rule bắt buộc, ưu tiên cao hơn mọi yêu cầu triển khai khác.

## 0.1 Không làm việc trực tiếp trên nhánh ổn định

Trước khi sửa bất kỳ file nào:

1. xác định branch hiện tại;
2. xác định branch ổn định của project (`main`, `master`, `develop`, hoặc branch khác);
3. không giả định branch ổn định luôn là `main`;
4. kiểm tra working tree;
5. chỉ tạo branch thử nghiệm khi trạng thái Git đủ an toàn.

Tên branch đề xuất:

```text
feature/neck-lateral-stretch-rulebased
```

Nếu branch đã tồn tại:
- không overwrite;
- không force reset;
- báo trạng thái;
- tiếp tục branch đó chỉ khi hợp lý.

---

## 0.2 Không được dùng các lệnh phá hủy

TUYỆT ĐỐI KHÔNG tự chạy:

```bash
git reset --hard
git clean -fd
git clean -fdx
git checkout -- .
git restore .
git restore --staged .
git branch -D ...
git push --force
git push --force-with-lease
rm -rf
del /s /q
format
```

Nếu một thao tác cleanup/destructive thực sự cần thiết:

```text
STOP
→ báo cho người dùng
→ giải thích rủi ro
→ chờ xác nhận thủ công
```

---

## 0.3 Không tự xóa branch nếu thử nghiệm thất bại

Nếu neck experiment không đạt:

```text
DO NOT DELETE BRANCH AUTOMATICALLY
```

Chỉ:
- ghi FAIL/BLOCKED;
- hướng dẫn user quay lại stable branch;
- giữ branch để audit hoặc xóa thủ công sau.

---

## 0.4 Không tự merge

AI coding agent không được tự merge vào stable branch.

Kết thúc chỉ được báo:

```text
READY_FOR_REVIEW
```

hoặc:

```text
NOT_READY_FOR_MERGE
```

User quyết định merge.

---

## 0.5 Không chạm dữ liệu lớn

Project hiện tại có thể rất lớn (~170GB).

Không:
- copy toàn repo vô tội vạ;
- duplicate dataset;
- duplicate model weights;
- duplicate video;
- duplicate uploads;
- duplicate caches;
- tạo archive toàn bộ project.

Không tạo worktree nếu chưa kiểm tra kích thước tracked files.

---

# 1. PREFLIGHT GIT AUDIT — BẮT BUỘC

Trước mọi code change, chạy và ghi lại:

```text
git status
git branch --show-current
git rev-parse --show-toplevel
git log -1 --oneline
git remote -v
```

Sau đó tạo report:

```text
reports/neck_experiment/git_preflight.md
```

Nội dung:

```text
REPO_ROOT:
CURRENT_BRANCH:
STABLE_BRANCH_CANDIDATE:
HEAD_COMMIT:
WORKING_TREE_STATUS:
UNTRACKED_FILES_PRESENT:
UNCOMMITTED_CHANGES_PRESENT:
REMOTE:
SAFE_TO_CREATE_EXPERIMENT_BRANCH:
```

---

# 2. XỬ LÝ WORKING TREE KHÔNG SẠCH

Nếu có file đang modified/untracked:

```text
DO NOT DISCARD THEM
DO NOT STASH AUTOMATICALLY
DO NOT COMMIT THEM AUTOMATICALLY
```

Hãy:

1. liệt kê file;
2. phân loại:
   - source;
   - config;
   - dataset;
   - generated;
   - unknown;
3. nếu các thay đổi đó không phải của task neck:
   - `BLOCKED_BY_DIRTY_WORKTREE`
4. đề xuất user commit/stash thủ công.

Không tự quyết định xử lý thay user.

---

# 3. SAFETY CHECKPOINT

Nếu working tree sạch:

Ghi commit hiện tại:

```text
BASELINE_COMMIT=<hash>
```

Có thể tạo lightweight safety tag CHỈ nếu project convention cho phép và không ảnh hưởng workflow:

```text
pre-neck-experiment-YYYYMMDD
```

Nhưng:
- không bắt buộc;
- không push tag tự động;
- không overwrite existing tag.

Nếu không cần tag:
- chỉ lưu `BASELINE_COMMIT` trong report.

---

# 4. TẠO EXPERIMENT BRANCH

Chỉ sau preflight PASS.

Pseudo workflow:

```bash
git switch <stable-branch>
git switch -c feature/neck-lateral-stretch-rulebased
```

Hoặc tương đương phù hợp với Git version.

Sau khi tạo branch:

```text
verify current branch
verify HEAD == BASELINE_COMMIT
```

Nếu không đúng:
```text
STOP
```

---

# 5. WORKTREE — OPTIONAL, KHÔNG MẶC ĐỊNH

Không tự tạo worktree ngay.

Trước tiên phải kiểm tra:

```text
git ls-files
tracked file sizes
Git LFS usage
large tracked directories
```

Nếu repo track dataset/model/video lớn:
- KHÔNG tạo worktree nếu có nguy cơ duplicate working files quá lớn.

Chỉ dùng worktree nếu:
- source tree nhẹ;
- large data nằm ngoài Git hoặc dùng external storage phù hợp;
- đủ disk space;
- user muốn workspace song song.

Nếu không chắc:
```text
BRANCH_ONLY_MODE
```

Đây là mặc định an toàn.

---

# 6. FEATURE FLAG — BẮT BUỘC

Bài cổ phải được đặt sau feature flag.

Ví dụ:

```text
NECK_LATERAL_STRETCH_ENABLED=false
```

hoặc cơ chế feature flag hiện có của project.

Default phải là:

```text
false
```

cho đến khi neck test đủ.

Không bật production mặc định.

---

# 7. PHẠM VI BÀI CỔ

Exercise:

```text
NECK_LATERAL_STRETCH
```

Không train model mới.

Engine:

```text
RULE_BASED_GEOMETRY
```

Dùng:

```text
MediaPipe Pose
+
optional MediaPipe Face Landmarker
+
Per-User Calibration
+
Head Tilt Geometry
+
Shoulder/Torso Stability
+
Smoothing
+
Hysteresis
+
State Machine
+
Hold Validation
+
Return-to-Center
+
Rep Counting
```

---

# 8. MODEL ISOLATION — BẮT BUỘC

Không được sửa:

```text
HAND_OPENING model/checkpoint
ELBOW_EXTENSION model/checkpoint
DEEP_BREATHING engine
```

Không được thay đổi:

```text
hand preprocessing
elbow preprocessing
existing checkpoint paths
existing model weights
existing trained feature dimensions
existing normalization
```

Nếu một file model/checkpoint thay đổi:

```text
STOP
FINAL_STATUS = BLOCKED_MODEL_FILE_CHANGED
```

---

# 9. TẠO MODULE RIÊNG

Theo convention thật của repo, tạo module riêng, ví dụ:

```text
neck_lateral_stretch/
├── config
├── types
├── landmarks
├── calibration
├── geometry
├── smoothing
├── quality
├── compensation
├── state_machine
├── counter
├── session_adapter
├── debug
└── tests
```

Không nhét neck logic vào:

```text
hand model
elbow model
breathing engine
generic model class
```

nếu không thật sự bắt buộc.

---

# 10. SHARED CODE POLICY

Ưu tiên:

```text
new isolated module
> modify shared code
```

Nếu buộc phải sửa shared component:

1. ghi file;
2. ghi lý do;
3. ghi phạm vi ảnh hưởng;
4. thêm regression test;
5. giữ backward compatibility.

Report:

```text
SHARED_FILES_CHANGED:
WHY:
RISK:
REGRESSION_TESTS_ADDED:
```

---

# 11. ROUTE SAFETY

Public:

```text
/exercises/neck-lateral-stretch
```

chỉ informational.

Không:
- camera;
- MediaPipe;
- state machine;
- rep count;
- session.

Protected:

```text
/app/exercises/neck-lateral-stretch
```

hoặc route convention hiện có.

Nếu unauthenticated:
```text
redirect → login
```

---

# 12. CAMERA / MEDIAPIPE SAFETY

Không tạo camera pipeline thứ hai nếu project đã có shared camera abstraction ổn định.

Reuse adapter/interface nếu có.

Neck code chỉ được active khi:

```text
exercise == NECK_LATERAL_STRETCH
AND feature flag == enabled
AND user authenticated
```

Khi rời neck route:

```text
stop listeners
clear timers
dispose observers
stop worker if neck-specific
reset state machine
release neck subscriptions
```

Không được để neck pipeline chạy nền.

---

# 13. LANDMARKS

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

Face Landmarker optional.

---

# 14. CALIBRATION

Center calibration 2–5 giây.

Tính median:

```text
baseline_head_angle
baseline_shoulder_angle
baseline_torso_angle
baseline_noise
```

Effective angle:

```text
relative_angle =
current_relative_angle - baseline_head_angle
```

Không start nếu calibration quality thấp.

---

# 15. GEOMETRY

Ear line:

```text
ear_angle =
atan2(
  right_ear_y - left_ear_y,
  right_ear_x - left_ear_x
)
```

Shoulder line:

```text
shoulder_angle =
atan2(
  right_shoulder_y - left_shoulder_y,
  right_shoulder_x - left_shoulder_x
)
```

Relative head tilt:

```text
head_tilt =
normalize_angle(
  ear_angle - shoulder_angle
)
```

Sau baseline:

```text
effective_tilt =
normalize_angle(
  head_tilt - baseline_head_angle
)
```

---

# 16. COMPENSATION

Theo dõi:

```text
shoulder angle change
shoulder midpoint displacement
torso angle change
```

Nếu vượt config:

```text
COMPENSATION_DETECTED
```

Không count frame đó.

Không gọi là diagnosis.

---

# 17. SMOOTHING + HYSTERESIS

Không dùng raw angle trực tiếp.

Dùng EMA hoặc filter nhẹ.

Ví dụ config ban đầu:

```json
{
  "angle_ema_alpha": 0.25,
  "max_angle_jump_deg": 12,

  "center_tolerance_deg": 6,
  "center_exit_deg": 8,

  "target_enter_deg": 15,
  "target_exit_deg": 13,

  "target_max_deg": 30,

  "hold_seconds": 3.0,
  "rep_cooldown_ms": 800
}
```

Các số này:
- chỉ starting defaults;
- không phải chuẩn y khoa;
- phải nằm trong neck config riêng.

---

# 18. STATE MACHINE

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

Left:

```text
CENTER
→ MOVING_LEFT
→ TARGET_LEFT
→ HOLD_LEFT
→ RETURNING_FROM_LEFT
→ CENTER
→ +1 left rep
```

Right tương tự.

---

# 19. REP COUNT RULE

Rep chỉ count khi đủ:

```text
CENTER
→ MOVING
→ TARGET
→ HOLD_OK
→ RETURNING
→ CENTER
```

Không count khi:
- vừa chạm target;
- chỉ hold;
- chưa return;
- tracking mất;
- compensation vượt ngưỡng;
- jitter quanh threshold.

---

# 20. SESSION RESULT

Ví dụ:

```json
{
  "exercise": "NECK_LATERAL_STRETCH",
  "engine_type": "RULE_BASED_GEOMETRY",
  "algorithm_version": "neck_rule_v1",
  "config_version": "v1",

  "left_reps": 3,
  "right_reps": 3,
  "total_reps": 6,
  "interrupted_reps": 1,

  "tracking_quality": "GOOD",
  "tracking_coverage": 0.94,

  "session_status": "COMPLETED"
}
```

Không thêm:
- diagnosis;
- injury score;
- clinical ROM;
- medical correctness.

---

# 21. BASELINE TESTS TRƯỚC KHI CODE

Trước neck implementation:

```text
HAND_OPENING baseline
ELBOW_EXTENSION baseline
DEEP_BREATHING baseline
AUTH baseline
SESSION/HISTORY baseline
BUILD baseline
```

Lưu:

```text
reports/neck_experiment/baseline_before.md
```

Nếu test chưa tồn tại:
- không invent PASS;
- ghi `NOT_TESTED`.

---

# 22. NECK UNIT TESTS

Geometry:

```text
G01 center
G02 left tilt
G03 right tilt
G04 relative shoulder correction
G05 camera tilt compensation
G06 mirror safety
G07 angle normalization
```

Filtering:

```text
F01 EMA
F02 jitter
F03 outlier
F04 short landmark gap
F05 long landmark gap
```

State:

```text
S01 valid left
S02 valid right
S03 target without hold
S04 hold without return
S05 invalid transition
S06 tracking loss
S07 compensation
S08 timeout
S09 cooldown
S10 reset
```

Counting:

```text
C01 left = 1
C02 right = 1
C03 six alternating = 6
C04 partial = 0
C05 jitter no duplicate
C06 tracking loss no fake rep
```

---

# 23. REAL CAMERA TESTS

Bắt buộc trước khi gọi stable:

```text
R01 sit still → 0
R02 one left → 1
R03 one right → 1
R04 six alternating → expected
R05 partial → 0
R06 target no hold → 0
R07 hold no return → 0
R08 whole-body tilt → compensation/no false rep
R09 ear occlusion → tracking warning
R10 low light → degraded quality
R11 camera slight tilt → calibration handles bias
R12 leave frame → interrupted
R13 reopen session → clean state
```

Nếu chưa có camera thật:
```text
BLOCKED_BY_REAL_CAMERA_VALIDATION
```

---

# 24. REGRESSION TEST — HAND_OPENING

Sau neck:

```text
same checkpoint path
same preprocessing
same known fixture result
same rep-count behavior
no neck config import
no neck worker/timer active
```

Nếu baseline fixture tồn tại:
- compare before/after.

---

# 25. REGRESSION TEST — ELBOW_EXTENSION

```text
same checkpoint
same preprocessing
same fixture result
same rep behavior
no neck thresholds leak
```

---

# 26. REGRESSION TEST — DEEP_BREATHING

```text
same breathing config
same state machine
same cycle behavior
no neck compensation logic
same Ollama-independent behavior
```

---

# 27. AUTH / ROUTE REGRESSION

Verify:

```text
public pages still public
public exercise pages still informational
/app remains protected
hand route works
elbow route works
breathing route works
neck route protected
login redirect unchanged
```

---

# 28. SESSION / HISTORY REGRESSION

Verify:

```text
hand session save
elbow session save
breathing session save
neck session save

history old entries unchanged
neck entries render separately
progress aggregation unchanged for old data
no cross-exercise corruption
```

---

# 29. RUNTIME ISOLATION TEST

Khi đang ở HAND:

```text
no neck state machine
no neck timers
no neck worker
no neck subscriptions
```

Tương tự:
```text
ELBOW
DEEP_BREATHING
```

Neck chỉ chạy khi:
```text
NECK route + feature enabled
```

---

# 30. CONFIG ISOLATION TEST

Thay:

```text
neck.target_enter_deg
```

Expected:

```text
HAND output unchanged
ELBOW output unchanged
BREATHING output unchanged
```

---

# 31. RESOURCE CLEANUP TEST

Sau khi rời neck:

```text
timers = cleared
subscriptions = disposed
workers = stopped
neck state = reset
```

Sau đó mở HAND/ELBOW/BREATHING.

Không:
- duplicate camera stream;
- stale state;
- extra CPU loop.

---

# 32. DATABASE / MIGRATION SAFETY

Nếu cần schema change:

Ưu tiên:
```text
additive migration
```

Không:
```text
DROP
TRUNCATE
destructive rename
rewrite historical rows
```

Migration phải:
- fresh DB test;
- existing DB upgrade test;
- preserve existing sessions.

Nếu destructive migration được phát hiện:

```text
STOP
BLOCKED_BY_DESTRUCTIVE_MIGRATION
```

---

# 33. NO DATASET / MODEL SIDE EFFECTS

Không ghi vào:

```text
datasets/
models/
checkpoints/
training_runs/
```

Không chạy training command.

Không tải model lớn nếu không cần.

---

# 34. BUILD / QUALITY GATE

Chạy command thật của repo:

```text
lint
typecheck
unit tests
integration tests
backend tests
production build
```

Không invent command.

Nếu thiếu command:
```text
NOT_TESTED
```

---

# 35. PERFORMANCE REGRESSION

Đo trước/sau nếu có thể:

```text
camera FPS
MediaPipe FPS
memory
CPU
startup latency
```

Đặc biệt verify:
```text
neck code adds ~0 runtime cost when neck route inactive
```

Không bịa số.

---

# 36. GIT DIFF AUDIT

Trước khi kết thúc:

```text
git status
git diff --stat <BASELINE_COMMIT>..HEAD
git diff --name-only <BASELINE_COMMIT>..HEAD
```

Phân loại:

```text
NECK_ONLY_FILES:
SHARED_FILES:
MODEL_FILES:
DATA_FILES:
MIGRATION_FILES:
```

Expected:

```text
MODEL_FILES = NONE
DATA_FILES = NONE
```

Nếu có:
```text
BLOCKED
```

trừ file fixture nhỏ được tạo rõ ràng cho tests.

---

# 37. COMMIT STRATEGY

Commit nhỏ, rõ:

```text
chore: add neck experiment scaffolding
feat: add neck geometry engine
feat: add neck state machine
test: add neck unit tests
test: add cross-exercise regression tests
```

Không squash/force rewrite history tự động.

---

# 38. KHÔNG PUSH TỰ ĐỘNG NẾU USER KHÔNG YÊU CẦU

Mặc định:
```text
local branch only
```

Không tự:
```text
git push
```

Nếu push được yêu cầu:
- push experimental branch thôi;
- không push stable branch;
- không force push.

---

# 39. MERGE GATE

Branch chỉ được đánh dấu:

```text
READY_FOR_REVIEW
```

nếu:

```text
NECK unit tests PASS
NECK integration PASS
NECK real-camera PASS
HAND regression PASS
ELBOW regression PASS
BREATHING regression PASS
AUTH PASS
SESSION/HISTORY PASS
BUILD PASS
MODEL_FILES unchanged
NO destructive migration
```

AI không tự merge.

---

# 40. FAIL PATH

Nếu thử nghiệm neck không ổn:

```text
FINAL_STATUS = NOT_READY_FOR_MERGE
```

Hướng dẫn:

```text
git switch <stable-branch>
```

Không cần xóa branch.

Stable project phải tiếp tục dùng bình thường.

---

# 41. OPTIONAL FEATURE FLAG RELEASE

Ngay cả sau khi merge về sau, feature flag có thể vẫn:

```text
false
```

và bật theo:
- dev;
- QA;
- selected users;
- production after validation.

---

# 42. FINAL REPORT

Tạo:

```text
reports/neck_experiment/final_report.md
```

Format:

```text
GIT_PREFLIGHT:

BASELINE_COMMIT:

EXPERIMENT_BRANCH:

WORKTREE_MODE:
BRANCH_ONLY / WORKTREE

FEATURE_FLAG:

FILES_ADDED:

SHARED_FILES_CHANGED:

MODEL_FILES_CHANGED:
MUST_BE NONE

DATA_FILES_CHANGED:
MUST_BE NONE

MIGRATIONS:

NECK_ENGINE:

NECK_TESTS:

REAL_CAMERA_TESTS:

HAND_REGRESSION:

ELBOW_REGRESSION:

BREATHING_REGRESSION:

AUTH_REGRESSION:

SESSION_HISTORY_REGRESSION:

PERFORMANCE:

BUILD:

FAIL:
BLOCKED:
NOT_TESTED:

KNOWN_LIMITATIONS:

MERGE_RECOMMENDATION:
READY_FOR_REVIEW / NOT_READY_FOR_MERGE

FINAL_STATUS:
```

---

# 43. FINAL EXECUTION INSTRUCTION

```text
Hãy triển khai thử nghiệm NECK_LATERAL_STRETCH trên một Git branch riêng.

KHÔNG làm việc trực tiếp trên stable branch.

Bắt đầu bằng Git preflight.
Nếu working tree không sạch:
→ STOP
→ không discard
→ không stash tự động
→ báo BLOCKED_BY_DIRTY_WORKTREE.

Không dùng destructive Git commands.

Lưu BASELINE_COMMIT.

Tạo:
feature/neck-lateral-stretch-rulebased

Mặc định dùng BRANCH_ONLY_MODE.
Chỉ tạo worktree nếu repo size/tracked files cho phép.

Bài neck:
- không train;
- không checkpoint;
- rule-based geometry;
- MediaPipe Pose;
- optional Face Landmarker;
- calibration;
- head tilt relative shoulder;
- smoothing;
- hysteresis;
- state machine;
- hold;
- return-center;
- rep count.

Feature flag neck mặc định OFF.

Không sửa:
- HAND model/checkpoint;
- ELBOW model/checkpoint;
- BREATHING engine;
- existing model preprocessing.

Nếu phải sửa shared code:
→ ghi rõ
→ backward-compatible
→ full regression.

Rep chỉ count khi:
CENTER
→ MOVING
→ TARGET
→ HOLD_OK
→ RETURNING
→ CENTER.

Sau implementation:
1. neck unit tests;
2. neck real-camera tests;
3. HAND regression;
4. ELBOW regression;
5. BREATHING regression;
6. auth regression;
7. session/history regression;
8. runtime isolation;
9. build;
10. Git diff audit.

Nếu model/checkpoint file thay đổi:
→ STOP / BLOCKED.

Nếu destructive migration xuất hiện:
→ STOP / BLOCKED.

Không tự merge.
Không tự xóa branch.
Không force push.
Không tự push nếu user chưa yêu cầu.

Nếu mọi gate PASS:
→ READY_FOR_REVIEW.

Nếu chưa:
→ NOT_READY_FOR_MERGE.

Stable branch phải luôn có thể quay lại và sử dụng bình thường.
```

---

# 44. NGUYÊN TẮC CUỐI

```text
Experiment branch = vùng thử nghiệm
Stable branch = vùng bất khả xâm phạm
```

```text
Không merge vì "code chạy".
Chỉ cân nhắc merge khi:
feature mới PASS
+
feature cũ không regression
+
build/security/data safety PASS.
```

```text
Không xóa dữ liệu để sửa code.
Không reset lịch sử để làm sạch lỗi.
Không đụng checkpoint để thêm bài rule-based.
```
