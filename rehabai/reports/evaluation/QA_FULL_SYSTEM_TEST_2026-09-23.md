# RehabAI — báo cáo kiểm thử toàn hệ thống

Ngày kiểm thử: 2026-09-23  
Môi trường: Windows host + Docker production-like, PostgreSQL, Ollama `qwen2.5:7b`

## 1. Kết luận

- **PASS cho mục đích demo/nghiên cứu nội bộ.**
- **Chưa PASS cho sản phẩm lâm sàng hoặc kết luận kỹ thuật động tác.**
- API nghiệp vụ, quyền riêng tư và AI Coach hoạt động tốt.
- Phạm vi sản phẩm chỉ gồm **2 bài**: gập/duỗi khuỷu tay (ID 2) và mở bàn tay (ID 4).
- Bộ đếm luật của hai bài sản phẩm vượt 10/10 chu kỳ mô phỏng có kiểm soát.
- Mô hình nhận diện trên spot-check hai bài thật đạt 7/10 dự đoán thô đúng loại bài (70%), nhưng chỉ 6/10 kết quả đủ ngưỡng 0,70 để ứng dụng chấp nhận (60%). Đây không thay thế kết quả LOSO chính thức.
- Kết quả chính thức của artifact production hiện tại vẫn là accuracy trung bình 43,79% và Macro-F1 35,44% trên 387 mẫu LOSO; chưa đủ mạnh để gọi là product-ready.

## 2. Kết quả tự động và dịch vụ

| Hạng mục | Kết quả | Bằng chứng |
|---|---:|---|
| Docker/backend/PostgreSQL/frontend | PASS | Các container hoạt động; backend healthy |
| Health/model/Ollama | PASS | HTTP 200, `model_loaded=true`, `ollama_enabled=true` |
| Backend + shared tests | CÓ LỖI | 176 passed, 1 failed, 1 skipped |
| Frontend lint | PASS | `npm run lint`, exit 0 |
| Frontend production build | PASS | 2.465 modules, build exit 0 |
| Live API E2E | PASS | 30/30 checks |
| WebSocket trên container | PASS | Token hợp lệ; JSON lỗi trả `Invalid JSON` |
| MediaPipe trên container | PASS | `RealtimeExtractor` khởi tạo thành công |
| AI Coach session RAG | PASS | HTTP 200, Ollama, khoảng 3,11 giây |
| Cách ly dữ liệu hai tài khoản | PASS | Truy cập chéo session/pain/chat đều HTTP 404 |

Test bị lỗi là `tests/test_websocket_auth.py::test_websocket_accepts_authenticated_user`: MediaPipe 0.10.21 trên Python Windows host không parse được Holistic graph. Cùng thao tác trong container Linux vẫn PASS, nên đây là lỗi môi trường phát triển/parity, không phải lỗi runtime Docker đang chạy.

## 3. Năm lượt nhận diện cho mỗi bài tập sản phẩm

Nguồn: mẫu `REAL_VERIFIED` từ fold 04; riêng lượt 5 của bài 2 lấy validation subject 02 vì test subject 04 chỉ có bốn mẫu bài 2. Artifact production là checkpoint fold 04. `Matched` chỉ được ghi khi dự đoán đúng và confidence >= 0,70. ID 1 và ID 3 chỉ là lớp nội bộ còn tồn tại trong artifact nghiên cứu, không phải bài tập được mở trên sản phẩm và không được tính trong báo cáo chức năng này.

### Bài 2 — Gập/duỗi khuỷu tay

| Lượt | Dự đoán | Confidence | Đánh giá ứng dụng |
|---:|---:|---:|---|
| 1 | 1 | 54,4% | Unassessed |
| 2 | 2 | 89,9% | Matched |
| 3 | 2 | 73,8% | Matched |
| 4 | 2 | 49,8% | Unassessed |
| 5 | 2 | 85,4% | Matched |

- Dự đoán thô đúng: **4/5 = 80%**.
- Kết quả được ứng dụng chấp nhận: **3/5 = 60%**.

