# RAG / knowledge audit

Audit date: 2026-09-18  
Conclusion: `NOT_APPROVED_FOR_PRODUCTION`

## Inventory

| Path | Type | Production content | Result |
|---|---|---|---|
| `backend/knowledge/approved/.gitkeep` | placeholder | No | PASS |
| `backend/knowledge/metadata/schema.json` | metadata contract | No | PASS |
| `backend/knowledge/README.md` | review workflow | No | PASS |

The approved directory contains no knowledge document and no indexed production
content. Therefore there are no document duplicates, content hashes or versions
to validate, and no unapproved document is currently supplied to the model.
Runtime correctly reports `knowledge_version=none-unapproved`.

The schema requires `document_id`, `title`, `source`, `language`, `version`,
`scope`, `review_date`, `approval_status` and `content_hash`. It additionally
supports reviewer identity/role and expiry metadata. `review_status` remains an
optional compatibility field for old draft metadata; production approval is
determined only by `approval_status=approved`.

Production RAG remains disabled/empty until an authorized domain reviewer
approves real source material. Download success, model opinion or retrieval does
not grant approval.
