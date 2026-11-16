# RehabAI Local AI Data Collection & Training Corpus Master Prompt
## Mục tiêu: xây dựng dữ liệu cho AI local theo hướng an toàn, tự nhiên và hữu ích

> Dùng prompt này cho Coding/Research Agent để xây pipeline thu thập dữ liệu, làm sạch, phân loại, tạo corpus và chuẩn bị dữ liệu huấn luyện/RAG cho AI local của RehabAI.
>
> Mục tiêu không phải là “crawl càng nhiều càng tốt”.
> Mục tiêu là:
>
> ```text
> dữ liệu hợp pháp
> + có nguồn
> + đúng phạm vi
> + sạch
> + có metadata
> + được review
> + phù hợp cho RAG / fine-tuning
> ```

---

# 0. BỐI CẢNH

Project:

```text
RehabAI
```

AI local hiện dùng Ollama/local LLM.

AI local cần hỗ trợ 4 nhóm nội dung chính:

```text
1. REHAB / EXERCISE KNOWLEDGE
2. SOFTWARE / PRODUCT SUPPORT
3. GENERAL NUTRITION / WELLNESS
4. NATURAL CONVERSATION / ENGAGEMENT
```

Không trộn tất cả dữ liệu vào một tập duy nhất mà không có metadata.

---

# 1. NGUYÊN TẮC KIẾN TRÚC DỮ LIỆU

Tách corpus thành 4 tầng:

```text
knowledge/
├── rehab/
├── software/
├── nutrition/
└── safety/

conversation/
├── casual/
├── supportive/
├── product_help/
└── bilingual_vi_en/

training/
├── sft/
├── preference/
└── evaluation/
```

Không dùng raw crawled text trực tiếp để fine-tune.

Pipeline:

```text
Source Discovery
↓
License / Access Check
↓
Fetch
↓
Deduplicate
↓
Clean
↓
Chunk
↓
Classify
↓
Fact / Safety Filter
↓
Metadata
↓
Human Review
↓
Approved Corpus
↓
RAG and/or Training Dataset
```

---

# 2. ƯU TIÊN RAG TRƯỚC FINE-TUNING

Mặc định:

```text
Knowledge facts
→ RAG
```

Không ưu tiên nhồi toàn bộ kiến thức y tế/dinh dưỡng vào weights.

Fine-tuning chủ yếu dùng cho:

```text
tone
response structure
conversation style
tool-use discipline
product behavior
bilingual fluency
refusal / safety behavior
```

Không dùng fine-tuning để “ghi nhớ” toàn bộ tài liệu y tế.

---

# 3. DATA DOMAIN 1 — REHABILITATION KNOWLEDGE

Chủ đề:

```text
HAND_OPENING
ELBOW_EXTENSION
NECK_LATERAL_STRETCH
DEEP_BREATHING

upper limb rehabilitation
home exercise guidance
movement repetition
posture
neck / shoulder relaxation
breathing / relaxation
exercise adherence
progress tracking
general rehabilitation education
```

Nguồn ưu tiên:

```text
WHO
NHS
NIH
PubMed
PubMed Central
Cochrane
government health agencies
university hospitals
professional rehabilitation associations
peer-reviewed journals
```

Không dùng:

```text
random blogs
anonymous forums
unverified TikTok/short videos
AI-generated health articles
```

trừ khi chỉ dùng làm negative/example corpus.

---

# 4. DATA DOMAIN 2 — SOFTWARE / PRODUCT SUPPORT

Thu thập dữ liệu phục vụ chatbot hỗ trợ sử dụng RehabAI.

Chủ đề:

```text
login
register
password reset
profile
camera permission
camera not detected
camera blocked
poor lighting
body/hand outside frame
tracking lost
MediaPipe not detecting landmarks
browser permission
microphone permission if used
WebSocket disconnected
Ollama unavailable
AI Coach unavailable
slow response
session not saved
history not updated
progress not displayed
exercise selection
session start / stop
network issue
frontend loading
backend unavailable
500 error
401 / 403
timeout
Docker/local setup
local Ollama connection
```

Nguồn dữ liệu:

```text
RehabAI own documentation
actual UI copy
backend error messages
API docs
FAQ
support tickets if available and consented
internal bug reports
test cases
release notes
```

Không để chatbot bịa nguyên nhân kỹ thuật.

Rule:

```text
if actual system state unknown:
say what can be checked
do not invent root cause
```

---

# 5. SOFTWARE INTENT TAXONOMY

Dùng các intent:

```text
AUTH_LOGIN_HELP
AUTH_REGISTER_HELP
AUTH_PASSWORD_HELP

CAMERA_PERMISSION
CAMERA_NOT_FOUND
CAMERA_POOR_LIGHT
CAMERA_OUT_OF_FRAME

TRACKING_LOST
TRACKING_UNSTABLE

SESSION_START_HELP
SESSION_STOP_HELP
SESSION_SAVE_ERROR

HISTORY_NOT_FOUND
PROGRESS_NOT_UPDATED

AI_COACH_UNAVAILABLE
OLLAMA_UNAVAILABLE

NETWORK_ERROR
BACKEND_ERROR
WEBSOCKET_ERROR

GENERAL_PRODUCT_HELP
BUG_REPORT
FEATURE_EXPLANATION
```

Mỗi sample nên có:

```json
{
  "intent": "CAMERA_PERMISSION",
  "language": "vi",
  "user_text": "...",
  "assistant_response": "...",
  "requires_system_state": true,
  "safe_to_answer_without_state": false
}
```

---

# 6. DATA DOMAIN 3 — NUTRITION / WELLNESS

Phạm vi CHỈ là:

```text
general healthy eating
balanced meals
hydration
protein as a nutrient
fiber
fruit and vegetables
meal regularity
general nutrition education
healthy snack ideas
general eating habits
```

Không cho AI local tự:

```text
chẩn đoán
điều trị bệnh
kê thực đơn điều trị
đưa liều supplement
đưa kế hoạch giảm cân cực đoan
tư vấn cho bệnh đặc hiệu nếu thiếu chuyên gia
thay bác sĩ / dietitian
```

Nếu người dùng hỏi personalized medical nutrition:

```text
answer at general level
state limitation
encourage professional guidance when appropriate
```

---

# 7. NUTRITION SOURCE POLICY

Ưu tiên:

```text
WHO
NHS
government nutrition guidance
NIH
recognized dietetic associations
peer-reviewed reviews
```

Không ưu tiên:

```text
supplement marketing
fitness influencer claims
detox
miracle diet
fat-burning products
extreme fasting claims
```

---

# 8. DATA DOMAIN 4 — NATURAL CONVERSATION

Mục tiêu:

AI không cứng nhắc kiểu:

```text
"Xin chào. Tôi có thể hỗ trợ bạn."
```

lặp đi lặp lại.

Cần dataset về hội thoại tự nhiên:

```text
greetings
small talk
encouragement
session check-in
post-session conversation
frustration
hesitation
motivation
user confusion
short answers
long answers
mixed Vietnamese-English
Vietnamese without accents
casual phrasing
polite phrasing
elder-friendly phrasing
```

---

# 9. CONVERSATIONAL STYLE PRINCIPLES

AI nên:

```text
warm
natural
short when possible
context-aware
not overly cheerful
not robotic
not patronizing
not repetitive
```

Tránh:

```text
"Tuyệt vời!"
"Rất tốt!"
"Bạn đang làm rất tốt!"
```

sau mọi câu.

Không được tạo cảm giác phụ thuộc cảm xúc.

---

# 10. RESPONSE STYLE DATASET

Tạo nhiều biến thể cho cùng intent.

Ví dụ user:

```text
hôm nay tôi hơi mệt
```

Response variants:

```text
"Hôm nay mình có thể giữ buổi tập nhẹ hơn. Nếu bạn muốn, hãy bắt đầu với bài ngắn và dừng nếu thấy khó chịu."

"Nếu đang mệt, bạn có thể ưu tiên buổi tập ngắn và thoải mái hơn hôm nay."

"Mình hiểu. Bạn có thể tập nhẹ, hoặc chỉ xem lại hướng dẫn trước khi quyết định bắt đầu."
```

Không bắt model học đúng 1 câu duy nhất.

---

# 11. BILINGUAL DATA

Tạo data:

```text
Vietnamese
English
Mixed VI/EN
Vietnamese without accents
```

Ví dụ:

```text
"camera khong nhan tay cua toi"
"my camera cannot detect my hand"
"camera của tôi tracking hơi lag"
```

Phải map về cùng intent khi phù hợp.

---

# 12. DATA SOURCES CHO CONVERSATION

Ưu tiên:

```text
synthetic conversation generated from approved scenarios
human-written examples
actual anonymized support conversations if legally usable
product QA conversations
bug reports transformed into dialogues
```

Không scrape private chats.

Không thu dữ liệu cá nhân nhạy cảm.

---

# 13. SOURCE DISCOVERY AGENT

