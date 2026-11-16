# RehabAI Two-Layer Architecture Correction Prompt
## CHANGE REQUEST — Tách PUBLIC WEBSITE và AUTHENTICATED PRODUCT APP
## Không làm lại project từ đầu, không phá logic hiện có

> Đây là một **architecture correction / change request** cho project RehabAI hiện tại.
>
> Trước đó project có thể đã được triển khai theo prompt cũ và có khả năng:
> - public website đang chứa logic bài tập;
> - route public có nút bắt đầu tập trực tiếp;
> - camera/MediaPipe/session logic bị đặt sai lớp.
>
> **Không được xóa project hoặc làm lại từ đầu.**
>
> Hãy audit implementation hiện tại, giữ lại các phần hoạt động tốt, và **tách hệ thống thành đúng 2 lớp giao diện** như yêu cầu dưới đây.

---

# 0. MỤC TIÊU KIẾN TRÚC

RehabAI phải có đúng 2 lớp:

```text
                    RehabAI
                       │
        ┌──────────────┴──────────────┐
        │                             │
 PUBLIC WEBSITE                AUTHENTICATED APP
 Không cần đăng nhập           Bắt buộc đăng nhập
        │                             │
        │                             │
 Giới thiệu dự án              Dashboard
 Bài tập dạng thông tin        Chọn bài tập
 Kiến thức                     Camera
 Nghiên cứu                    MediaPipe
 FAQ                           AI inference
        │                      Rep counting
        │                      Complete / Incomplete
        │                      Session Result
        │                      History / Progress
        │                      AI Coach
        │
 [Đăng nhập] [Đăng ký]
        │
        └──────────────→ Login/Register success
                                 │
                                 ▼
                               /app
```

---

# 1. QUY TẮC QUAN TRỌNG NHẤT

## PUBLIC WEBSITE TUYỆT ĐỐI KHÔNG ĐƯỢC CHO NGƯỜI DÙNG TẬP

Public website chỉ có chức năng:

```text
giới thiệu
đọc
xem
tìm hiểu
đăng nhập
đăng ký
```

Public website KHÔNG được:

```text
khởi tạo camera
request camera permission
khởi tạo MediaPipe
mở WebSocket exercise session
gọi movement model
gọi rep-counting model
đếm repetitions
đánh giá Complete / Incomplete
tạo exercise session
lưu exercise result
lưu rep event
hiển thị realtime inference
```

Nếu bất kỳ logic nào ở trên đang tồn tại trong public route:

```text
KHÔNG XÓA LOGIC
→ MOVE / REUSE / REFACTOR sang protected /app route
```

---

# 2. PUBLIC WEBSITE — LỚP 1

Public routes phải truy cập được khi chưa login.

Đề xuất:

```text
/
/about
/exercises
/exercises/[slug]
/knowledge
/knowledge/[slug]
/research
/faq
/login
/register
```

Public navigation:

```text
RehabAI

Trang chủ
Về dự án
Bài tập
Kiến thức
Nghiên cứu
FAQ

[Đăng nhập]
[Đăng ký]
```

---

# 3. PUBLIC HOMEPAGE

Homepage chỉ làm nhiệm vụ giới thiệu.

Sections:

```text
Header
Hero
Benefit Strip
Exercise Preview
How RehabAI Works
About RehabAI
Knowledge Preview
Research Preview
FAQ
Final CTA
Footer
```

Hero CTA:

```text
[Đăng nhập để sử dụng RehabAI]
[Đăng ký]
[Tìm hiểu thêm]
```

Không dùng CTA:

```text
Bắt đầu tập ngay
Mở camera
Start exercise
```

nếu hành động đó diễn ra ngay trong public website.

---

# 4. PUBLIC EXERCISE PAGE

Ví dụ:

```text
/exercises/hand-opening
/exercises/elbow-extension
/exercises/neck-lateral-stretch
/exercises/deep-breathing
```

Public exercise page chỉ được hiển thị:

```text
Tên bài
Mô tả
Mục tiêu
Vùng vận động
Hình minh họa
Video hướng dẫn nếu có
Cách thực hiện cơ bản
Lưu ý
Bài viết liên quan
```

CTA:

```text
[Đăng nhập để sử dụng RehabAI]
[Đăng ký tài khoản]
```

Không có:

```text
Camera
Rep Count
Tracking state
Complete / Incomplete
Live skeleton
Start Session
WebSocket
Realtime model
```

---

# 5. AUTHENTICATED APP — LỚP 2

Toàn bộ chức năng thật phải nằm dưới:

```text
/app/*
```

Routes đề xuất:

```text
/app
/app/dashboard
/app/exercises
/app/exercises/[slug]
/app/session/[exercise]
/app/progress
/app/history
/app/coach
/app/profile
/app/settings
```

Tất cả route này:

```text
require authentication
```

Nếu user chưa đăng nhập:

```text
redirect → /login
```

---

# 6. CHỨC NĂNG CHỈ ĐƯỢC TỒN TẠI TRONG /app

Chỉ authenticated app mới được:

```text
request camera permission
open camera
initialize MediaPipe
run pose/hands tracking
connect exercise WebSocket
load movement model
count repetitions
classify Complete / Incomplete
create session
save session
save history
show progress
show AI Coach
```

---

# 7. LOGIN / REGISTER FLOW

## Từ public exercise page

Ví dụ:

```text
/exercises/hand-opening
```

User bấm:

```text
[Đăng nhập để sử dụng RehabAI]
```

→

```text
/login?redirect=/app/exercises/hand-opening
```

Login thành công:

```text
→ /app/exercises/hand-opening
```

## Nếu chưa có tài khoản

```text
/register
```

Register thành công:

```text
→ /app
```

hoặc quay về redirect target nếu có.

---

# 8. ROUTE GUARD

Bắt buộc bảo vệ:

```text
/app/*
```

Pseudo logic:

```text
if path startsWith("/app"):
    requireAuthenticatedUser()
else:
    allowPublicAccess()
```

Không dựa vào việc chỉ ẩn button ở frontend.

Backend/API nhạy cảm vẫn phải check auth.

---

# 9. API AUTHORIZATION

Các API liên quan exercise phải yêu cầu user hợp lệ:

```text
POST /api/sessions
POST /api/session/*
WS /ws/exercise/*
GET /api/history
GET /api/progress
POST /api/chat
```

Không cho unauthenticated user gọi exercise/session API chỉ vì biết URL.

Nếu API đã có auth:

```text
giữ nguyên
```

Nếu chưa có:

```text
bổ sung authorization mà không phá contract ngoài phần cần thiết
```

---

# 10. QUY TẮC DI CHUYỂN CODE HIỆN TẠI

Nếu prompt cũ đã làm sai kiến trúc:

## Case A — Camera đang nằm trong `/exercises/[slug]`

Sửa:

```text
/exercises/[slug]
→ chỉ informational UI
```

Move camera logic sang:

```text
/app/exercises/[slug]
hoặc
/app/session/[exercise]
```

## Case B — Public card có "Bắt đầu tập"

Đổi CTA thành:

```text
[Đăng nhập để sử dụng RehabAI]
```

hoặc nếu đã login:

```text
[Đi tới ứng dụng]
```

nhưng action phải dẫn vào `/app`.

## Case C — Public homepage đang render realtime demo bằng camera thật

Thay bằng:

```text
static mockup
illustration
demo image
pre-recorded non-interactive preview
```

Không dùng camera thật.

## Case D — Logic session bị duplicate

Refactor thành shared module:

```text
exercise engine
camera component
MediaPipe adapter
session hooks
```

nhưng chỉ import/use trong `/app`.

---

# 11. KHÔNG LÀM LẠI TOÀN BỘ UI

Giữ lại nếu đang tốt:

```text
design system
colors
typography
cards
article system
knowledge system
research pipeline
public homepage sections
auth pages
existing backend logic
database
AI Coach
exercise engine
```

Chỉ sửa:

```text
route ownership
auth boundary
CTA behavior
camera location
session location
protected navigation
```

---

# 12. PUBLIC WEBSITE NAVIGATION

Khi chưa login:

```text
Trang chủ
Về dự án
Bài tập
Kiến thức
Nghiên cứu
FAQ
Đăng nhập
Đăng ký
```

Khi đã login nhưng vẫn ở public site:

Có thể hiển thị:

```text
[Đi tới ứng dụng]
```

thay vì:

```text
[Đăng nhập]
```

Không tự động ép user khỏi public site nếu họ muốn đọc article.

---

# 13. AUTHENTICATED APP NAVIGATION

Trong `/app`:

```text
Trang chủ
Bài tập
Tiến trình
Lịch sử
AI Coach
Hồ sơ
Cài đặt
```

Không cần hiển thị toàn bộ public nav trong app shell.

Có thể có:

```text
[Trang giới thiệu RehabAI]
```

như secondary link nếu cần.

---

# 14. BÀI TẬP HIỆN TẠI

Public chỉ xem thông tin:

```text
HAND_OPENING
ELBOW_EXTENSION
NECK_LATERAL_STRETCH
DEEP_BREATHING
```

Authenticated app mới được thực hiện.

Mapping:

