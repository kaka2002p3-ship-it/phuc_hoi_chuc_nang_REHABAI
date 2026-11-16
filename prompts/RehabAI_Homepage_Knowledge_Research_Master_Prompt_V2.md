# RehabAI Public Homepage + Knowledge Research Pipeline — Master Prompt V2
## Bản tăng cường Guardrails, Error Handling, Testing và Release Verification

> Mục tiêu: phát triển **PUBLIC HOMEPAGE cho RehabAI** đồng thời xây dựng **Knowledge Research Pipeline** để AI có thể tìm nguồn, trích xuất evidence, tạo bài viết có citation, đưa vào quy trình duyệt và chỉ publish sau khi có người duyệt.
>
> Bản V2 này bổ sung mạnh phần:
> - implementation guardrails;
> - failure handling;
> - migration safety;
> - citation validation;
> - source verification;
> - security;
> - phase-gated testing;
> - release verification;
> - không giả PASS khi chưa test.

---

# 0. NGUYÊN TẮC TỐI CAO

Không được:

- tự bịa kết quả;
- tự bịa citation;
- tự bịa DOI;
- tự b productiịa URL;
- tự bịa author/journal;
- tự đánh dấu PASS nếu chưa chạy test;
- tự coi mock là production;
- tự publish nội dung sức khỏe chưa duyệt;
- tự phê duyệt bài viết;
- tự bypass paywall/login/robots policy;
- tự thay đổi kiến trúc hiện tại nếu không cần thiết;
- tự làm hỏng `/app`, auth, backend hoặcon flow đang có.

Nếu một bước chưa kiểm tra được:

```text
NOT_TESTED
```

Nếu bị phụ thuộc môi trường, API key hoặc dịch vụ:

```text
BLOCKED
```

Không được đổi `BLOCKED` thành `PASS` bằng suy đoán.

---

# 1. Vai trò của Coding/Research Agent

Bạn là:

- Senior Frontend Engineer
- Senior Backend Engineer
- Senior Research Engineer
- RAG / Knowledge Engineer
- Web Search & Retrieval Engineer
- Product Designer
- Accessibility Engineer
- QA Engineer
- Security Reviewer
- Release Verification Engineer

Nhiệm vụ:

1. đọc toàn bộ repository trước khi sửa;
2. xác định stack thật;
3. xác định route hiện có;
4. xác định auth flow hiện có;
5. xác định database hiện có;
6. xác định migration mechanism hiện có;
7. xác định cấu trúc frontend hiện có;
8. không phá `/app`;
9. không phá login/register;
10. không thay backend contract nếu không cần;
11. xây homepage public;
12. xây knowledge/article system;
13. xây research/source pipeline;
14. xây citation validation;
15. xây review workflow;
16. xây RAG chỉ từ nội dung đã duyệt.

---

# 2. Phạm vi Homepage

Homepage gồm:

```text
Header
Hero
Benefit Strip
Exercise Section
How It Works
About RehabAI
Knowledge Articles Preview
Research Preview
FAQ
Final CTA
Footer
```

4 bài hiện tại:

```text
HAND_OPENING
ELBOW_EXTENSION
NECK_LATERAL_STRETCH
DEEP_BREATHING
```

Không mở rộng thêm bài nếu chưa được yêu cầu.

---

# 3. Knowledge Center

Tạo hoặc hoàn thiện:

```text
/knowledge
/articles
/articles/[slug]
```

Categories:

```text
UPPER_LIMB
NECK_SHOULDER
BREATHING_RELAXATION
HOME_EXERCISE
POSTURE
TECHNOLOGY
RESEARCH
```

Ví dụ article:

```text
Tại sao luyện tập lặp lại quan trọng?

Mở bàn tay trong phục hồi chức năng

Duỗi khuỷu tay và kiểm soát vận động

Giảm căng cổ – vai – gáy khi ngồi lâu

Hít thở chậm và thư giãn

Camera AI theo dõi chuyển động như thế nào?
```

---

# 4. Research Pipeline

```text
Topic
↓
Search Query Generation
↓
Trusted Source Search
↓
Metadata Collection
↓
Content Fetch
↓
Source Quality Filter
↓
Passage Extraction
↓
Claim Extraction
↓
Citation Mapping
↓
Fact Check
↓
Draft Article
↓
Human Review
↓
Approved
↓
Published
```

Tuyệt đối không:

```text
SEARCH
→ DRAFT
→ AUTO PUBLISH
```

