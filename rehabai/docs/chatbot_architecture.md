# Chatbot architecture

`React → authenticated FastAPI → safety screening → owned session context → local Ollama → schema/evidence validation → owned conversation storage`.

Camera và bộ đếm rep không phụ thuộc Ollama. Khi chatbot lỗi, buổi tập vẫn tiếp tục hoạt động. Backend giới hạn số yêu cầu Ollama đồng thời và chỉ lấy lịch sử hội thoại thuộc tài khoản hiện tại.

Knowledge ingestion chỉ đọc tài liệu có metadata `approved`, hash nội dung khớp
và chưa hết hạn. Quy trình review và hợp đồng metadata nằm trong
`backend/knowledge/`. Runtime hiện có hướng dẫn sử dụng sản phẩm đã được đối
chiếu với mã nguồn; nội dung y khoa/chuyên môn vẫn phải chờ chuyên gia duyệt.
Mỗi knowledge set sinh `knowledge_version` xác định từ version và SHA-256.
