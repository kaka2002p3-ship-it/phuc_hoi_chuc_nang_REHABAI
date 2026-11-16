# RehabAI — Báo cáo audit tổng thể

Ngày kiểm tra: 2026-09-20

## 1. Kết luận điều hành

Preflight dữ liệu: **PASS (16/16 checks)**. Unit/integration tests: **175 passed, 1 skipped**. Frontend production build: **PASS**. Backend/frontend runtime tại thời điểm audit: **STOPPED**, không có tiến trình Uvicorn/Vite đang chạy.

Mô hình nghiên cứu RehabCTR-TCN đã train được trên GPU nhưng **chưa đạt product-ready**. Không được dùng kết quả hiện tại như bằng chứng lâm sàng.

## 2. Dữ liệu và provenance

| Hạng mục | Kết quả |
|---|---|
| Video nguồn trong index | 491 |
| Subjects | 10 |
| Source tồn tại/đúng root/không trùng | PASS |
| Extraction success | 202/491 (41.1%) |
| Extraction rejected | 289 |
| Rep annotation rows | 247 |
| Rep annotation approved | 0 |

289 extraction failures vẫn cần review; không tự động nới quality gate.

## 3. Đánh giá mô hình corrected

| Exercise | Valid folds | Skipped | Accuracy | Macro Precision | Macro Recall | Macro-F1 | Majority F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| HAND_OPENING | 5 | 5 | 0.5368 | 0.3661 | 0.5100 | 0.3646 | 0.3540 |
| ELBOW_EXTENSION | 4 | 6 | 0.2960 | 0.2105 | 0.5000 | 0.2392 | 0.4096 |

Diễn giải: `ELBOW_EXTENSION` hiện kém majority baseline; `HAND_OPENING` chỉ nhỉnh nhẹ. Kết quả có độ biến thiên lớn theo subject và nhiều fold không đủ hai lớp để đánh giá hợp lệ.

## 4. Chức năng đã kiểm tra

- 3-stream Joint/Bone/Motion, graph encoder, MS-TCN, attention pooling: PASS tensor smoke test.
- LOSO checkpoint riêng theo bài: PASS cho 9 fold hợp lệ.
- Metric corrected dùng `average="macro"`, confusion matrix và majority baseline: PASS.
- Rep MAE/boundary F1/temporal IoU: **CHƯA ĐÁNH GIÁ**, vì chưa có annotation start/end từng rep.
- Privacy/RAG/chat/session detail: đã có test ownership trước đó; toàn bộ test hiện tại vẫn PASS.

## 5. Trạng thái ứng dụng

- Frontend build: PASS (Vite/TypeScript).
- Backend health/runtime: không chạy trong lúc audit; cần khởi động lại trước khi demo.
- Ollama model `qwen2.5:7b`: có sẵn local.

## 6. Việc còn thiếu bắt buộc

1. Annotate và review `data/annotations/rep_annotations.csv` với `rep_id`, `start_frame`, `end_frame`, `completion_label`, `review_status=approved`.
2. Cân bằng Complete/Incomplete theo subject cho hai bài.
3. Chạy lại rep-level training và báo Rep MAE/Boundary F1/Temporal IoU.
4. Review 289 video extraction rejected; không dùng chúng trước khi quality gate mới được kiểm chứng.
5. Chỉ promote checkpoint vào app sau khi vượt majority baseline ổn định trên subject holdout.

## 7. Tệp bằng chứng

- `reports/phase_4_7/final_comprehensive_preflight.json`
- `experiments/rehab_ctr_tcn_corrected/loso_results.json`
- `reports/evaluation/REHAB_CTR_TCN_EVALUATION_CORRECTED.md`
- `logs/rehab_ctr_tcn_corrected_loso_visual.log`
- `data/annotations/rep_annotations.csv`
- `reports/evaluation/extraction_rescue_candidates.csv`