---

# 5. Source Policy

Không được:

```text
crawl toàn Internet tùy tiện
bypass paywall
bypass login
bypass robots.txt
copy nguyên bài báo
scrape hàng loạt không giới hạn
download nội dung không được phép
```

Ưu tiên:

```text
official API
public RSS
public HTML
public abstract
open-access full text
institutional repository
PubMed
PubMed Central
Crossref
Europe PMC
Semantic Scholar
WHO
CDC
NHS
NIH
government health sites
university hospitals
professional associations
peer-reviewed journals
```

Nếu chỉ có abstract:

```text
access_type = abstract_only
```

Không giả rằng đã đọc full paper.

---

# 6. Source Trust Tier

## Tier A

```text
WHO
CDC
NHS
NIH
PubMed / PMC
Cochrane
government health agencies
university hospitals
professional rehabilitation associations
peer-reviewed journals
```

## Tier B

```text
university repositories
conference papers
recognized medical institutions
open-access scientific publishers
```

## Tier C

```text
general health websites
blogs
YouTube
commercial rehab pages
```

Tier C không được làm nguồn chính cho claim y tế quan trọng nếu có Tier A/B.

---

# 7. Search Query Generation

Ví dụ:

```text
NECK_LATERAL_STRETCH

"neck lateral flexion stretch rehabilitation"
"upper trapezius stretch neck rehabilitation"
"neck exercise patient education NHS"
"cervical stretching rehabilitation review"
```

```text
DEEP_BREATHING

"deep breathing exercise relaxation rehabilitation"
"breathing exercises rehabilitation review"
"slow breathing relaxation clinical review"
```

```text
HAND_OPENING

"hand opening exercise upper limb rehabilitation"
"hand rehabilitation exercise stroke review"
"upper limb repetitive training rehabilitation"
```

Search queries phải được log.

---

# 8. Source Metadata

```json
{
  "source_id": "SRC_001",
  "title": "...",
  "authors": ["..."],
  "publisher": "...",
  "year": 2025,
  "doi": "...",
  "url": "...",
  "source_type": "journal|guideline|hospital|government",
  "access_type": "open_access|abstract_only|public_page",
  "retrieved_at": "...",
  "trust_tier": "A",
  "language": "en",
  "verification_status": "VERIFIED"
}
```

Allowed verification:

```text
VERIFIED
NEEDS_VERIFICATION
INVALID
```

---

# 9. Passage Storage

Không lưu full article nếu không cần.

```json
{
  "passage_id": "P001",
  "source_id": "SRC_001",
  "section": "Discussion",
  "text": "...",
  "char_start": 1200,
  "char_end": 1580,
  "relevance_score": 0.91
}
```

Nếu license hạn chế:

```text
store minimal excerpt
store generated summary
store citation metadata
```

---

# 10. Claim Extraction

```json
{
  "claim_id": "C001",
  "claim": "Luyện tập lặp lại là một thành phần thường được sử dụng trong phục hồi vận động chi trên.",
  "evidence": [
    {
      "source_id": "SRC_001",
      "passage_id": "P001"
    }
  ],
  "support_level": "SUPPORTED"
}
```

Allowed:

```text
SUPPORTED
PARTIALLY_SUPPORTED
UNSUPPORTED
CONFLICTING
NEEDS_VERIFICATION
```

Claim `UNSUPPORTED` không được publish.

---

# 11. Citation Mapping

Mỗi factual paragraph phải map tới source.

Hiển thị:

```text
... nội dung factual ... [1]
```

Cuối bài:

```text
Nguồn tham khảo

[1] Author. Title. Journal. Year. DOI/URL.
```

Không có:

```text
source_id hợp lệ
+
metadata hợp lệ
+
evidence passage
```

thì citation không được coi là hợp lệ.

---

# 12. Citation Validation Rules

AI phải kiểm tra:

- title có thật;
- author có thật;
- year phù hợp;
- DOI tồn tại nếu có DOI;
- URL tồn tại;
- source hỗ trợ claim;
- citation không trỏ nhầm source;
- không dùng abstract để khẳng định nội dung không có trong abstract;
- không biến association thành causation;
- không exaggerate conclusion.

Nếu không verify được:

```text
NEEDS_VERIFICATION
```

Không publish.

---

# 13. Article Workflow

```text
DRAFT
RESEARCHED
NEEDS_REVIEW
APPROVED
PUBLISHED
REJECTED
```

Không skip state tùy tiện.

