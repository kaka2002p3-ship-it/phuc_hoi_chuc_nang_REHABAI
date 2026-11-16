# RehabAI — các cải tiến an toàn đã thực hiện

Ngày: 2026-09-22

## Đã triển khai

### Công cụ duyệt dữ liệu

- Khi hàng đợi đã được duyệt hết, bộ lọc mặc định tự chuyển từ `Chưa duyệt` sang `Đã duyệt`.
- Thêm bộ lọc `Mức ưu tiên` cho queue đa seed.
- Smoke test bằng Streamlit AppTest: 0 exception; hiển thị đúng 401/401 đã duyệt.

### Frontend

- Chuyển các page sang `React.lazy` + `Suspense` để tải theo route.
- Entry JavaScript bundle giảm từ khoảng `725.15 KB` xuống `282.94 KB` trước gzip.
- Frontend lint: PASS.
- TypeScript + Vite production build: PASS.

### Regression

- Backend/shared: 176 passed, 1 skipped.
- Skip duy nhất do Windows host không có quyền tạo symlink.

## Chưa tự động thực hiện và lý do

### Đổi `ELBOW_EXTENSION` thành `ELBOW_FLEXION` trong production

Chưa đổi trực tiếp vì production artifact hiện khai báo bài ID 2 là duỗi khuỷu tay, trong khi tập `datanew` mới là gập khuỷu tay. Đổi tên đơn thuần sẽ làm sai semantic của artifact và dữ liệu lịch sử. Cần một migration/versioned exercise registry sau khi chủ dự án xác nhận bài production mục tiêu.

### Tích hợp temporal checkpoint vào quyết định người dùng

Chưa tích hợp vì checkpoint temporal nhận cửa sổ rep 48 frame đã cắt, còn realtime backend hiện tạo cửa sổ inference 96 frame và rep counter chỉ báo số rep, chưa cung cấp boundary/window adapter đã kiểm chứng. Nối trực tiếp sẽ tạo sai lệch preprocessing và có nguy cơ đưa kết quả nghiên cứu thành cảnh báo không hợp lệ.

Temporal model chỉ nên được đưa vào shadow mode sau khi có adapter:

1. chốt boundary rep từ realtime counter;
2. lưu đủ pose/hand landmarks của rep;
3. áp dụng đúng normalization/resampling như `DatanewRepDataset`;
4. ghi shadow output riêng, không thay `matched/mismatched`;
5. đối chiếu với video fresh-subject được chuyên gia duyệt.

## Trạng thái

Các cải tiến UX/performance đã đạt regression gate. Model production và ý nghĩa lịch sử người dùng không bị thay đổi.

## Bổ sung sau QA

- Đã thêm `scripts/evaluate_datanew_fresh_subject.py`: evaluator inference-only,
  từ chối video trùng split v2 và ghi kết quả shadow riêng.
- Đã thêm manifest mẫu `data/annotations/fresh_subject_eval_manifest.template.csv`
  và hướng dẫn `reports/evaluation/FRESH_SUBJECT_EVAL_README.md`.
- Evaluator dùng threshold riêng của từng seed và majority vote; không tối ưu
  ngưỡng trên tập fresh-subject.
- Regression sau bổ sung: **176 passed, 1 skipped**; script evaluator compile PASS.
