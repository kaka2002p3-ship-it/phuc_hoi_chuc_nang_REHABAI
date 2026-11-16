# ELBOW_FLEXION — hàng đợi duyệt lại theo đa seed

Ngày: 2026-09-21  
Checkpoint được đối chiếu: seed `42`, `7`, `2026`.  
Mục đích: chọn các rep cần xem lại bằng video gốc; **không thay đổi nhãn chuyên gia**.

## Tóm tắt

| Mức | Tiêu chí | Test | Validation | Train | Tổng |
|---:|---|---:|---:|---:|---:|
| 1 | Nhãn chuyên gia `incorrect`, nhưng đa số 3 seed đoán `correct` | 15 | 9 | 27 | 51 |
| 2 | Nhãn `correct`, nhưng đa số đoán `incorrect` | 2 | 4 | 13 | 19 |
| 3 | Ba seed bất đồng | 11 | 8 | 43 | 62 |
| 4 | Xác suất gần ngưỡng quyết định (≤ 0.08) | 30 | 37 | 202 | 269 |
| **Tổng** |  | **58** | **58** | **285** | **401** |

## Thứ tự duyệt đề xuất

1. Duyệt toàn bộ **51 mẫu mức 1** trước. Đây là nhóm quan trọng nhất vì các mẫu `incorrect` đang bị bỏ sót.
2. Duyệt **19 mẫu mức 2** để tìm nhãn `correct` có thể gây nhiễu.
3. Nếu còn thời gian, duyệt mức 3 rồi mức 4. Ưu tiên `test` trước `val`, sau đó `train`.

## Cách dùng

Mở file CSV và tìm theo `source_video_path`. Xem đoạn từ `start_frame` đến `end_frame` (hoặc `start_time_s` đến `end_time_s` nếu có). Sau khi xem, chỉ điền hai cột cuối:

- `second_review_label`: `correct`, `incorrect` hoặc `uncertain`
- `second_review_notes`: lý do ngắn gọn, ví dụ “không duỗi hết khuỷu”, “cắt sai rep”, “góc quay che khuất”

Không ghi đè `completion_label`. Sau khi duyệt xong, cần tạo một file second-review riêng để kiểm tra và merge có kiểm soát.

## Tệp dữ liệu

- Hàng đợi: `data/annotations/elbow_flexion_multiseed_review_queue.csv`
- Nhãn gốc bất biến: `data/annotations/datanew_rep_expert_final.csv`
- Script tái tạo hàng đợi: `scripts/build_elbow_multiseed_review_queue.py`

Các cột `prob_correct_seed*`, `threshold_seed*`, `prediction_seed*`, `correct_votes` cho biết bằng chứng của từng seed. Đây là tín hiệu ưu tiên kiểm tra, không phải phán quyết thay cho chuyên gia.