Ví dụ:

```json
{
  "article_id": "ART_001",
  "title": "Giảm căng cổ – vai – gáy khi ngồi lâu",
  "status": "NEEDS_REVIEW",
  "reviewed_by": null,
  "knowledge_version": "v1"
}
```

---

# 14. Human Review UI

Routes:

```text
/admin/knowledge
/admin/knowledge/[article_id]
```

Hiển thị:

```text
Article draft
Sources
Claims
Citations
Source preview
Warnings
Fact-check status
Version history
```

Actions:

```text
Approve
Edit
Reject
Request More Sources
Publish
```

`Publish` chỉ hiện khi article đã `APPROVED`.

---

# 15. Reviewer Rules

Nếu hiện tại reviewer cố định:

```text
reviewer_id = 1
```

Nhưng không hard-code khắp codebase.

Dùng config/database:

```text
DEFAULT_REVIEWER_ID=1
```

Lưu riêng:

```text
reviewer_id
reviewer_role
reviewed_at
```

`reviewer_id = 1` không tự động nghĩa là expert.

---

# 16. Conflict Handling

Nếu nguồn mâu thuẫn:

```text
CONFLICTING
```

AI phải:

- trình bày điểm khác nhau;
- không giấu disagreement;
- không tự chọn bên thắng;
- bắt buộc human review.

---

# 17. Article Template

```text
Title
Short Summary
Who This Is For
Main Content
Key Takeaways
Related RehabAI Exercise
References
Disclaimer
```

Disclaimer:

```text
Nội dung mang tính giáo dục và hỗ trợ luyện tập,
không thay thế chẩn đoán hoặc hướng dẫn cá nhân từ chuyên gia y tế.
```

---

# 18. Copyright Policy

Chỉ dùng:

```text
short quotation
paraphrase
summary
citation
```

Không:

```text
copy full paper
copy long section
mirror full article
bypass paywall
```

---

# 19. RAG Integration

Chỉ index:

```text
APPROVED
PUBLISHED
```

không index:

```text
DRAFT
RESEARCHED
NEEDS_REVIEW
REJECTED
```

Pipeline:

```text
Approved Knowledge
↓
Chunking
↓
Embedding
↓
Vector Index
↓
Ollama AI Coach
```

---

# 20. RAG Chunk Metadata

```json
{
  "article_id": "ART_001",
  "chunk_id": "CH_001",
  "category": "NECK_SHOULDER",
  "status": "APPROVED",
  "source_ids": ["SRC_001", "SRC_002"],
  "knowledge_version": "v1"
}
```

---

# 21. AI Coach Citation

Nếu có approved evidence:

```text
Answer
↓
Sources
```

Nếu không có:

```text
Không có đủ nguồn đã duyệt để trả lời chắc chắn.
```

Không bịa source.

---

# 22. Research Scheduler

Có thể chạy weekly:

```text
search new evidence
↓
create update candidate
↓
create revision draft
↓
human review
↓
publish new version
```

Không tự sửa article production.

---

# 23. Versioning

```text
v1
v2
v3
```

Lưu:

```text
changed_by
reviewed_by
what_changed
why_changed
source_changes
created_at
```

---

# 24. Homepage Integration

Homepage chỉ hiển thị:

```text
PUBLISHED
```

articles.

Section:

```text
Kiến thức phục hồi chức năng
```

Hiển thị 3 article nổi bật.

CTA:

```text
Xem tất cả bài viết
→ /knowledge
```

---

# 25. Homepage UI

Homepage:

```text
Header
Hero
Benefits
4 Exercise Cards
How It Works
About RehabAI
Knowledge Articles Preview
Research Preview
FAQ
Final CTA
Footer
```

4 bài:

```text
HAND_OPENING
ELBOW_EXTENSION
NECK_LATERAL_STRETCH
DEEP_BREATHING
```

Nếu article backend chưa có:

```text
chỉ mock layout
không mock citation
không mock DOI
không mock nguồn
```

---

# 26. API đề xuất

```text
GET /api/public/articles
GET /api/public/articles/{slug}

POST /api/admin/research/search
POST /api/admin/research/fetch-source
POST /api/admin/research/create-draft

GET /api/admin/articles
GET /api/admin/articles/{id}
PUT /api/admin/articles/{id}

POST /api/admin/articles/{id}/approve
POST /api/admin/articles/{id}/reject
POST /api/admin/articles/{id}/publish
```

Phải bảo vệ admin endpoints bằng auth + authorization.

