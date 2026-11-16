# RehabAI Web

Web-first interface for RehabAI. The existing React 19 + Vite stack is retained because it is already integrated with the FastAPI backend.

## Run locally

Backend (terminal 1):

```powershell
cd D:\PhucHoiChucNangTay\rehabai
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend (terminal 2):

```powershell
cd D:\PhucHoiChucNangTay\rehabai\frontend
npm install
npm run dev
```

Ollama is local-only. The browser calls FastAPI; it never calls Ollama directly. Configure the backend with `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `OLLAMA_ENABLED`. Camera/session operation remains available when Ollama is offline.

Optional frontend environment:

```text
VITE_API_BASE=http://127.0.0.1:8000
VITE_WS_BASE=ws://127.0.0.1:8000
```

## Contracts

- Auth and settings: `/api/auth/*`, `/api/settings`
- Sessions: `/api/exercise/session/start`, `/api/exercise/session/end`, `/api/exercise/history`
- Analytics: `/api/reports/summary`, `/api/reports/progress`
- Local AI Coach: `/api/chat`, `/api/chat/status`
- Realtime: `WS /ws/inference?token=...` or `WS /ws/exercise/{session_id}?token=...`

The realtime UI only displays skeleton, recognition, tracking and rep information actually returned by the backend. Research Mode intentionally shows empty states until a real session supplies metadata.

## Theme

Light, dark and system modes use CSS design tokens. The preference is stored locally and also saved to authenticated user settings. Theme changes do not reload the page.

## Verification

```powershell
npm run lint
npm run build
```

Backend regression subset:

```powershell
cd D:\PhucHoiChucNangTay\rehabai
$env:PYTHONPATH = (Get-Location).Path
pytest -q tests\test_sessions.py tests\test_websocket_auth.py tests\test_chatbot_master.py
```

## Known limitations

- The production bundle reports a size warning; route-level code splitting is still recommended.
- Research Mode has no dedicated backend listing/export API yet and therefore does not invent research records.
- Session timeline currently records validated rep-counter changes in the active browser session; persisted repetition-event retrieval requires a backend endpoint.
- Existing database rows may contain `light`/`dark`; new settings also support `system`.
- This interface is supportive software, not a diagnosis or treatment system.