### Bài 4 — Mở bàn tay

| Lượt | Dự đoán | Confidence | Đánh giá ứng dụng |
|---:|---:|---:|---|
| 1 | 2 | 36,9% | Unassessed |
| 2 | 4 | 98,1% | Matched |
| 3 | 4 | 99,7% | Matched |
| 4 | 4 | 98,4% | Matched |
| 5 | 3 | 45,9% | Unassessed |

- Dự đoán thô đúng: **3/5 = 60%**.
- Kết quả được ứng dụng chấp nhận: **3/5 = 60%**.

### Tổng 10 lượt của hai bài sản phẩm

- Dự đoán thô đúng loại bài: **7/10 = 70%**.
- Matched đủ confidence: **6/10 = 60%**.
- Unassessed do confidence thấp: **4/10 = 40%**.
- Mismatched confidence cao: **0/10 = 0%**.

Đây chỉ là spot-check 10 mẫu của hai bài sản phẩm, không phải accuracy/F1 chính thức. Chỉ số LOSO hiện có là của artifact bốn lớp nội bộ nên chưa phải metric riêng sạch cho đúng hai bài đang mở trên giao diện.

## 4. Kiểm thử bộ đếm ở năm mức độ

Hai bài sản phẩm được chạy cùng năm tình huống bằng tín hiệu landmark có kiểm soát:

| Mức | Tình huống | Kỳ vọng | Bài 2 | Bài 4 |
|---:|---|---:|---:|---:|
| 1 | Biên độ đầy đủ | Đếm 1 | PASS | PASS |
| 2 | Chạm đúng ngưỡng | Đếm 1 | PASS | PASS |
| 3 | Thiếu biên độ | Không đếm | PASS | PASS |
| 4 | Nhiễu, không ổn định đủ frame | Không đếm | PASS | PASS |
| 5 | Landmark không đạt quality gate | Không đếm | PASS | PASS |

Ngoài ra, chuỗi năm chu kỳ đầy đủ liên tiếp của từng bài đều được đếm đúng 5/5. Tổng kiểm thử logic sản phẩm là 10/10 chu kỳ. Kết quả này xác minh state machine/ngưỡng, **không chứng minh camera ngoài đời đếm chính xác 100%**.

## 5. Thử nghiệm video qua WebSocket thật

Một video thật 810x1440 của bài khuỷu tay được gửi 110 frame qua đúng pipeline WebSocket -> MediaPipe -> quality gate -> model:

- 110/110 frame: `insufficient_landmarks`.
- 0 frame inference.
- 0 rep được đếm.

Khung hình chỉ chứa một phần cánh tay, không thấy đủ vai–khuỷu–cổ tay. Quality gate từ chối là hành vi an toàn đúng thiết kế, nhưng kịch bản quay cận/dọc này **FAIL về khả năng sử dụng**. Người dùng phải lùi camera để thấy đủ các khớp bắt buộc.

## 6. Ma trận chức năng

### PASS

- Đăng ký, đăng nhập, từ chối sai mật khẩu/email trùng.
- Route bảo vệ từ chối người chưa đăng nhập.
- Hồ sơ cá nhân, ảnh đại diện, mục tiêu tuần và chỉ số tự khai báo qua API.
- Tạo/kết thúc buổi tập, mục tiêu số lần, tạm dừng phía giao diện.
- Chặn bắt đầu khi đau trước tập >= 7; cảnh báo đau tăng sau tập.
- Lịch sử, lọc/tìm kiếm, chi tiết buổi và danh sách từng lần đã ghi.
- Báo cáo tổng hợp, tiến trình, export và xóa tài khoản.
- Theme sáng/tối/hệ thống và lưu setting.
- Quyền riêng tư session, pain, history, conversation và AI Coach RAG.
- AI Coach Ollama, lưu/xóa/xem lại hội thoại, ngôn ngữ trả lời ở API.
- WebSocket authentication, lỗi payload, MediaPipe runtime Docker.
- Frontend lint/build và phục vụ HTTP.
- Bộ đếm logic cho hai bài sản phẩm (ID 2 và 4).

