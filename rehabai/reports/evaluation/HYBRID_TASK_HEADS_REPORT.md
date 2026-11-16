# Hybrid task-specific heads — research evaluation

**Status:** RESEARCH CANDIDATE / NOT PRODUCTION  
**Protocol:** strict 10-fold subject-wise LOSO, unchanged 387 test samples  
**Artifact:** `loso_hybrid_optimized_exercise_datanew_completion.json`

## Phương án

- Exercise head: `optimized_v1`, seed 42 — cấu hình bỏ attention và contrastive branch.
- Completion head: `datanew_ssl_all_full`, seed 42 — SSL pretraining trên 619 video datanew.
- Hai model được nạp theo cùng fold/test manifest; không chọn checkpoint dựa trên test fold.
- Đây là đánh giá hai task head độc lập, không phải một checkpoint đơn duy nhất.

## Kết quả

| Candidate | Exercise Macro-F1 | Exercise accuracy | Completion Macro-F1 | Completion accuracy |
|---|---:|---:|---:|---:|
| Baseline v2 | 0.3544 | 0.4379 | 0.4828 | 0.5024 |
| Optimized-v1 | 0.3945 | 0.4837 | 0.5096 | 0.5202 |
| Datanew combined | 0.3718 | 0.4646 | 0.5606 | 0.5803 |
| **Hybrid** | **0.3945** | **0.4837** | **0.5606** | **0.5803** |

Hybrid delta so với baseline:

- Exercise Macro-F1: **+0.0401**.
- Exercise accuracy: **+0.0457**.
- Completion Macro-F1: **+0.0778**.
- Completion accuracy: **+0.0779**.

Hybrid thắng/hòa/thua theo fold:

- Exercise Macro-F1: `4/1/5`.
- Exercise accuracy: `4/1/5`.
- Completion Macro-F1: `5/1/4`.
- Completion accuracy: `5/2/3`.

Kết quả hybrid khớp chính xác với exercise metrics của optimized-v1 và completion metrics của datanew combined, nên không có lỗi ghép nhầm thứ tự sample.

## Đánh giá và quyết định

Đây là phương án khả quan nhất trong các artifact hiện có vì đạt đồng thời exercise tốt nhất và completion tốt nhất. Tuy nhiên, nó vẫn chưa phải production model:

- Exercise vẫn có fold 08 Macro-F1 `0.0000` và fold 07/09/10 rất thấp.
- Completion mới dùng seed 42 trong hybrid; multi-seed đã cho tín hiệu tốt nhưng chưa được ghép thành một mô hình production.
- Chưa có fresh-subject/prospective validation.
- Runtime là `torch 2.5.1+cu121`, profile exploratory.
- Hai task head dùng hai checkpoint khác nhau; cần tích hợp runtime có kiểm soát trước khi triển khai.

**Gate:**

| Gate | Kết quả |
|---|---|
| Strict LOSO và artifact integrity | PASS |
| Tổ hợp metric tốt nhất hiện có | PASS |
| Exercise ổn định trên subject mới | FAIL — chưa kiểm chứng |
| Completion đủ bằng chứng promotion | FAIL |
| Production/clinical readiness | FAIL |

## Khuyến nghị triển khai tiếp theo

1. Giữ production hiện tại không đổi.
2. Dùng hybrid này làm research reference.
3. Chạy fresh-subject validation cho cả hai head với cùng pipeline runtime.
4. Nếu fresh-subject đạt gate, mới đóng gói một `HybridTaskHeads` artifact có metadata và calibration riêng cho từng task.

