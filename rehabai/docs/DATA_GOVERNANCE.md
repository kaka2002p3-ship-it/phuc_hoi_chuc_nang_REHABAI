# Quản trị dữ liệu RehabAI

- Chỉ lưu landmark/kết quả phiên tập; backend không lưu frame webcam.
- Session, pain, report và settings được giới hạn theo chủ tài khoản bằng JWT.
- `GET /api/users/me/export` xuất dữ liệu của chính người dùng.
- `DELETE /api/users/me` xóa tài khoản cùng session, pain, settings, report, hội thoại chatbot và dữ liệu dẫn xuất liên quan.
- Audit event chỉ lưu hành động và định danh tài nguyên tối thiểu; khi xóa tài khoản, liên kết người dùng trong audit được ẩn danh.
- Retention mặc định do đơn vị triển khai quyết định. Trước khi dùng với người thật phải công bố thời hạn lưu, consent, quy trình backup và người chịu trách nhiệm dữ liệu.
- Production bắt buộc HTTPS ở reverse proxy, JWT secret riêng, CORS allowlist và PostgreSQL có backup/mã hóa ổ đĩa.
