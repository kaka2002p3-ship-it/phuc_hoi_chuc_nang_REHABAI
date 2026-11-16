# RehabAI Two-Layer Architecture Audit — 2026-09-25

## Scope

Đối chiếu repository hiện tại với `RehabAI_Two_Layer_Architecture_Correction_Prompt.md`. Đây là audit trước migration; trạng thái dựa trên code review, chưa phải PASS kiểm thử runtime.

## CURRENT_PUBLIC_ROUTES

- `/` — homepage giới thiệu public (đã có).
- `/login` — auth page public (đã có, nhưng chưa giữ deep-link `redirect`).
- Chưa có public route riêng cho `/about`, `/exercises`, `/exercises/:slug`, `/knowledge`, `/knowledge/:slug`, `/research`, `/faq`.
- `/exercises`, `/history`, `/reports`, `/ai-coach`, `/research`, `/profile`, `/settings` hiện đang được render sau một guard chung nhưng URL không có namespace `/app`; đây là vi phạm ownership của hai lớp.

## CURRENT_PROTECTED_ROUTES

- `/app` — dashboard.
- Các product page hiện đang ở route cũ: `/exercises`, `/practice/:id`, `/history`, `/history/:id`, `/reports`, `/ai-coach`, `/research`, `/settings`, `/profile`.
- Cần chuyển sang `/app/exercises`, `/app/practice/:id`, `/app/history`, `/app/history/:id`, `/app/reports`, `/app/ai-coach`, `/app/research`, `/app/settings`, `/app/profile`.

## CAMERA_LOCATIONS

- Camera permission (`navigator.mediaDevices.getUserMedia`), MediaPipe/realtime extraction và WebSocket nằm trong `frontend/src/pages/Practice.tsx`.
- Hiện page này chỉ được mount sau auth guard của `AppRoutes`; không có camera logic trong homepage. Sau migration, page được giữ nguyên và chỉ mount dưới `/app/practice/:id`.

## SESSION_LOGIC_LOCATIONS

- `Practice.tsx`: start/end session, rep timeline và WebSocket.
- Backend `api/platform.py`: start/end/history/report APIs đều dùng `Depends(current_user)` và ownership theo `user.id`.
- Backend `api/websocket.py`: token bắt buộc, session query có `user_id` ownership.

## AUTH_GUARDS

- Existing guard: mọi path khác `/`, `/login` redirect về `/login` nếu chưa có user.
- Gap: guard chưa dựa trên `path.startsWith('/app')`; public informational routes chưa tồn tại.
- Gap: login/register chưa đọc `redirect` target.

## EXERCISE_API_AUTH

- `/api/exercises` là metadata public, phù hợp với public exercise preview.
- Session, pain, history, reports, chat và user APIs yêu cầu `current_user`.
- WebSocket inference yêu cầu token và kiểm tra session owner.

## DUPLICATED_LOGIC

- Không phát hiện camera/session engine bị copy sang public page; engine tập trung ở `Practice.tsx`.
- Có nhiều link nội bộ trỏ tới route product cũ; cần cập nhật đồng loạt sang `/app/*`.

## RISKY_AREAS

- Đổi route có thể làm hỏng deep-link và notification links.
- Login redirect không được nhận URL ngoài origin hoặc path không bắt đầu `/app`.
- Không được biến các thẻ bài viết/knowledge preview thành citation production khi chưa có `PUBLISHED` content.

## Migration status before changes

```text
PUBLIC/APP separation: PARTIAL
Public camera isolation: CODE_REVIEW_ONLY (camera absent from current public home)
Protected namespace /app/*: NOT_IMPLEMENTED
Public exercise information routes: NOT_IMPLEMENTED
Public knowledge routes: NOT_IMPLEMENTED
Login deep-link: NOT_IMPLEMENTED
Backend session authorization: IMPLEMENTED (code review)
```

## Plan

```text
KEEP: existing visual system, auth, backend, database, Practice engine, knowledge/RAG guardrails
MOVE: product routes and all product links under /app
REFACTOR: AppRoutes guard, AppShell navigation, login redirect
ADD: public informational exercise/knowledge/research pages and authenticated exercise detail route
DELETE: no engine deletion; remove only public direct-start behavior
```

## Implementation report

### KEPT

- Existing backend API, database/migrations, auth, ownership checks, WebSocket token validation, exercise engine and RAG guardrails.
- Existing visual system and public homepage sections.

### MOVED / REFACTORED

- Product routes now live under `/app/*`; legacy product URLs redirect for compatibility.
- AppShell, dashboard, profile, notifications, chatbot actions and exercise links now target `/app/*`.
- Camera/MediaPipe/session code remains in `Practice.tsx`, mounted only by `/app/practice/:id`.
- Login accepts only internal `/app...` redirect targets, preventing open redirects.

### ADDED

- Public informational routes: `/exercises`, `/exercises/:slug`, `/knowledge`, `/knowledge/:slug`, `/research`.
- Public exercise detail pages with description, goal, region, safe instructions, optional tutorial video and login/register CTA.
- Public knowledge/research placeholders marked `MOCK_ONLY`/`NEEDS_REVIEW`; no fake citations or health claims were added.
- `/app/exercises/:slug` maps supported slugs to existing exercise IDs (hand opening=4, elbow extension=2).

### TESTED

- Frontend `npm run lint`: PASS.
- Frontend `npm run build`: PASS.
- Public route smoke: `/`, `/exercises`, `/exercises/hand-opening`, `/knowledge`, `/knowledge/mo-ban-tay`, `/research`: HTTP 200.
- Backend negative auth checks: unauthenticated session start/history/chat all return `401`.
- Backend focused tests: `12 passed`; one known host-Windows MediaPipe WebSocket test remains blocked.
- Docker frontend rebuilt and running; backend health endpoint returns `200`.

### NOT_TESTED

- Browser-level permission assertion (`getUserMedia` call count) with Playwright/browser automation.
- Successful authenticated camera/WebSocket session end-to-end with a physical camera.
- Public article `PUBLISHED` workflow because no published article exists in the current backend.

### BLOCKED / KNOWN LIMITATIONS

- `tests/test_websocket_auth.py::test_websocket_accepts_authenticated_user` fails on host Windows because installed MediaPipe cannot parse its Holistic graph. Docker/Linux remains the supported inference runtime.
- React Router is client-side: direct HTTP requests to `/app/*` return the SPA shell (`200`), while the browser app redirects unauthenticated users to `/login`. Server-side auth is enforced by backend APIs.

### FINAL_STATUS

```text
Two-layer route ownership: IMPLEMENTED
Public informational layer: IMPLEMENTED
Authenticated /app product layer: IMPLEMENTED
Backend API authorization: PASS (focused tests + 401 smoke)
Frontend verification: PASS
Full release verification: NOT_READY until browser E2E and host MediaPipe limitation are resolved
```
