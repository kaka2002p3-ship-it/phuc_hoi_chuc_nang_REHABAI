# Phase 4.7 Stage 3 — Real data preparation

Chạy các file CMD theo thứ tự. Không chạy nhiều bước cùng lúc.

1. `01_VERIFY_ENV.cmd`
   - Chỉ kiểm tra 491 video, 10 subject, đường dẫn, dependency và dung lượng đĩa.
   - Tạo một khóa HMAC cục bộ trong `.secrets/`; khóa không được gửi cho người khác.
   - Nếu hiện `[FAIL]` hoặc `[STOP]`, dừng lại và gửi file `logs/phase_4_7_stage3/01_verify_env.log`.

2. `02_EXTRACT_REAL_DATA.cmd`
   - Chạy MediaPipe trên video thật.
   - Ghi kết quả riêng vào `data/stage3_real/interim/keypoints`.
   - Có thể chạy lại cùng file CMD nếu máy tắt hoặc tiến trình bị gián đoạn.
   - Không dùng tùy chọn `--overwrite` khi chưa kiểm tra nguyên nhân.
   - Khi xong, gửi:
     - `logs/phase_4_7_stage3/02_extract_real_data.log`
     - `data/stage3_real/indexes/extraction_quality.csv`

3. `03_PROCESS_REAL_FEATURES.cmd`
   - Chỉ chạy sau khi bước 2 đã được kiểm tra.
   - Chỉ nhận các mẫu có trạng thái extraction `success`.
   - Không fit mean/std toàn bộ dataset; normalization thống kê sẽ được fit riêng từ train của từng LOSO fold.
   - Tạo `REAL_CANDIDATE`, chưa cấp quyền `REAL_VERIFIED`.

4. `04_VERIFY_PROVENANCE.cmd`
   - Chỉ chạy sau khi bước 3 đã được kiểm tra.
   - Kiểm tra lại file thật, hash và đường dẫn; sau đó ký manifest.
   - Khóa trong `.secrets/provenance_hmac_key.txt` phải được giữ nguyên cho các bước LOSO/train/evaluate sau này.

## Điều kiện dừng

Dừng ngay nếu một CMD trả mã lỗi, có dòng `[FAIL]` hoặc `[STOP]`, có `error_*` trong quality log, hoặc số lượng video không phải 491. Các video bị quality gate từ chối cần được xem xét riêng; không tự đổi ngưỡng để ép đủ mẫu.