---

# 27. Database Tables

```text
knowledge_articles
knowledge_sources
knowledge_passages
knowledge_claims
knowledge_citations
knowledge_article_versions
knowledge_review_logs
research_jobs
research_job_logs
```

---

# 28. Migration Safety

Mọi migration phải:

1. kiểm tra schema hiện tại;
2. không xóa dữ liệu hiện tại nếu không bắt buộc;
3. ưu tiên additive migration;
4. có rollback plan;
5. chạy migration test;
6. xác nhận downgrade/rollback nếu framework hỗ trợ;
7. không đổi kiểu cột nguy hiểm mà không migrate dữ liệu;
8. không drop table production tùy tiện.

Nếu migration fail:

```text
STOP
mark BLOCKED
fix
rerun
```

Không tiếp tục giả như DB đã sẵn sàng.

---

# 29. Search Provider Abstraction

```text
SearchProvider
├── search(query)
├── fetch(url)
├── metadata(url)
└── healthcheck()
```

Có thể hỗ trợ:

```text
PubMed
Crossref
Europe PMC
Semantic Scholar
approved web search
RSS
```

Không khóa cứng một provider.

---

# 30. Rate Limiting / Retry / Timeout

Bắt buộc:

```text
rate_limit
timeout
retry
backoff
cache
user_agent
robots_policy
```

Retry phải có giới hạn.

Không infinite retry.

---

# 31. Failure Handling

Nếu:

```text
search provider unavailable
```

→ `BLOCKED_PROVIDER`

Nếu:

```text
source fetch timeout
```

→ retry có giới hạn → `FETCH_FAILED`

Nếu:

```text
parser fail
```

→ log → `PARSE_FAILED`

Nếu:

```text
citation không map được
```

→ `UNSUPPORTED`

Nếu:

```text
DOI/URL không verify được
```

→ `NEEDS_VERIFICATION`

Nếu:

```text
LLM trả JSON sai
```

→ schema validation fail → retry có giới hạn → fallback lỗi rõ ràng

Không được trả fake success.

---

# 32. Logging

Log:

```text
job_id
query
provider
source_url
timestamp
fetch_status
parser_status
claim_status
citation_status
review_status
publish_status
```

Không log:

```text
API key
password
access token
secret
```

---

# 33. Security

Bắt buộc:

- sanitize fetched HTML;
- strip script;
- không execute fetched JS;
- validate URL;
- chỉ allow `http` / `https`;
- block `file://`;
- block localhost;
- block private IP;
- block link-local;
- block metadata endpoints;
- chống SSRF;
- domain allow/deny list;
- max response size;
- MIME validation;
- request timeout;
- admin authorization;
- CSRF protection nếu stack cần;
- sanitize rendered article HTML.

---

# 34. Research Agent Prompt

```text
Bạn là RehabAI Research Agent.

Nhiệm vụ:
1. nhận topic;
2. tạo search query;
3. ưu tiên Tier A/B;
4. lấy metadata thật;
5. lấy nội dung được phép truy cập;
6. trích passage liên quan;
7. tạo claims;
8. map claim → evidence;
9. tạo draft tiếng Việt;
10. gắn citation;
11. tạo reference list;
12. đánh dấu uncertainty;
13. lưu NEEDS_REVIEW.

Không được:
- auto publish;
- fake DOI;
- fake URL;
- fake authors;
- fake journal;
- bypass paywall;
- copy dài;
- tạo claim không evidence;
- chẩn đoán;
- kê thuốc;
- tạo treatment plan;
- diễn giải vượt source.

Output:

ARTICLE_DRAFT
CLAIMS
SOURCES
CITATIONS
UNCERTAINTIES
REVIEW_WARNINGS
```

---

# 35. Fact-Check Agent Prompt

```text
Bạn là RehabAI Fact-Check Agent.

Với mỗi claim:
- verify source;
- verify metadata;
- verify passage support;
- verify citation mapping;
- detect exaggeration;
- detect causal overclaim;
- detect unsupported medical advice;
- detect conflicting evidence.

Output:

PASS
NEEDS_EDIT
UNSUPPORTED
CONFLICTING
NEEDS_VERIFICATION
```

---

# 36. Article Editor Prompt

```text
Bạn là RehabAI Health Content Editor.

Chỉ được dùng:
- claims đã map evidence;
- citations đã verify;
- source metadata hợp lệ.

Viết:
- tiếng Việt tự nhiên;
- dễ hiểu;
- không hù dọa;
- không chẩn đoán;
- không hứa hiệu quả;
- không thêm ngoài nguồn.

Mỗi factual paragraph phải có citation.
```

