# RehabAI full status audit — 2026-09-20

## Runtime verification

| Component | Status | Evidence |
|---|---|---|
| FastAPI backend | PASS | `http://127.0.0.1:8000/docs` → HTTP 200 |
| React/Vite frontend | PASS | `http://127.0.0.1:5173/` → HTTP 200 |
| Ollama local endpoint | PASS | `http://127.0.0.1:11434/api/version` → HTTP 200 |
| Backend/frontend tests | PASS | `175 passed, 1 skipped` |
| Frontend production build | PASS | `tsc -b && vite build` |

## Đã làm được

- Tài khoản, JWT và phân quyền dữ liệu theo `user_id`.
- History và session detail chỉ trả session thuộc tài khoản hiện tại.
- Chi tiết từng repetition có trạng thái `matched`, `mismatched`, `unassessed`.
- `matched/mismatched` chỉ được ghi khi confidence đạt ngưỡng và landmark tracking đủ; mặc định ngưỡng `0.70`.
- `unassessed` được dùng khi confidence thấp hoặc pose/tracking chưa đủ.
- AI Coach dùng context RAG theo session/user sở hữu; có giới hạn history và kiểm tra evidence IDs.
- Ollama dùng structured output, local-only fallback và prompt đóng gói có kiểm tra drift.
- Hai bài production trong artifact hiện tại là 4 lớp model registry; luồng người dùng đang dùng bài được chọn và có kiểm tra khớp classifier.
- Datanew đã catalog 238 video local, 179 ready; manifest tổng có 619 ready samples.
- Đã tạo 921 repetition candidates và nhãn nghiên cứu `auto_rule_v1` với provenance.
- Đã chạy strict multi-seed research baseline; artifact/log được lưu trong `experiments/` và `logs/`.

## Đã làm nhưng chỉ ở mức nghiên cứu

- Model RehabMotionNet/CTR-TCN chưa đạt product-ready theo audit model hiện có.
- Datanew completion có tín hiệu nghiên cứu, nhưng exercise replacement không vượt baseline ổn định.
- Rep baseline strict 4 seed đạt trung bình heuristic-label Macro-F1 `0.6590` (ELBOW_FLEXION) và `0.6712` (HAND_OPENING); đây không phải correctness lâm sàng.
- `auto_rule_v1` tạo nhãn từ quy tắc biên độ/timing; không được dùng làm ground truth.

## Chưa làm được / đang bị chặn

- Chưa có nhãn chuyên gia hoặc người dùng xác nhận đủ để kết luận động tác đúng kỹ thuật.
- Chưa có đánh giá rep MAE, boundary F1 và temporal IoU với annotation chuẩn.
- `ELBOW_FLEXION` của datanew chưa phải bài production `ELBOW_EXTENSION`; không được trộn hai ontology.
- EHW trigger chưa nối được với video cùng subject nên chưa dùng được cho boundary/correctness supervision.
- 289 video extraction rejected của bộ dữ liệu chính chưa được rescue/quality-gate lại.
- Chưa có bằng chứng fresh-subject/clinical validation; không promote checkpoint nghiên cứu vào production.
- Chưa nên gọi `mismatched` là “động tác sai”; nó chỉ là model nhận diện bài khác bài đã chọn.

## Artifact chính

- `artifacts/model_v2/`: production bundle đang được backend load.
- `data/datanew_unlabeled/combined_ready_manifest.csv`: 619 ready samples.
- `data/annotations/datanew_rep_review_queue.csv`: 921 candidate repetitions.
- `data/annotations/datanew_rep_auto_experimental.csv`: 462 heuristic labels + 459 uncertain.
- `reports/evaluation/DATANEW_REP_MULTISEED_STRICT_4SEEDS.md`: 4-seed strict summary.
- `reports/evaluation/REHABAI_COMPREHENSIVE_AUDIT_2026-09-20.md`: audit model/data cũ cần đọc cùng báo cáo này.

## Kết luận phát hành

Ứng dụng chạy được để demo/nghiên cứu có kiểm soát. Quyền riêng tư, API history, RAG ownership, build và test đều đạt. Tuy nhiên hệ thống chưa đủ bằng chứng để tuyên bố nhận diện đúng/sai kỹ thuật hoặc hiệu quả lâm sàng. Nhãn heuristic và các model nghiên cứu phải được giữ ngoài production gate cho đến khi có annotation được duyệt và fresh-subject validation.
