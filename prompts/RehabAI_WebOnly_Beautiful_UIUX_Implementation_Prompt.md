# RehabAI Web-Only UI/UX + Frontend/Backend Implementation Prompt

## 0. Mục tiêu

Xây dựng **RehabAI phiên bản Web trước**, chưa triển khai mobile.

Mục tiêu sản phẩm:

- Giao diện hiện đại, thân thiện, tạo cảm giác tích cực và nhẹ nhàng khi sử dụng.
- Hỗ trợ **Light Mode** và **Dark Mode**.
- Màu sắc phải cân bằng:
  - không quá trắng/chói;
  - không quá tối/nặng nề;
  - ưu tiên cảm giác sạch, ấm, vui vẻ, đáng tin cậy.
- Tập trung vào hai bài:
  - `HAND_OPENING` — Mở bàn tay.
  - `ELBOW_EXTENSION` — Duỗi khuỷu tay.
- Frontend Web dùng Next.js/React.
- Backend dùng FastAPI.
- Realtime qua WebSocket.
- Chatbot dùng Ollama local.
- Database chính dùng PostgreSQL.
- Có thể dùng Redis cho session/cache nếu cần.
- Có thể dùng MinIO hoặc local object storage cho video/file.
- Không thêm X-ray/CT.
- Không thêm AI tự đề xuất phác đồ điều trị.

---

# 1. Vai trò của Agent

Bạn là:

- Senior Product Designer
- Senior UI/UX Designer
- Senior Frontend Engineer
- Senior Backend Engineer
- Design System Engineer
- AI Product Engineer

Nhiệm vụ:

1. Thiết kế lại toàn bộ RehabAI theo hướng Web-first.
2. Giữ giao diện nhất quán, đẹp, hiện đại và giàu cảm xúc tích cực.
3. Xây dựng design system rõ ràng.
4. Tạo các trang frontend hoàn chỉnh.
5. Tích hợp backend hiện tại thay vì phá bỏ kiến trúc đang chạy.
6. Tạo API contract, WebSocket contract và các trạng thái loading/error/empty.
7. Giữ Ollama là local chatbot, không đưa cloud fallback vào production.
8. Không bịa dữ liệu hoặc dùng mock để chứng minh production đã hoạt động.

---

# 2. Định hướng hình ảnh tổng thể

## 2.1. Tính cách thương hiệu

RehabAI phải tạo cảm giác:

- vui vẻ;
- nhẹ nhàng;
- có hy vọng;
- hiện đại;
- khoa học;
- thân thiện;
- không lạnh lẽo như phần mềm bệnh viện truyền thống;
- không quá game hóa;
- không quá trẻ con.

Từ khóa thiết kế:

`calm + hopeful + modern + soft + trustworthy + human`

Slogan có thể dùng:

> **Your Hand, Brighter Tomorrow**

hoặc:

> **Small Movements, Big Changes**

---

# 3. Design System

## 3.1. Light Mode

Không dùng nền trắng tinh `#FFFFFF` cho toàn bộ trang.

Nền chính đề xuất:

- `#F7F8FC`
- `#F5F7FB`
- `#F6F8FA`

Card:

- `#FFFFFF`
- shadow rất nhẹ;
- border `#E8EBF2`.

Text chính:

- `#17233C`
- `#22304A`

Text phụ:

- `#667085`
- `#7A869A`

Primary:

- Indigo/Violet:
  - `#5B5FEF`
  - `#6C63FF`

Secondary:

- Aqua/Mint:
  - `#2EC4B6`
  - `#43D3B4`

Accent:

- Coral:
  - `#FF7A7A`

Positive:

- `#34C98F`

Warning:

- `#F5B942`

Error:

- `#E75A67`

Không dùng quá nhiều màu cùng lúc.

---

## 3.2. Dark Mode

Dark mode không được dùng nền đen tuyệt đối.

Background:

- `#111827`
- `#151B2B`
- `#171C2C`

Card:

- `#1E2638`
- `#20283A`

Borders:

- `#2D3748`

Primary text:

- `#F1F5F9`

Secondary text:

- `#AAB3C5`

Primary accent giữ Indigo nhưng sáng hơn:

- `#7C83FF`

Mint:

- `#4EDBC4`

Coral:

- `#FF8A8A`

Dark mode phải tạo cảm giác êm, không gắt.