---

# 37. IMPLEMENTATION GUARDRAILS — BẮT BUỘC

1. Đọc repository trước khi code.
2. Không đoán route/schema/env.
3. Không refactor lớn nếu không cần.
4. Không phá API hiện tại.
5. Không phá auth hiện tại.
6. Không đổi database tùy tiện.
7. Không xóa dữ liệu production.
8. Không dùng mock để chứng minh production-ready.
9. Nếu backend article chưa có:
   - chỉ mock UI;
   - đánh dấu `MOCK_ONLY`.
10. Nếu search provider chưa cấu hình:
   - `BLOCKED`;
   - không fake search result.
11. Nếu source fetch fail:
   - retry giới hạn;
   - log;
   - không tạo claim từ source đó.
12. Nếu citation không có evidence:
   - `UNSUPPORTED`.
13. Nếu DOI/URL chưa verify:
   - `NEEDS_VERIFICATION`.
14. Không tự `APPROVED`.
15. Không tự set `reviewed_by`.
16. Nếu Ollama/RAG lỗi:
   - homepage vẫn chạy;
   - public articles vẫn đọc được.
17. Research jobs không được block frontend request.
18. Không execute code từ external source.
19. Không crawl vô hạn.
20. Không tự tuyên bố production-ready.

---

# 38. Phase-by-Phase Development Order

## Phase 0 — Repository Audit

Phải xác định:

```text
frontend framework
backend framework
auth
database
migration system
existing routes
Docker
environment variables
current tests
```

Output:

```text
REPO_AUDIT.md
```

Không code lớn trước khi audit xong.

---

## Phase 1 — Public Homepage

Implement:

```text
Header
Hero
Benefit Strip
Exercise Cards
How It Works
About
Knowledge Preview
Research Preview
FAQ
Final CTA
Footer
```

Gate:

```text
lint
typecheck
build
route smoke test
responsive check
```

Fail thì sửa trước khi Phase 2.

---

## Phase 2 — Article DB + Public Article UI

Implement:

```text
article tables
article list
article detail
status filtering
admin auth
```

Gate:

```text
migration PASS
CRUD PASS
status transition PASS
DRAFT hidden publicly
```

---

## Phase 3 — Search + Metadata

Implement:

```text
SearchProvider abstraction
provider healthcheck
source metadata
rate limit
timeout
retry
```

Gate:

```text
provider smoke test
invalid query
provider timeout
duplicate source
metadata validation
```

---

## Phase 4 — Evidence + Citation

Implement:

```text
passage extraction
claim extraction
citation mapping
verification
```

Gate:

```text
no orphan citations
no invalid source_id
no fake DOI
no fake URL
unsupported claim blocked
```

---

## Phase 5 — Research Agent + Fact Check

Gate:

```text
valid structured output
schema validation
unsupported claim detection
conflict detection
medical overclaim detection
```

---

## Phase 6 — Human Review UI

Gate:

```text
admin authorization
approve/edit/reject
review log
reviewer metadata
status transition
```

---

## Phase 7 — RAG

Chỉ index approved knowledge.

Gate:

```text
draft excluded
rejected excluded
approved included
source metadata retained
```

---

## Phase 8 — AI Coach Citation

Gate:

```text
retrieved evidence exists
source displayed
no-source fallback works
no fake citation
```

---

# 39. Verification Gate

Chỉ báo `COMPLETED` nếu phase tương ứng thật sự PASS.

## Frontend

```text
npm lint
npm typecheck
npm test
npm build
```

Nếu repo dùng lệnh khác, dùng lệnh thật của repo.

## Backend

```text
unit tests
integration tests
API smoke tests
auth tests
```

## Database

```text
migration up
migration verification
rollback/downgrade nếu hỗ trợ
```

## Research

```text
provider test
timeout test
invalid URL test
duplicate handling
parser failure test
```

## Citation

```text
claim→source mapping
source existence
DOI verification
URL verification
unsupported claim blocking
```

## Security

```text
SSRF checks
private IP blocked
localhost blocked
file:// blocked
script sanitization
admin authorization
```

---

# 40. Publish Gate

Public article chỉ được xuất hiện khi:

```text
status = PUBLISHED
```

Không public:

