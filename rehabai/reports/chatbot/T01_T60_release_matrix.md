# T01–T60 release evidence matrix

Date: 2026-09-18  
Overall: `INCOMPLETE`

The reviewer document supplies scenario names and expected behavior for T01–T60,
but it does not provide a complete frozen request/context fixture and objective
oracle for every case. The release prompt explicitly forbids inventing that
missing specification. Therefore this file records the actual evidence boundary
instead of fabricating 60 PASS results.

## Evidence classification

| Range | Specification status | Execution status | Release result |
|---|---|---|---|
| T01–T07 Language | Scenario/expectation available; frozen requests absent | Partial real smoke only (VI/EN) | NOT_RUN as full range |
| T08–T12 Emotional | Scenario/expectation available; human oracle required | Not run as frozen suite | NOT_RUN |
| T13–T18 Nutrition | Approved knowledge unavailable | Blocked | BLOCKED |
| T19–T29 Session/movement | Real owned fixtures required per case | Automated ownership/grounding subset exists | NOT_RUN as full range |
| T30–T34 Safety | Scenario/expectation available; professional review required | Automated deterministic subset exists | NEEDS_REVIEW |
| T35–T39 Security/RAG | RAG unavailable; security subset automated | Partial | NOT_RUN as full range |
| T40–T43 Output | Schema validator has automated tests | Partial | NOT_RUN as full range |
| T44–T50 Failure/deployment | Fallback and Docker-host connectivity tested; cold start not formally measured | Partial | NOT_RUN as full range |
| T51–T55 Performance | Real-camera protocol/criteria and run missing | Blocked | BLOCKED |
| T56–T60 Regression | Version-change frozen comparisons missing | Full current regression passes, but change matrix not executed | NOT_RUN |

## Real release-verification evidence obtained

| Evidence | HTTP/provider/status/language | Result | Location |
|---|---|---|---|
| Production-like backend container → host Ollama tags | model `qwen2.5:7b` found | PASS | `docker_ollama_production_like.md` |
| Production-like backend container → host inference | response `OK` | PASS | `docker_ollama_production_like.md` |
| Containerized `/api/chat`, VI | `200 / ollama / ready / vi` | PASS | `docker_ollama_production_like.md` |
| Containerized `/api/chat`, EN | `200 / ollama / ready / en` | PASS | `docker_ollama_production_like.md` |
| Backend regression | `166 passed, 1 skipped` | PASS | `release_gate_final.md` |

No `reports/chatbot/evidence/Txx` folders were created because incomplete or
template-only records must not resemble production evidence. Human reviewers can
use `human_review_matrix.md` and `clinical_review.md` to generate the missing
real records.