---

# 4. Typography

Ưu tiên:

- Inter
- Manrope
- Plus Jakarta Sans

Gợi ý:

- H1: 36–48 px
- H2: 28–32 px
- H3: 20–24 px
- Body: 15–17 px
- Small: 12–14 px

Không dùng font quá mảnh.

---

# 5. Layout tổng thể

Web desktop ưu tiên:

```text
┌──────────────────────────────────────────────────────────────┐
│ Top Navigation                                               │
├──────────────┬───────────────────────────────────────────────┤
│ Sidebar      │ Main Content                                  │
│              │                                               │
│ Dashboard    │ Cards / Camera / Charts / AI Coach            │
│ Exercise     │                                               │
│ History      │                                               │
│ Analytics    │                                               │
│ AI Coach     │                                               │
│ Research     │                                               │
│ Settings     │                                               │
└──────────────┴───────────────────────────────────────────────┘
```

Responsive nhưng tập trung Desktop/Web trước.

---

# 6. Trang Landing / Login

## Mục tiêu

Tạo cảm giác chào đón và có động lực.

## Bố cục

Left:

- headline lớn;
- mô tả ngắn;
- CTA;
- tính năng nổi bật.

Right:

- minh họa bàn tay / skeleton / abstract 3D nhẹ;
- không dùng hình ảnh quá y khoa.

Headline ví dụ:

> Phục hồi hôm nay, cho một ngày mai tốt đẹp hơn.

Subheadline:

> RehabAI đồng hành cùng bạn qua từng chuyển động nhỏ, bằng công nghệ AI riêng tư và dễ sử dụng.

CTA:

- `Bắt đầu ngay`
- `Tìm hiểu thêm`

---

# 7. Dashboard người tập

## Thành phần chính

### 7.1. Greeting card

Ví dụ:

> Chào buổi sáng, Nguyễn Văn A 👋

Hiển thị:

- số buổi tuần này;
- streak;
- mục tiêu tuần;
- tiến độ.

### 7.2. Hai bài tập chính

Card 1:

- Mở bàn tay
- icon/illustration bàn tay
- `Bắt đầu`

Card 2:

- Duỗi khuỷu tay
- icon cánh tay
- `Bắt đầu`

### 7.3. Tiến độ tuần

- bar chart;
- số buổi;
- số rep;
- thời gian.

### 7.4. Thành tích gần đây

- huy hiệu;
- streak;
- milestone.

Không dùng gamification quá mức.

---

# 8. Trang Realtime Exercise

Đây là màn hình quan trọng nhất.

## Layout

```text
┌───────────────────────────────┬──────────────────────┐
│ Camera / skeleton overlay     │ Session Panel        │
│                               │                      │
│                               │ Rep count            │
│                               │ Tracking             │
│                               │ Complete/Incomplete  │
│                               │ Timer                │
│                               │ AI short feedback    │
└───────────────────────────────┴──────────────────────┘
```

## Camera

Hiển thị:

- video camera;
- MediaPipe landmarks;
- vùng quan sát;
- trạng thái tracking;
- FPS;
- timer.

Không hiển thị quá nhiều debug mặc định.

## Right session panel

- Rep: `8 / 10`
- Complete / Incomplete
- Tracking: Good / Lost / Recovering
- Session timer
- Pain status nếu có
- nút:
  - Pause
  - Resume
  - End Session

## Feedback card

Ví dụ:

> Tốt lắm! Hệ thống đang theo dõi bàn tay ổn định.

Nếu tracking lost:

> Hệ thống tạm mất dấu bàn tay. Hãy đưa bàn tay trở lại vùng camera.

Không tự bịa lỗi chi tiết.

---

# 9. Session Timeline — tính năng đặc sắc

Thêm một timeline phía dưới camera:

```text
Rep 1   Rep 2   Rep 3   Rep 4   Rep 5
 ✓       ✓       !       ✓       ...
```

Click vào từng rep để xem:

- timestamp;
- completion result;
- tracking status;
- validated event;
- confidence nếu có;
- không tự suy diễn.

Đây là điểm đặc sắc của RehabAI.

---

# 10. Trang Session Result

Hiển thị sau khi kết thúc buổi tập.

## Hero result card

- số rep;
- số complete;
- số incomplete;
- tổng thời gian;
- tỷ lệ tracking tốt;
- pain before / after nếu có.