Research Agent phải:

1. nhận domain;
2. tạo search queries;
3. tìm nguồn hợp lệ;
4. kiểm tra license/access;
5. lấy metadata;
6. fetch phần public/allowed;
7. lưu provenance;
8. không bypass paywall;
9. không crawl vô hạn.

---

# 14. RAW SOURCE METADATA

```json
{
  "source_id": "SRC_001",
  "domain": "rehab",
  "title": "...",
  "publisher": "...",
  "authors": ["..."],
  "year": 2025,
  "url": "...",
  "doi": "...",
  "license": "...",
  "access_type": "public_page|open_access|abstract_only",
  "retrieved_at": "...",
  "trust_tier": "A",
  "status": "VERIFIED"
}
```

---

# 15. LEGAL / COPYRIGHT RULE

Không:

```text
copy entire copyrighted articles
republish full books
bypass paywall
ignore robots policy
store full text when license does not allow
```

Ưu tiên:

```text
metadata
short excerpt
summary
fact extraction
open-license full text
```

---

# 16. DEDUPLICATION

Phải loại:

```text
exact duplicate
near duplicate
mirror website
same article in multiple formats
syndicated copies
```

Có thể dùng:

```text
hash
MinHash
embedding similarity
title/DOI matching
```

---

# 17. DATA CLEANING

Loại:

```text
navigation text
cookie banners
ads
menus
footers
broken HTML
tracking script
duplicate references
OCR noise
```

Giữ:

```text
title
section
main text
source metadata
citation anchors
```

---

# 18. QUALITY LABELS

Mỗi item:

```text
HIGH
MEDIUM
LOW
REJECT
```

Theo:

```text
source trust
clarity
relevance
factual support
license
noise
duplication
```

Chỉ:

```text
HIGH
MEDIUM
```

được vào approved corpus.

---

# 19. KNOWLEDGE CHUNK SCHEMA

```json
{
  "chunk_id": "CHK_001",
  "domain": "rehab",
  "topic": "HAND_OPENING",
  "text": "...",
  "source_id": "SRC_001",
  "language": "en",
  "trust_tier": "A",
  "review_status": "APPROVED",
  "tags": ["upper_limb", "home_exercise"]
}
```

---

# 20. CONVERSATION SAMPLE SCHEMA

```json
{
  "sample_id": "CONV_001",
  "domain": "software",
  "intent": "CAMERA_PERMISSION",
  "language": "vi",
  "messages": [
    {
      "role": "user",
      "content": "Sao camera không chạy?"
    },
    {
      "role": "assistant",
      "content": "Bạn kiểm tra xem trình duyệt đã được cấp quyền camera chưa. Nếu đang bị chặn, hãy bật quyền camera cho RehabAI rồi tải lại trang."
    }
  ],
  "style": ["natural", "concise", "supportive"],
  "source": "synthetic_from_product_spec",
  "review_status": "APPROVED"
}
```

---

# 21. MULTI-TURN CONTEXT DATA

Không chỉ tạo single-turn.

Tạo:

```text
2-turn
4-turn
6-turn
8-turn
```

Ví dụ:

```text
User: Camera không thấy tay tôi.
Assistant: Bạn thử đưa bàn tay vào giữa khung hình...
User: Tôi làm rồi mà vẫn không được.
Assistant: Nếu tay đã nằm trong khung hình, bạn thử tăng ánh sáng...
```

Model cần học theo context chứ không reset mỗi câu.

---

# 22. NATURAL VARIATION GENERATION

Mỗi intent tạo nhiều cách nói:

```text
formal
casual
short
long
typo
without accents
mixed language
older-user style
younger-user style
frustrated
uncertain
```

Không thay đổi factual meaning.

---

# 23. EMOTION / SUPPORT DATA

Tạo scenario:

```text
frustrated
discouraged
confused
bored
tired
hesitant
satisfied
curious
```

Response phải supportive nhưng không overdo.

Ví dụ:

```text
User:
Tập mãi mà vẫn vậy.

Assistant:
Mình hiểu cảm giác đó. Bạn có thể xem lại tiến trình theo từng buổi thay vì chỉ nhìn một ngày. Nếu hôm nay khó hơn bình thường, hãy giữ buổi tập ngắn và thoải mái.
```

Không nói:

```text
"Bạn chắc chắn sẽ hồi phục."
```

---

# 24. HEALTH SAFETY DATA

Tạo evaluation/training scenarios về:

```text
pain
increasing pain
dizziness
numbness
weakness
shortness of breath
fainting
swelling
unexpected symptoms
```