```text
/exercises/hand-opening
→ public information

/app/exercises/hand-opening
→ authenticated product
```

Tương tự cho 3 bài còn lại.

---

# 15. KNOWLEDGE / ARTICLES

Knowledge vẫn là PUBLIC.

Routes:

```text
/knowledge
/knowledge/[slug]
```

Ai cũng đọc được.

Article cuối bài có thể có:

```text
Bài tập liên quan: Giãn cơ cổ

[Đăng nhập để sử dụng RehabAI]
```

Không được chạy exercise trực tiếp từ article page.

---

# 16. KNOWLEDGE RESEARCH PIPELINE

Giữ lại pipeline nếu đã triển khai:

```text
Topic
→ Search
→ Sources
→ Evidence
→ Citation
→ Draft
→ Fact Check
→ Human Review
→ Approved
→ Published
```

Không cần thay đổi chỉ vì tách 2 lớp UI.

Knowledge public:

```text
chỉ PUBLISHED article
```

RAG:

```text
chỉ APPROVED/PUBLISHED knowledge
```

---

# 17. PUBLIC WEBSITE KHÔNG PHỤ THUỘC PRODUCT ENGINE

Homepage/public article/public exercise information phải vẫn chạy nếu:

```text
camera service lỗi
MediaPipe lỗi
model chưa load
WebSocket exercise lỗi
Ollama lỗi
RAG lỗi
```

Public website phải degrade gracefully.

---

# 18. SESSION MODEL

Exercise session chỉ được tạo sau khi:

```text
authenticated = true
```

Flow:

```text
Authenticated user
↓
/app/exercises/[slug]
↓
Pre-check
↓
Camera setup
↓
Start session
↓
Realtime tracking
↓
Rep count
↓
Complete / Incomplete
↓
Result
↓
Save history
```

---

# 19. SECURITY RULE

Không được coi frontend route guard là đủ.

Backend phải verify:

```text
user_id
ownership
session access
history access
progress access
chat ownership nếu có
```

Unauthenticated request:

```text
401
```

Unauthorized request:

```text
403
```

---

# 20. IMPLEMENTATION AUDIT — BẮT BUỘC LÀM TRƯỚC

Trước khi sửa code, tạo audit:

```text
CURRENT_PUBLIC_ROUTES:
CURRENT_PROTECTED_ROUTES:
CAMERA_LOCATIONS:
SESSION_LOGIC_LOCATIONS:
AUTH_GUARDS:
EXERCISE_API_AUTH:
DUPLICATED_LOGIC:
RISKY_AREAS:
```

Không bắt đầu refactor lớn trước audit.

---

# 21. MIGRATION PLAN

Coding agent phải tạo plan trước khi sửa:

```text
KEEP
MOVE
REFACTOR
DELETE
ADD
```

Ví dụ:

```text
KEEP:
- Hero
- Knowledge section
- Research section

MOVE:
- Camera component
- Exercise session hook

REFACTOR:
- Exercise page routing

DELETE:
- public Start Session behavior only

ADD:
- /app protected route
- auth redirect
```

---

# 22. TEST CASES BẮT BUỘC

## T01 — Public homepage

```text
not logged in
→ /
→ PASS
```

## T02 — Public article

```text
not logged in
→ /knowledge/...
→ PASS
```

## T03 — Public exercise information

```text
not logged in
→ /exercises/hand-opening
→ PASS
→ no camera permission
```

## T04 — Public exercise must not start

```text
not logged in
→ /exercises/hand-opening
→ cannot create session
```

## T05 — Protected app

```text
not logged in
→ /app
→ redirect /login
```

## T06 — Protected exercise

```text
not logged in
→ /app/exercises/hand-opening
→ redirect /login
```

## T07 — Login redirect

```text
/login?redirect=/app/exercises/hand-opening
→ valid login
→ /app/exercises/hand-opening
```

## T08 — Authenticated exercise

```text
logged in
→ /app/exercises/hand-opening
→ camera allowed
→ session can start
```

## T09 — Direct API attack

```text
not logged in
→ session API
→ 401
```

## T10 — Public page must not initialize exercise engine

Check:

```text
MediaPipe not loaded
camera getUserMedia not called
exercise websocket not opened
```

---

# 23. FRONTEND VERIFICATION

Chạy đúng command của repo:

```text
lint
typecheck
tests
production build
```

Nếu Next.js:

```text
npm run lint
npm run typecheck
npm test
npm run build
```

chỉ dùng nếu repo thật sự có các script đó.

---

# 24. BACKEND VERIFICATION

Chạy:

```text
auth tests
route tests
session tests
ownership tests
API smoke tests
```

Không được skip auth regression.

---