### ĐANG TĨNH / CHƯA HOÀN THIỆN

- Artifact nghiên cứu/backend registry vẫn chứa bốn lớp; giao diện sản phẩm chỉ mở đúng bài 2 và 4. Đây là chi tiết nội bộ cần được tách khỏi phạm vi chức năng người dùng.
- `Research Mode` chỉ hiển thị placeholder; chưa lấy tracking quality, latency, WebSocket và session log thật.
- Nút chuông thông báo không có hành động.
- Ba nút gợi ý trên trang AI Coach không điền/gửi prompt.
- `practice_reminders` chỉ lưu DB, chưa có bộ lập lịch/thông báo.
- `language` trong Settings chỉ lưu DB, chưa đổi ngôn ngữ toàn giao diện.
- `camera_resolution` chỉ lưu DB; Practice vẫn hard-code 640x480.
- Bộ nhớ dài hạn AI Coach trả `not_enabled`.
- Kho knowledge đã duyệt là `none-unapproved`; session RAG vẫn hoạt động.
- Completion head chưa được promote; `completion_status`, `quality_score`, phase và feedback lỗi chi tiết chưa hoạt động.
- Chấm đúng/sai **kỹ thuật** theo góc khớp, biên độ và lỗi động tác chưa có; chi tiết từng lần hiện chỉ so sánh loại bài nhận diện với bài đã chọn.

### FAIL / CẦN KHẮC PHỤC

- Mô hình nhận diện hiện chưa đạt chất lượng production/clinical: LOSO accuracy 43,79%, Macro-F1 35,44%.
- Kịch bản camera/video quay cận không thấy đủ khớp: 110/110 frame bị từ chối, không có inference hoặc rep.
- Bộ test WebSocket trực tiếp trên Python Windows fail do MediaPipe graph parse; cần đồng bộ môi trường Windows với container hoặc chạy test này trong container.

## 7. Hạng mục chưa thể tuyên bố PASS

- Năm lượt người thật trước webcam/điện thoại ở các khoảng cách, ánh sáng, góc quay và tốc độ khác nhau.
- Camera permission trên Chrome Android/iOS và HTTPS trong mạng LAN.
- Độ chính xác rep ngoài đời vì chưa có ground-truth start/end của từng rep cho các video vừa chạy.
- Đánh giá lâm sàng hoặc đúng/sai kỹ thuật bởi chuyên gia.
- Tải đồng thời nhiều người dùng và soak test kéo dài.

## 8. Ưu tiên đề xuất

1. P0: quay bộ kiểm thử fresh-subject cho hai bài đang mở, mỗi bài ít nhất 30–50 clip, bao phủ đủ khung, quay cận, ánh sáng yếu, nhanh/chậm và tay trái/phải.
2. P0: cải thiện model cho đến khi vượt baseline ổn định trên subject holdout; không dựa vào spot-check 80%.
3. P0: thêm hướng dẫn framing trực quan để bắt buộc thấy đủ vai–khuỷu–cổ tay hoặc toàn bàn tay trước khi bắt đầu.
4. P1: làm `camera_resolution`, ngôn ngữ và reminder thực sự có hiệu lực; hoàn thiện Research Mode và notification.
5. P1: sửa parity MediaPipe trên Windows hoặc chuẩn hóa toàn bộ inference/test bằng Docker.
6. P2: chỉ triển khai chấm kỹ thuật sau khi có nhãn chuyên gia theo từng rep và validation fresh-subject độc lập.

## 9. Bằng chứng chính

- `artifacts/model_v2/metrics.json`
- `artifacts/model_v2/model_card.md`
- `backend/core/rep_counter.py`
- `backend/api/websocket.py`
- `frontend/src/pages/Practice.tsx`
- `frontend/src/pages/SessionDetail.tsx`
- `frontend/src/pages/Research.tsx`
- `.runtime/qa_e2e_runner.py`