Không gọi đây là “điểm sức khỏe”.

## Biểu đồ

- rep timeline;
- completion distribution;
- tracking quality;
- góc hoặc feature chỉ khi model thực sự cung cấp.

## AI summary

Ollama có thể tổng kết:

> Hôm nay bạn hoàn thành 8/10 lần lặp. Trong 2 lần chưa hoàn thành, hệ thống không có đủ dữ liệu để xác định nguyên nhân cụ thể.

Không bịa.

---

# 11. Progress Analytics

Tabs:

- Tổng quan
- Mở bàn tay
- Duỗi khuỷu tay

Filters:

- 7 ngày
- 30 ngày
- 3 tháng
- tùy chỉnh

Metrics:

- sessions;
- reps;
- complete ratio;
- exercise duration;
- tracking reliability.

Charts:

- line chart;
- bar chart;
- stacked chart.

Không dùng quá nhiều chart trên một màn hình.

---

# 12. Progress Story — điểm đặc sắc

Ngoài biểu đồ, có vùng:

> **Câu chuyện tiến trình của bạn**

Backend tính dữ liệu thật, Ollama chỉ diễn đạt.

Ví dụ:

> Trong 7 ngày gần đây, bạn đã hoàn thành 4 buổi tập với tổng 86 lần lặp. Tần suất tập ổn định hơn tuần trước.

Nếu không đủ dữ liệu:

> Chưa có đủ dữ liệu để tạo tổng kết tuần.

---

# 13. AI Coach

Trang riêng hoặc panel side drawer.

Chat UI:

- bubble nhẹ;
- avatar đơn giản;
- không dùng hiệu ứng quá nhiều.

Quick actions:

- `Tóm tắt buổi tập`
- `Giải thích kết quả`
- `Tôi muốn tâm sự`
- `Gợi ý ăn uống`
- `Cách dùng RehabAI`

AI Coach không được:

- tự chẩn đoán;
- bịa rep;
- bịa lỗi động tác;
- thay đổi bài tập;
- kê thuốc;
- kê supplement.

---

# 14. History

Table/card hybrid.

Columns:

- ngày;
- bài tập;
- rep;
- complete;
- duration;
- pain before/after;
- model version;
- view details.

Filters:

- exercise;
- date;
- status.

Export:

- CSV
- PDF nếu backend hỗ trợ.

---

# 15. Research Mode — điểm đặc sắc cho đề tài

Tạo một chế độ riêng:

`Research Mode`

Chỉ dùng cho người được phân quyền.

Hiển thị:

- session id;
- subject/user id pseudonymized;
- model version;
- prompt version;
- frame rate;
- inference latency;
- tracking quality;
- confidence;
- event log;
- timeline;
- source dataset nếu dùng offline research;
- export.

Không hiển thị toàn bộ debug này cho người tập bình thường.

---

# 16. Theme Toggle

Top-right:

- Sun icon
- Moon icon

Có 3 mode:

- Light
- Dark
- System

Lưu preference vào local storage và user settings.

Không reload toàn trang khi đổi theme.

Dùng CSS variables hoặc Tailwind theme tokens.

---

# 17. Motion / Animation

Dùng animation nhẹ:

- card hover: 150–200ms;
- fade in;
- progress bar;
- chart transition;
- skeleton glow rất nhẹ.

Không dùng animation liên tục gây mệt.

Tắt hoặc giảm motion nếu:

`prefers-reduced-motion`.

---

# 18. Accessibility

Phải có:

- contrast tốt;
- keyboard navigation;
- focus ring;
- aria-label;
- form validation;
- screen reader support cơ bản;
- không dùng màu duy nhất để truyền tải trạng thái.

Ví dụ:

Không chỉ dùng đỏ/xanh.

Dùng:

- icon;
- text;
- màu.

---

# 19. Frontend stack

Khuyến nghị:

```text
Next.js 14+
TypeScript
TailwindCSS
shadcn/ui
Lucide Icons
Recharts
Framer Motion
React Query / TanStack Query
Axios hoặc fetch wrapper
Zustand nếu cần global state
```

Có thể dùng Three.js nhẹ cho minh họa hand twin nhưng không bắt buộc.

---

# 20. Frontend structure

