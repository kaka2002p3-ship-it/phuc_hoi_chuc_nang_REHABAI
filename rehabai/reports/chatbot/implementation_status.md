# RehabAI Companion — current audit state

Audit date: 2026-09-18  
Production runtime: `React → FastAPI → Ollama local → qwen2.5:7b`  
Reviewer/Codex is not a production dependency.

## Version evidence

| Item | Value | Status |
|---|---|---|
| Ollama | `0.34.1` | TESTED |
| Model tag | `qwen2.5:7b` | TESTED |
| Prompt | `master-vi-en-1.0` | TESTED |
| Schema | `1.0` | TESTED |
| Knowledge | `none-unapproved` | TESTED |
| Backend | FastAPI application `1.0.0`; commit unknown because Git CLI is unavailable | UNKNOWN |

## CURRENT AUDIT STATE

| Area | Audit state | Evidence | Remaining issue / action |
|---|---|---|---|
| Backend regression | PASS | `pytest -q`: 166 passed, 1 skipped | Skipped test is not counted as PASS |
| Chat API | PASS | authenticated API tests and real local Ollama smoke | Full T01–T60 frozen run is not complete |
| Authentication | PASS | automated auth tests | — |
| Ownership/privacy | PASS | cross-user conversation and session tests | Continue security review before public release |
| Structured JSON | PASS | strict schema and invalid evidence tests | Semantic correctness still needs content review |
| Exercise grounding | PASS for implemented contract | context reads owned DB values; unsupported exercise IDs rejected | Frame-level tracking state is not persisted, so it reports `unknown` |
| Safety rules | PASS for automated cases | pre-LLM safety, English templates, accentless Vietnamese and normal-sadness regression | Human safety wording review required |
| Vietnamese | NOT_TESTED | automated prompt/safety checks only | Human naturalness review and full matrix required |
| English | NOT_TESTED | real `/api/chat` smoke returned Ollama `ready/en`; automated safety checks pass | Human naturalness review and full matrix required |
| Emotional support | NOT_TESTED | prompt exists; no complete human-reviewed output set | Run T08–T12 with human reviewer |
| Nutrition | BLOCKED | `knowledge_version=none-unapproved` | Approve sources before enabling grounded nutrition claims |
| Approved RAG | BLOCKED | workflow/schema implemented; approved directory empty | Domain reviewer must approve source content |
| Conversation controls | PASS | owned list/detail/delete API and UI; tests | UX human test remains |
| Long-term memory | NOT_APPLICABLE | endpoint explicitly reports disabled | Must not claim permanent memory |
| Ollama failure | PASS for unavailable/invalid-output fallback | automated fallback tests | Crash during active camera session not measured |
| No cloud fallback | PASS by code/config inspection | no cloud model references in backend/deployment/release/env example; fallback disabled | Repeat on frozen release artifact |
| Docker prompt/runtime | PASS | release-verification image builds and starts; migrations 0001–0004 pass | — |
| Docker → Ollama | PASS | container DNS, `/api/tags`, direct inference and authenticated VI/EN `/api/chat` | Re-run on frozen release artifact |
| Camera + Ollama performance | NOT_TESTED | no measured A–F baseline | Run T51–T55 and record FPS/latency/resources |
| Human bilingual review | NOT_TESTED | no signed review evidence | Required Gate B |
| Clinical/content review | NOT_TESTED | no professional review evidence | Required Gate B |
| Fine-tuning | NOT_APPLICABLE | prompt/context integration only | Do not claim fine-tuned |

## Defects resolved in audit iteration 1

| Defect | Severity | Error class | Resolution evidence |
|---|---|---|---|
| English safety input returned Vietnamese template | HIGH | LANGUAGE_ERROR / SAFETY_ERROR | bilingual deterministic templates and regression test |
| Accentless Vietnamese self-harm wording could bypass screening | HIGH | SAFETY_ERROR | Unicode folding and regression test |
| Session context asserted tracking was available without stored evidence | HIGH | CONTEXT_ERROR / DATA_ERROR | default changed to `unknown`; only persisted allowed status is used |
| Ollama 404/model missing was merged into generic timeout | MEDIUM | BACKEND_ERROR | HTTP 404 maps to `MODEL_UNAVAILABLE` |
| Chat context could include exercise outside IDs 2/4 | HIGH | CONTEXT_ERROR | backend rejects unsupported session exercise IDs |
| Knowledge metadata omitted reviewer-required fields | MEDIUM | RAG_ERROR | required `version`, `review_date`, `content_hash` added |
| Explicit English preference could receive output tagged Vietnamese | MEDIUM | LANGUAGE_ERROR / MODEL_ERROR | backend rejects language mismatch; real smoke falls back in English with `INVALID_MODEL_OUTPUT` |

## Release gates

| Gate | State | Reason |
|---|---|---|
| Gate A — Software/automated | NOT_TESTED | Baseline and Docker runtime pass, but complete T01–T60 frozen evidence is incomplete |
| Gate B — Human content | BLOCKED | Bilingual, safety, nutrition and health wording reviews have not occurred |
| Gate C — System performance | BLOCKED | Camera/Ollama measurements T51–T55 do not exist |

## Highest-priority next actions

1. Run the frozen T01–T50 matrix against the real `/api/chat`, storing actual output and versions in the reviewer record format.
2. Obtain bilingual and domain review for safety/emotional/nutrition content; do not self-approve knowledge.
3. Measure camera-only, Ollama-idle, active generation, cold start, concurrency and crash scenarios T51–T55.
4. Execute the remaining frozen T01–T60 records after fixtures/oracles and reviewers are available.
5. Re-run full regression on the frozen release artifact and record an application commit/digest.

## CURRENT RELEASE STATE

`BLOCKED_BY_HUMAN_REVIEW`

The system is not a release candidate and is not claimed to be medical-grade, fine-tuned or clinically validated. Knowledge review and performance are additional independent blockers.
