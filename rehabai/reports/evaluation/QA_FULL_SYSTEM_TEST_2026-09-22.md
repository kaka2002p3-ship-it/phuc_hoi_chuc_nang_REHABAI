# RehabAI — báo cáo kiểm thử toàn hệ thống

Ngày: 2026-09-22  
Vai trò: tester/QA độc lập trong workspace phát triển.

## Kết quả tổng quan

| Nhóm kiểm thử | Kết quả |
|---|---|
| Backend + shared automated tests | **176 passed, 1 skipped** |
| Frontend lint | **PASS** |
| Frontend production build | **PASS** |
| API E2E trên DB QA riêng | **30/30 PASS** |
| WebSocket auth/invalid payload tests | **16 passed** (trong subset chạy riêng) |
| Data/artifact/leakage audit | **PASS** |
| Streamlit review app smoke run | **PASS, 0 exception** |
| Docker Compose config | **PASS** khi cung cấp `JWT_SECRET` |
| Production import với auto schema creation tắt | **PASS** |

## Phạm vi đã kiểm tra

- Đăng ký, đăng nhập, sai mật khẩu, email trùng.
- Route bảo vệ khi chưa xác thực.
- Cập nhật hồ sơ và settings round-trip.
- Tạo/kết thúc buổi tập.
- Ngăn bắt đầu khi pain trước tập >= 7.
- Cảnh báo khi pain tăng sau tập.
- Lịch sử, chi tiết rep, báo cáo tổng hợp và tiến trình.
- Export dữ liệu cá nhân và xóa tài khoản.
- Cô lập session, pain, lịch sử và hội thoại giữa hai tài khoản.
- AI Coach dùng Ollama `qwen2.5:7b`, truy cập session thuộc tài khoản hiện tại.
- WebSocket thiếu token, token hợp lệ và payload JSON lỗi.
- Model artifact, registry, schema, split v2 và video-disjoint leakage.
- Streamlit review queue sau khi 401/401 mẫu đã được duyệt.

## Lỗi chức năng

Không phát hiện lỗi blocker trong các luồng đã kiểm thử.

## Cảnh báo và nợ kỹ thuật

1. **Màn hình duyệt sau khi duyệt hết dữ liệu:** bộ lọc mặc định là `Chưa duyệt`, nên hiển thị `Đang hiển thị = 0` dù `Đã duyệt = 401`. Đây là vấn đề UX; nên tự chuyển sang `Đã duyệt` hoặc `Tất cả` khi không còn hàng chờ.
2. Frontend bundle chính khoảng **725 KB** sau minify; nên code-split/lazy-load các page để cải thiện tải lần đầu.
3. Có 1 test symlink bị skip vì Windows host không có quyền tạo symlink (`WinError 1314`), không phải lỗi logic ứng dụng.
4. Một số cảnh báo TensorFlow/Matplotlib deprecation xuất hiện, không làm fail test.
5. `ELBOW_FLEXION` của temporal research model chưa được nối vào production artifact; production vẫn dùng registry/model v2 và tên bài `ELBOW_EXTENSION`. Cần thống nhất mapping trước khi tích hợp.
6. `approved_knowledge` đang rỗng; AI Coach hiện RAG dữ liệu session có phân quyền, chưa phải kho kiến thức vector đã phê duyệt.
7. Kết quả model `ELBOW_FLEXION` tốt trên split v2 nhưng chưa thay thế kiểm định fresh-subject/video và chưa phải bằng chứng lâm sàng.

## Trạng thái dịch vụ lúc kết thúc QA

- Backend demo chính: cổng `8000` đang lắng nghe.
- Ollama: cổng `11434` đang lắng nghe.
- Frontend `5173` và Streamlit `8502` không còn lắng nghe tại thời điểm kiểm tra cuối; có thể khởi động lại bằng lệnh demo trong README.
- Server QA tạm dùng cổng `8011` đã được dừng sau khi kiểm thử.

## Đánh giá phát hành

**PASS cho demo/research nội bộ.**  
**Chưa PASS cho production/clinical use** do giới hạn mô hình, mapping tên bài, fresh-subject validation và các cảnh báo UX/performance ở trên.
