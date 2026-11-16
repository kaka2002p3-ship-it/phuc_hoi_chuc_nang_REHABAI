# RehabAI Companion — Ollama local

Chatbot chạy local bằng Ollama và chỉ hỗ trợ hai bài đang mở: chu kỳ gập/duỗi khuỷu tay (`ELBOW_EXTENSION`, ID 2, mã production lịch sử) và `HAND_OPENING` (ID 4). Tác vụ nghiên cứu `ELBOW_FLEXION` chưa tự động thay thế model production. Chatbot không đo chuyển động, không tạo metric và không thay đổi phác đồ. Context session được backend truy vấn theo JWT.

## Runtime

- Ollama đã kiểm tra: `0.34.1`; model local: `qwen2.5:7b`.
- System prompt: chỉ khối mục 7 trong `RehabAI_Ollama_Chatbot_MASTER_VI_EN.md`.
- Prompt version `master-vi-en-1.0`, schema version `1.0`.
- Cloud fallback tắt mặc định.
- Long-term memory chưa bật. RAG hướng dẫn sản phẩm đã hoạt động; knowledge
  chuyên môn y khoa vẫn chưa được phê duyệt.

## API

- `POST /api/chat`
- `GET /api/chat/status`
- `GET /api/chat/conversations`
- `GET/DELETE /api/chat/conversations/{id}`
- `GET /api/chat/memory`
- `POST /api/chat/session-summary?session_id=...`

Tất cả endpoint yêu cầu Bearer token. Conversation và session được kiểm tra ownership. Ollama trả JSON có cấu trúc; backend chặn evidence ID không tồn tại và fallback rõ trạng thái khi model lỗi.

Đây là prototype nghiên cứu/demo, chưa được kiểm định lâm sàng.