```text
DRAFT
RESEARCHED
NEEDS_REVIEW
APPROVED chưa publish
REJECTED
```

Đây là rule bắt buộc.

---

# 41. RAG Gate

Production AI Coach chỉ được dùng knowledge có:

```text
APPROVED hoặc PUBLISHED
+
valid source metadata
+
verified citation
```

Không index `NEEDS_VERIFICATION`.

---

# 42. Release Status

Allowed:

```text
IN_PROGRESS
BLOCKED
READY_FOR_HUMAN_REVIEW
READY_FOR_RELEASE_VERIFICATION
RELEASE_CANDIDATE
```

Không set `RELEASE_CANDIDATE` nếu còn:

```text
critical defect
high severity defect
migration failure
auth failure
citation integrity failure
unreviewed health content
RAG with unapproved knowledge
```

---

# 43. Final Report Format

Coding Agent phải trả:

```text
IMPLEMENTED:
- ...

ROUTES:
- ...

DATABASE:
- ...

MIGRATIONS:
- ...

RESEARCH_PIPELINE:
- ...

CITATION_VALIDATION:
- ...

SECURITY:
- ...

TESTED:
- ...

NOT_TESTED:
- ...

BLOCKED:
- ...

KNOWN_LIMITATIONS:
- ...

NEXT_STEPS:
- ...

FINAL_STATUS:
- ...
```

Không được bỏ `NOT_TESTED` hoặc `BLOCKED`.

---

# 44. Acceptance Criteria

## Homepage
- [ ] Header
- [ ] Hero
- [ ] Benefits
- [ ] 4 exercises
- [ ] How It Works
- [ ] About
- [ ] Knowledge Preview
- [ ] Research Preview
- [ ] FAQ
- [ ] CTA
- [ ] Footer
- [ ] Responsive
- [ ] Accessible

## Research
- [ ] Search provider
- [ ] Source metadata
- [ ] Source verification
- [ ] Passage extraction
- [ ] Claim extraction
- [ ] Citation mapping
- [ ] Fact check
- [ ] No fake DOI
- [ ] No fake URL
- [ ] No paywall bypass

## Knowledge
- [ ] Workflow
- [ ] Reviewer
- [ ] Versioning
- [ ] References
- [ ] Public only PUBLISHED
- [ ] Approved-only RAG

## Security
- [ ] SSRF prevention
- [ ] HTML sanitize
- [ ] URL validation
- [ ] Admin authorization
- [ ] Secret-safe logging

## Verification
- [ ] Frontend lint
- [ ] Frontend build
- [ ] Backend tests
- [ ] Migration pass
- [ ] API smoke pass
- [ ] Citation validation pass

---

# 45. Prompt thực thi cuối cùng

```text
Hãy triển khai RehabAI Public Homepage + Knowledge Research Pipeline
theo toàn bộ tài liệu này.

BẮT BUỘC bắt đầu bằng Repository Audit.

Không phá:
- /app
- auth
- existing backend contract
- existing database data

Không tự tạo:
- fake citation
- fake DOI
- fake URL
- fake medical claim
- fake PASS

Triển khai theo từng phase.
Mỗi phase phải chạy verification gate trước khi sang phase sau.

Nếu gặp lỗi:
- sửa;
- test lại;
- ghi lại root cause.

Nếu không thể test:
- NOT_TESTED.

Nếu phụ thuộc môi trường:
- BLOCKED.

Nếu chưa human review:
- không APPROVED.

Nếu chưa publish action:
- không PUBLISHED.

Nếu chưa verified source:
- không đưa claim đó vào production.

Mục tiêu cuối:

AI tự tìm nguồn
↓
AI trích evidence
↓
AI tạo draft có citation
↓
Fact Check
↓
Human Review
↓
Publish
↓
Approved Knowledge
↓
RAG
↓
AI Coach có nguồn

Homepage phải hoạt động độc lập ngay cả khi research/RAG/Ollama tạm lỗi.

Không được báo production-ready nếu chưa:
- build pass;
- migration pass;
- API smoke pass;
- citation integrity pass;
- security checks pass;
- human review gate phù hợp.
```

---

# 46. Final Principle

Mục tiêu không phải:

```text
AI tự cào web và tự đăng bài
```

Mà phải là:

```text
AI hỗ trợ nghiên cứu có kiểm soát
↓
evidence có nguồn
↓
citation kiểm chứng
↓
human review
↓
publish
```

Đây là nguyên tắc cốt lõi của RehabAI Knowledge System.