```text
frontend/
├── app/
│   ├── login/
│   ├── dashboard/
│   ├── exercise/
│   ├── session/
│   ├── progress/
│   ├── history/
│   ├── ai-coach/
│   ├── research/
│   └── settings/
├── components/
│   ├── layout/
│   ├── camera/
│   ├── charts/
│   ├── chat/
│   ├── session/
│   ├── research/
│   └── ui/
├── hooks/
├── services/
├── stores/
├── types/
└── styles/
```

---

# 21. Backend architecture

```text
FastAPI
├── Auth
├── Users
├── Exercise Sessions
├── Realtime WebSocket
├── Movement Inference
├── Ollama Chat
├── Analytics
├── Reports
├── Research Mode
└── Settings
```

Không cần microservices thật sự ngay.

Ưu tiên modular monolith trước.

---

# 22. Backend modules

```text
backend/
├── api/
│   ├── auth.py
│   ├── users.py
│   ├── exercise.py
│   ├── sessions.py
│   ├── chat.py
│   ├── analytics.py
│   ├── reports.py
│   └── research.py
├── services/
│   ├── movement_service.py
│   ├── chat_service.py
│   ├── analytics_service.py
│   ├── report_service.py
│   └── research_service.py
├── websocket/
│   └── exercise_ws.py
├── models/
├── schemas/
├── db/
└── prompts/
```

---

# 23. API đề xuất

```text
POST /api/auth/login
POST /api/auth/register
GET  /api/users/me

POST /api/exercise/session/start
POST /api/exercise/session/end

GET  /api/sessions
GET  /api/sessions/{id}

POST /api/chat

GET  /api/analytics/summary
GET  /api/analytics/progress

GET  /api/research/sessions
GET  /api/research/session/{id}

GET  /api/settings
PUT  /api/settings
```

Realtime:

```text
WS /ws/exercise/{session_id}
```

---

# 24. WebSocket event contract

Ví dụ:

```json
{
  "type": "movement_update",
  "timestamp": 1720000000,
  "tracking_status": "valid",
  "rep": 7,
  "completion": null,
  "validated_event": null
}
```

Rep completed:

```json
{
  "type": "rep_completed",
  "rep": 7,
  "completion": "complete",
  "validated_event": null
}
```

Tracking lost:

```json
{
  "type": "tracking_status",
  "status": "lost"
}
```

Không gửi giá trị giả.

---

# 25. Database entities

```text
users
exercise_types
exercise_sessions
session_repetitions
pain_assessments
movement_predictions
movement_events
chat_conversations
chat_messages
reports
settings
```

Research metadata có thể lưu thêm:

```text
model_version
prompt_version
inference_latency
tracking_quality
```

---

# 26. PostgreSQL

Dùng PostgreSQL làm database chính.

Redis chỉ dùng:

- session cache;
- realtime ephemeral state;
- rate limit;
- queue nhẹ nếu cần.

Không dùng Redis làm database chính.

---

# 27. Ollama integration

Flow:

```text
Frontend
↓
POST /api/chat
↓
FastAPI
↓
Auth + Ownership
↓
Context Builder
↓
Safety Rules
↓
Ollama Local
↓
JSON Validation
↓
Frontend
```

Không gọi Ollama trực tiếp từ browser.

---

# 28. Local-first

Production phải hoạt động:

```text
Browser
↓
FastAPI local/server
↓
PostgreSQL
↓
Ollama local
```

Không dùng cloud fallback mặc định.

---

# 29. Visual states

Mỗi component phải có:

- Default
- Hover
- Active
- Disabled
- Loading
- Error
- Empty
- Success

Không được để layout nhảy khi loading.

Dùng skeleton loading.

---

# 30. Empty states

Ví dụ lịch sử chưa có:

> Chưa có buổi tập nào. Bắt đầu một phiên tập để xem tiến trình của bạn tại đây.

Không hiện bảng trống lạnh lẽo.

---

# 31. Error states

Ví dụ camera lỗi:

> Không thể truy cập camera. Hãy kiểm tra quyền camera trong trình duyệt.

Ollama unavailable:

> AI Coach hiện tạm không khả dụng. Bạn vẫn có thể tiếp tục buổi tập bình thường.

Backend offline:

> Không thể kết nối máy chủ. Hãy thử lại.

---

# 32. Đặc sắc của sản phẩm

