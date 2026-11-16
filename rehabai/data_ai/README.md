# RehabAI local AI corpus

Thư mục này được sinh bởi `scripts/build_local_ai_corpus.py` theo nguyên tắc RAG-first.

- `approved/rag`: chỉ tài liệu đã được workflow knowledge của dự án duyệt.
- `processed/conversations`: dữ liệu tổng hợp đã làm sạch nhưng **chưa được duyệt**.
- `processed/evaluation`: bộ đánh giá nháp, không được dùng để train.
- `approved/sft`: để trống cho tới khi reviewer xác nhận từng mẫu.
- `manifests`: provenance và thống kê build.
- `reports`: báo cáo chất lượng và giới hạn.

Lệnh build và kiểm tra:

```powershell
cd D:\PhucHoiChucNangTay\rehabai
$env:PYTHONPATH='.'
python scripts\build_local_ai_corpus.py
python scripts\validate_local_ai_corpus.py
pytest -q tests\test_local_ai_corpus.py tests\test_knowledge_retriever.py tests\test_chatbot_master.py
```

Không fine-tune trực tiếp từ `raw/` hoặc `processed/`. Chỉ item có `review_status=APPROVED`
mới được chuyển vào `approved/sft`. Nội dung rehabilitation/nutrition/safety cần reviewer phù hợp.

Thu thập một nguồn công khai đã được chọn trước (không crawl hàng loạt):

```powershell
python scripts\safe_source_collector.py `
  --url "https://example.org/public-document" `
  --domain rehab `
  --title "Tên tài liệu" `
  --publisher "Nhà xuất bản" `
  --license "CC-BY-4.0" `
  --access-type open_access `
  --trust-tier A
```

Collector kiểm tra scheme, DNS/IP công khai, redirect, robots.txt, MIME, timeout và kích thước.
Nếu license không rõ, nguồn được đánh dấu `NEEDS_VERIFICATION` và không vào approved corpus.

Sau khi reviewer đã đọc từng sample, sao chép file mẫu
`manifests/review_decision.example.json`, điền danh tính/vai trò và các `sample_id`, rồi chạy:

```powershell
python scripts\promote_local_ai_samples.py --review-file data_ai\manifests\review_decision.json
python scripts\validate_local_ai_corpus.py
```

Để tạo bảng CSV cho bạn duyệt các mẫu software/conversation còn lại:

```powershell
python scripts\export_local_ai_review_queue.py --reviewer TOS_01 --domains software,conversation
```

Mở file `reports/TOS_01_review_queue.csv`, đọc từng câu trả lời. Chỉ các `sample_id`
được bạn xác nhận mới thêm vào `approved_sample_ids` trong `review_decision.json`, sau đó
chạy lại lệnh promote. Công cụ promote cộng dồn, không ghi đè các mẫu đã duyệt trước đó.

Cách đơn giản hơn: trong CSV, đổi cột `decision` từ `PENDING` thành `APPROVED` hoặc
`REJECTED`, lưu file rồi nhập trực tiếp quyết định bằng lệnh:

```powershell
python scripts\apply_local_ai_review_queue.py `
  --queue data_ai\reports\TOS_01_review_queue.csv `
  --reviewer TOS_01 `
  --reviewer-role "Chủ sở hữu sản phẩm RehabAI"

python scripts\validate_local_ai_corpus.py
```