# 25. KHÔNG ĐƯỢC GIẢ PASS

Nếu chưa test:

```text
NOT_TESTED
```

Nếu bị thiếu môi trường:

```text
BLOCKED
```

Nếu chỉ nhìn code:

```text
CODE_REVIEW_ONLY
```

Không được gọi:

```text
PASS
```

nếu chưa thực thi test tương ứng.

---

# 26. ACCEPTANCE CRITERIA

## Public Website

- [ ] Truy cập không cần login
- [ ] Không camera
- [ ] Không MediaPipe
- [ ] Không rep counting
- [ ] Không Complete / Incomplete
- [ ] Không session
- [ ] Không history write
- [ ] Không exercise WebSocket
- [ ] Có project info
- [ ] Có exercise info
- [ ] Có knowledge
- [ ] Có research
- [ ] Có FAQ
- [ ] Có login/register

## Authenticated App

- [ ] `/app/*` protected
- [ ] Có dashboard
- [ ] Có exercise flow
- [ ] Camera chỉ ở `/app`
- [ ] Session chỉ authenticated
- [ ] History protected
- [ ] Progress protected
- [ ] AI Coach protected nếu product yêu cầu
- [ ] Ownership checks

## Routing

- [ ] Public exercise ≠ private exercise
- [ ] Login redirect đúng
- [ ] Register redirect đúng
- [ ] Deep link `/app/...` được bảo vệ

## Regression

- [ ] Existing UI không bị phá
- [ ] Existing backend không bị phá
- [ ] Existing knowledge pipeline không bị phá
- [ ] Existing auth vẫn hoạt động
- [ ] Existing exercise engine được reuse

---

# 27. OUTPUT CUỐI CÙNG

Sau khi hoàn thành, báo cáo:

```text
ARCHITECTURE_AUDIT:
- ...

KEPT:
- ...

MOVED:
- ...

REFACTORED:
- ...

DELETED:
- ...

ADDED:
- ...

PUBLIC_ROUTES:
- ...

PROTECTED_ROUTES:
- ...

AUTH_GUARDS:
- ...

API_AUTHORIZATION:
- ...

TESTED:
- ...

NOT_TESTED:
- ...

BLOCKED:
- ...

KNOWN_LIMITATIONS:
- ...

FINAL_STATUS:
- ...
```

---

# 28. FINAL EXECUTION PROMPT

```text
Đây là CHANGE REQUEST cho RehabAI hiện tại.

KHÔNG làm lại project từ đầu.

Hãy audit implementation hiện có và chỉnh kiến trúc thành đúng 2 lớp:

LỚP 1 — PUBLIC WEBSITE
- không cần login;
- chỉ giới thiệu;
- chỉ đọc;
- project;
- exercise information;
- knowledge;
- research;
- FAQ;
- login/register;
- TUYỆT ĐỐI KHÔNG ĐƯỢC CHO TẬP.

PUBLIC WEBSITE KHÔNG ĐƯỢC:
- camera;
- MediaPipe;
- model inference;
- rep counting;
- Complete/Incomplete;
- session creation;
- exercise WebSocket.

LỚP 2 — AUTHENTICATED APP
- tất cả nằm dưới /app/*;
- bắt buộc login;
- dashboard;
- exercise;
- camera;
- MediaPipe;
- AI model;
- rep counting;
- Complete/Incomplete;
- session result;
- progress;
- history;
- AI Coach.

Nếu logic exercise hiện đang nằm trong public route:
KHÔNG XÓA.
Hãy MOVE / REUSE nó trong /app.

Public exercise page:
- informational only;
- CTA = "Đăng nhập để sử dụng RehabAI".

Login flow:
public CTA
→ /login?redirect=/app/exercises/{slug}
→ login success
→ protected exercise.

Bắt buộc:
1. Audit trước.
2. Lập migration plan.
3. Sửa ít nhất có thể.
4. Giữ UI tốt đang có.
5. Không phá auth/backend/DB.
6. Chạy lint/typecheck/tests/build.
7. Test public không gọi camera.
8. Test unauthenticated không vào /app.
9. Test unauthenticated không tạo session.
10. Không báo PASS nếu chưa test.

Mục tiêu cuối cùng:

PUBLIC WEBSITE
= website giới thiệu và kiến thức

AUTHENTICATED /app
= sản phẩm RehabAI thực tế

Hai lớp phải tách rõ ràng cả về:
- route;
- UI;
- auth;
- camera;
- session;
- API access;
- product behavior.
```

---

# 29. FINAL PRINCIPLE

```text
Public = Learn about RehabAI
Private = Use RehabAI
```

Không được trộn hai lớp này nữa.