Ưu tiên 6 điểm:

1. Realtime skeletal overlay.
2. Session Timeline.
3. Progress Story.
4. AI Coach local.
5. Research Mode.
6. Light/Dark Theme có mood tích cực.

---

# 33. Không nên làm ở bản đầu

Không thêm:

- social feed;
- leaderboard toàn cầu;
- NFT;
- AI chẩn đoán;
- AI chọn bài tập thay chuyên viên;
- X-ray/CT;
- video call;
- mobile app;
- microservices phức tạp;
- Kubernetes.

---

# 34. Mục tiêu UI cảm xúc

Người dùng mở RehabAI phải cảm thấy:

- “Mình có thể làm được.”
- “Hệ thống này dễ dùng.”
- “Mình được hỗ trợ, không bị phán xét.”
- “Tiến trình của mình được nhìn thấy.”
- “AI đang hỗ trợ chứ không áp đặt.”

---

# 35. Prompt cho Agent thực hiện

```text
Hãy triển khai RehabAI Web-Only theo toàn bộ tài liệu này.

Yêu cầu:

1. Đọc repository hiện tại trước.
2. Không thay framework đang hoạt động nếu không cần.
3. Xây design system light/dark trước.
4. Tạo layout/sidebar/topbar thống nhất.
5. Triển khai lần lượt:
   - Landing/Login
   - Dashboard
   - Exercise Realtime
   - Session Result
   - Progress Analytics
   - AI Coach
   - History
   - Research Mode
   - Settings
6. Kết nối API thật hiện có.
7. Nếu API chưa có:
   - tạo interface/service rõ ràng;
   - không giả production success.
8. Tạo loading/error/empty states.
9. Kiểm tra responsive desktop/tablet.
10. Kiểm tra accessibility.
11. Không để theme quá sáng hoặc quá tối.
12. Không dùng màu neon quá mức.
13. Không tạo giao diện bệnh viện lạnh lẽo.
14. Không thêm mobile ở giai đoạn này.
15. Không dùng cloud LLM fallback.
16. Ollama vẫn là local chatbot.
17. Camera/session phải hoạt động dù Ollama lỗi.
18. Không bịa thông tin model/session.
19. Tạo README:
    - run frontend;
    - run backend;
    - env;
    - WebSocket;
    - theme;
    - screenshots;
    - known limitations.
20. Chạy:
    - lint;
    - typecheck;
    - unit tests;
    - production build.

Báo cáo cuối theo format:

IMPLEMENTED:
TESTED:
NOT_TESTED:
BLOCKED:
KNOWN_LIMITATIONS:
```

---

# 36. Acceptance Criteria

## UI

- [ ] Có Light Mode.
- [ ] Có Dark Mode.
- [ ] Theme đổi mượt.
- [ ] Không quá sáng.
- [ ] Không quá tối.
- [ ] Có màu accent đẹp.
- [ ] UI nhất quán.
- [ ] Responsive.
- [ ] Có empty/error/loading state.
- [ ] Có accessibility cơ bản.

## Product

- [ ] Dashboard.
- [ ] 2 bài tập.
- [ ] Camera realtime.
- [ ] Rep tracking.
- [ ] Complete/Incomplete.
- [ ] Tracking status.
- [ ] Session Timeline.
- [ ] Session Result.
- [ ] Analytics.
- [ ] History.
- [ ] AI Coach.
- [ ] Research Mode.
- [ ] Settings.

## Backend

- [ ] Authentication.
- [ ] Ownership.
- [ ] Session management.
- [ ] WebSocket.
- [ ] Analytics.
- [ ] Ollama local.
- [ ] Error handling.
- [ ] PostgreSQL.
- [ ] Model/prompt version metadata.

---

# 37. Future Expansion

Chỉ sau khi Web ổn định mới cân nhắc:

- mobile;
- PWA nâng cao;
- fully on-device AI;
- multi-user therapist portal;
- mobile offline;
- model optimization;
- WebGPU.

---

# 38. Final Design Principle

> RehabAI không nên trông như một công cụ bệnh viện lạnh lẽo.

> RehabAI phải tạo cảm giác như một người bạn công nghệ nhẹ nhàng, đáng tin cậy và giúp người dùng thấy được từng tiến bộ nhỏ của mình.

**Small Movements, Big Changes.**