AI phải:

- không chẩn đoán;
- không bịa nguyên nhân;
- không tiếp tục thúc người dùng tập khi có dấu hiệu đáng lo;
- dùng wording an toàn.

---

# 25. PRODUCT FACT BOUNDARY

Chatbot chỉ được nói fact mà backend/context cho phép.

Ví dụ:

```text
Complete
```

không được diễn giải thành:

```text
"Bạn thực hiện đúng về mặt y khoa."
```

`Incomplete` không được tự diễn giải:

```text
"Bạn bị yếu cơ."
```

Tracking lost không được gọi là movement error.

---

# 26. TRAINING DATA SPLIT

Tách theo:

```text
train
validation
test
```

Không để near-duplicate cùng intent/text xuất hiện cả train và test.

Evaluation set phải được giữ riêng.

---

# 27. SFT DATA

SFT chủ yếu cho:

```text
tone
format
scope
product behavior
context following
safe nutrition language
software troubleshooting
bilingual response
```

Không dùng SFT để nhồi hàng nghìn facts y tế.

---

# 28. RAG DATA

RAG dùng cho:

```text
rehab facts
exercise education
approved nutrition guidance
product documentation
FAQ
research references
```

RAG chunk phải có source.

---

# 29. PREFERENCE DATA

Có thể tạo pair:

```text
GOOD RESPONSE
vs
BAD RESPONSE
```

Ví dụ bad:

```text
"Bạn bị đau cổ do thoái hóa."
```

Good:

```text
"Mình không thể xác định nguyên nhân đau cổ chỉ từ mô tả này. Nếu triệu chứng tăng hoặc kéo dài, bạn nên được đánh giá phù hợp."
```

Dùng cho preference optimization nếu stack hỗ trợ.

---

# 30. NEGATIVE DATA

Tạo examples để model học không làm:

```text
hallucinated citation
fake product state
fake diagnosis
invented exercise result
invented backend action
invented session history
invented medical advice
overly robotic replies
overly enthusiastic replies
```

---

# 31. DATA BALANCE

Không để 80% data là health warnings.

Cân bằng:

```text
30% natural conversation
25% software/product support
20% rehabilitation education
10% nutrition/wellness
10% safety edge cases
5% mixed/other
```

Đây là starting target, không phải tỷ lệ bắt buộc.

---

# 32. DATA REVIEW

Status:

```text
RAW
CLEANED
REVIEWED
APPROVED
REJECTED
```

Chỉ `APPROVED` dùng production.

---

# 33. HUMAN REVIEW

Health/nutrition:

```text
require appropriate human review before production use
```

Conversational style:

```text
bilingual human review preferred
```

Software:

```text
verify against actual RehabAI behavior
```

---

# 34. CRAWLER SECURITY

Bắt buộc:

- only HTTP/HTTPS;
- block localhost;
- block private IP;
- block file://;
- block internal metadata endpoint;
- request timeout;
- max response size;
- redirect limit;
- MIME validation;
- sanitize HTML;
- do not execute fetched JS;
- rate limit;
- cache;
- retry with backoff.

---

# 35. CRAWLER FAILURE HANDLING

Nếu provider lỗi:

```text
PROVIDER_UNAVAILABLE
```

Nếu timeout:

```text
FETCH_TIMEOUT
```

Nếu parsing fail:

```text
PARSE_FAILED
```

Nếu license không rõ:

```text
LICENSE_UNKNOWN
```

Nếu source không verify:

```text
NEEDS_VERIFICATION
```

Không fake success.

---

# 36. SOFTWARE DATA GENERATION AGENT

Agent phải đọc:

```text
frontend routes
backend routes
API schemas
error codes
UI labels
auth behavior
camera flow
session flow
Ollama integration
```

Sau đó tạo support dataset từ fact thật.

Không được bịa route/API.

---

# 37. CONVERSATION GENERATION AGENT

Tạo synthetic conversations nhưng:

- grounded vào approved product/knowledge;
- nhiều phong cách;
- không thêm facts;
- không copy cùng một mẫu;
- không tạo câu trả lời quá dài nếu user chỉ hỏi ngắn.

---

# 38. NUTRITION GENERATION AGENT

Chỉ tạo:

```text
general education
meal structure examples
hydration guidance
food group explanations
balanced plate concepts
general protein/fiber education
```

Không tạo:

```text
prescriptive clinical meal plan
disease treatment diet
supplement dosing
extreme calorie target
```

---

# 39. OUTPUT DATA FORMAT

Xuất:

```text
JSONL
```

Ví dụ SFT:

```json
{"messages":[{"role":"system","content":"..."},{"role":"user","content":"..."},{"role":"assistant","content":"..."}],"domain":"software","intent":"CAMERA_PERMISSION","language":"vi","review_status":"APPROVED"}
```

---

# 40. DIRECTORY STRUCTURE

```text
data_ai/
├── raw/
│   ├── rehab/
│   ├── software/
│   ├── nutrition/
│   └── conversation/
│
├── processed/
│   ├── chunks/
│   ├── conversations/
│   └── metadata/
│
├── approved/
│   ├── rag/
│   ├── sft/
│   └── eval/
│
├── rejected/
├── reports/
└── manifests/
```

---

# 41. MANIFEST

Mỗi build corpus tạo:

```json
{
  "corpus_version": "v1",
  "created_at": "...",
  "source_count": 0,
  "chunk_count": 0,
  "conversation_count": 0,
  "approved_count": 0,
  "rejected_count": 0,
  "domains": {},
  "languages": {},
  "licenses": {}
}
```

---

# 42. QUALITY REPORT

Agent phải báo:

```text
sources collected
sources rejected
duplicate rate
language distribution
domain distribution
intent distribution
average turns
average response length
unsupported claim count
license unknown count
human review pending
```

---

# 43. EVALUATION SET

Tạo riêng:

```text
software QA
rehab QA
nutrition QA
natural conversation
safety
hallucination
bilingual
context retention
```

Không train trên eval set.

---

# 44. NATURALNESS EVALUATION

Đánh giá:

```text
not robotic
not repetitive
correct tone
context aware
concise when appropriate
natural Vietnamese
natural English
mixed-language handling
```

---

# 45. PRODUCT ACCURACY EVALUATION

Check:

```text
no fake session
no fake history
no fake backend action
no fake exercise cause
no fake citation
no fake model confidence
```

---

# 46. RAG-FIRST RELEASE PLAN

Recommended order:

```text
Phase 1
Product docs + FAQ RAG

Phase 2
Approved rehab knowledge RAG

Phase 3
Approved nutrition RAG

Phase 4
Conversation SFT

Phase 5
Preference tuning if needed

Phase 6
Regression evaluation
```

Không fine-tune trước khi baseline + RAG được đánh giá.

---

# 47. FINAL EXECUTION PROMPT

```text
Hãy xây dựng RehabAI Local AI Data Pipeline.

Mục tiêu:
- thu thập dữ liệu hợp pháp;
- không crawl vô hạn;
- không bypass paywall;
- không lấy private data;
- không fake citation;
- không dùng raw data trực tiếp để train;
- giữ provenance và metadata.

Tách data thành:

1. rehab knowledge
2. software/product support
3. general nutrition/wellness
4. natural conversation
5. safety
6. bilingual VI/EN

Kiến thức factual:
→ ưu tiên RAG.

Fine-tuning:
→ ưu tiên tone, style, product behavior, context handling.

Software dataset:
→ phải dựa trên code/docs/API thật của RehabAI.

Nutrition:
→ general education only;
→ không clinical diet planning;
→ không supplement dosing;
→ không diagnosis.

Conversation:
→ tự nhiên;
→ không máy móc;
→ không lặp;
→ đa dạng cách nói;
→ multi-turn;
→ VI/EN/mixed;
→ có typo/no-accent examples.

Mỗi source phải có:
- source_id
- URL
- publisher
- license/access type
- retrieved_at
- trust tier
- verification status.

Mỗi training item phải có:
- domain
- intent/topic
- language
- source/provenance
- review status.

Chỉ APPROVED data được:
- index vào production RAG;
- dùng để fine-tune production model.

Nếu source/license không rõ:
→ NEEDS_VERIFICATION.

Nếu không thể verify:
→ BLOCKED / REJECT.

Không tự báo dataset production-ready.

Cuối cùng phải xuất:

COLLECTED:
CLEANED:
DEDUPLICATED:
APPROVED:
REJECTED:
LICENSE_UNKNOWN:
HUMAN_REVIEW_PENDING:
RAG_READY:
SFT_READY:
EVAL_READY:
KNOWN_LIMITATIONS:
NEXT_STEPS:
```

---

# 48. FINAL PRINCIPLE

```text
Knowledge accuracy
→ RAG

Conversation quality
→ SFT

Safety
→ rules + curated training + evaluation

Product facts
→ backend/context

Human review
→ required before production
```

Không dùng một kỹ thuật duy nhất cho tất cả.
