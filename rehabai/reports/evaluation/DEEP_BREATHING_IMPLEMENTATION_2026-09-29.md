# Deep Breathing implementation audit — 2026-09-29

## AUDIT

`DEEP_BREATHING` was not added to the trained model registry or the old
`/ws/inference` classifier flow. The public route remains informational and
does not request camera permission. The protected route is authenticated with
the existing JWT dependency and every session/event query is scoped to the
current user.

## IMPLEMENTED

- Guided timer with configurable inhale/hold/exhale/rest protocol.
- MediaPipe Pose shoulder visibility gate, calibration by median, torso/shoulder normalization, EMA smoothing, trend/derivative, outlier rejection, missing-frame handling, artifact heuristic and hysteresis-compatible rule engine.
- Explicit `IDLE`, `READY`, `INHALE`, `HOLD`, `EXHALE`, `REST`, `UNKNOWN`, `TRACKING_INSUFFICIENT`, `PAUSED`, `COMPLETED` phases.
- Cycle counter requires observed stable inhale and exhale evidence, good-frame coverage, duration limits and cooldown. Duplicate counts and long tracking gaps are guarded.
- Separate protected API and WebSocket: `/api/deep-breathing/*`, `/ws/deep-breathing/{session_id}`.
- Separate `deep_breathing_sessions` and `deep_breathing_events` persistence with no raw video.
- Timer-only fallback truthfully records `tracking_quality=UNAVAILABLE`; it never claims camera-observed cycles.
- Deep Breathing UI, pause/stop/retry, safety message, camera error handling, tracking quality and session history detail.
- Existing classifier WebSocket uses lazy MediaPipe initialization so malformed/auth-only connections do not initialize the graph.

## REUSED

Existing React/Vite shell, auth/JWT, SQLAlchemy session, Alembic, nginx WebSocket proxy, MediaPipe dependency and privacy/account export/delete flows.

## NEW_FILES

- `backend/deep_breathing/{__init__,config,types,signal,state_machine,analyzer}.py`
- `backend/api/deep_breathing.py`
- `migrations/versions/0006_deep_breathing.py`
- `frontend/src/pages/DeepBreathing.tsx`
- `tests/test_deep_breathing.py`

## CONFIG

All breathing durations and thresholds are in `DeepBreathingConfig` and can be
overridden with `REHABAI_BREATH_*` environment variables. Examples are present
in both `.env.example` files. No threshold is hidden in the UI component.

## ROUTES

- Public: `/exercises/deep-breathing` — information/CTA only, no camera.
- Protected: `/app/exercises/deep-breathing` and `/app/session/deep-breathing`.
- API: `/api/deep-breathing/config`, `/api/deep-breathing/sessions`, owned detail and finish endpoints.
- WebSocket: `/ws/deep-breathing/{session_id}`.

## STATE_MACHINE / SIGNAL_PIPELINE

`Pose landmarks → visibility gate → median baseline → torso/shoulder scale →
outlier rejection → EMA → multi-frame trend → guided timer phase → conservative
state transition → cycle closure`.

## FALLBACK

Camera denied/unavailable or MediaPipe failure switches to guided timer-only and
labels tracking unavailable. Ollama is not called by the engine and cannot stop
or alter phase/cycle logic.

## TESTS

- Backend full suite: **118 passed, 1 skipped**.
- Deep breathing unit/API/synthetic suite: **13 passed**.
- Frontend `npm run lint`: passed.
- Frontend `npm run build`: passed.
- HTTP smoke: auth → create → owned detail → timer-only finish passed; smoke
  account deleted afterward.
- Deployment migration: `0006_deep_breathing (head)`.
- Runtime health: `/api/health` returned 200; public and protected SPA shells
  returned 200 (protected API/session still requires JWT).

## PERFORMANCE

Local/container spot measurement (not a production benchmark): signal
processor ~4.77 µs/frame over 100,000 frames; Pose initialization ~16 ms and a
blank 640×480 frame ~95 ms on the current container CPU.

## KNOWN_LIMITATIONS / NOT_TESTED

- Real-user camera scenarios RC01–RC08 have not been executed here.
- Mobile browser/orientation, low-light and device-specific FPS/CPU/memory are
  not validated.
- Thresholds are conservative starting defaults, not clinical accuracy claims.
- The shoulder signal is an observation aid, not a respiratory measurement.
- Optional chest ROI/optical-flow phase 2 is not implemented.

## BLOCKED

No code blocker remains. Production camera readiness is **NOT_TESTED** until a
real camera session is exercised by the user on target devices.

## NEXT_STEPS

1. Open the deployed app, log in, choose `Hít thở sâu có hướng dẫn`.
2. Test one timer-only session and one camera session; verify history detail.
3. Run RC01–RC08 on the target laptop/phone and record FPS, latency, CPU and
   memory before tuning environment thresholds.

## FINAL_STATUS

Implemented and regression-tested as a non-clinical, no-training MVP. It is
ready for controlled user validation, not declared production-ready for real
camera accuracy until the listed tests are completed.
