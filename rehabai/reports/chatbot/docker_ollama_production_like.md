# Production-like Docker → Ollama verification

Date: 2026-09-18  
Status: `PASS`

## Topology tested

`Host test client → backend Docker container :18000 → host.docker.internal:11434 → Ollama host → qwen2.5:7b`

The image `rehabai-backend:release-verification` was built from
`backend/Dockerfile`. The container used the packaged prompt, a read-only real
movement-model artifact mount, temporary SQLite migrated through revision 0004,
`OLLAMA_BASE_URL=http://host.docker.internal:11434`, and cloud fallback disabled.
It was stopped after the test; temporary database state was not retained.

## Evidence

| Check | Actual result | Status |
|---|---|---|
| DNS from backend image | `host.docker.internal → 192.168.65.254` | PASS |
| `/api/tags` from backend image | `qwen2.5:7b` present | PASS |
| Model digest | `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` | PASS |
| Direct inference from backend image | output `OK` | PASS |
| Container startup/migrations | Alembic 0001 → 0004; Uvicorn started | PASS |
| `/api/chat/status` | `provider=ollama-local`, `model=qwen2.5:7b`, `assistant_status=ready` | PASS |
| Authenticated VI `/api/chat` | HTTP 200, `provider=ollama`, `status=ready`, `language=vi` | PASS |
| Authenticated EN `/api/chat` | HTTP 200, `provider=ollama`, `status=ready`, `language=en` | PASS |
| Runtime cloud dependency | none found in backend/config inspection | PASS |

This verifies backend-container connectivity and real chat inference. It does not
substitute for the blocked real-camera performance gate.
