# Audit nhãn chuyên gia datanew — 2026-09-20

## Kết quả kiểm tra cấu trúc

| Kiểm tra | Kết quả |
|---|---:|
| Dòng trong hàng đợi | 921 |
| Dòng đã gắn nhãn | 921 |
| Video duy nhất | 179 |
| Khóa `video_id + rep_id` trùng | 0 |
| Thiếu dòng so với hàng đợi | 0 |
| Dòng thừa ngoài hàng đợi | 0 |
| Frame kết thúc không hợp lệ | 0 |
| Người gắn nhãn | `PT_01` |
| Validation schema | PASS |

Lệnh validation đã chạy thành công:

```text
PASS rows=921 confirmed=901 uncertain=20
```

## Phân bố nhãn

| Bài tập | Correct | Incorrect | Uncertain | Tổng |
|---|---:|---:|---:|---:|
| `ELBOW_FLEXION` | 365 | 17 | 19 | 401 |
| `HAND_OPENING` | 515 | 4 | 1 | 520 |
| **Tổng** | **880** | **21** | **20** | **921** |

Tỷ lệ trên các nhãn đã kết luận (`correct`/`incorrect`) là `97.7% correct` và `2.3% incorrect`. Riêng `HAND_OPENING` chỉ có 4 mẫu `incorrect`; đây là mất cân bằng rất mạnh.

## Phân bố nguồn

| Bài tập | ex1 | ex2 | ex3 |
|---|---:|---:|---:|
| `ELBOW_FLEXION` | 114 | 227 | 60 |
| `HAND_OPENING` | 120 | 311 | 89 |

`ex1/ex2/ex3` hiện là nhóm nguồn, chưa được xác nhận là subject độc lập. Không dùng chúng như LOSO subject nếu chưa có mapping người tập.

## Đánh giá khả năng train

- **Đủ điều kiện kỹ thuật để lưu nhãn:** PASS.
- **Đủ điều kiện train phân loại correctness cân bằng:** BLOCKED/WEAK.
- Nguyên nhân: lớp `incorrect` quá ít, đặc biệt `HAND_OPENING` (4 mẫu), và chỉ có một annotator nên chưa đo được độ đồng thuận liên chuyên gia.
- Không nên oversample/nhân bản 4 mẫu rồi báo F1 như bằng chứng tin cậy.

## Khuyến nghị trước khi train chính thức

1. Bổ sung hoặc chọn có chủ đích thêm các lần `incorrect`, đặc biệt cho `HAND_OPENING`; mục tiêu nghiên cứu tối thiểu nên có khoảng 30–50 mẫu mỗi lớp mỗi bài, phân bố trên nhiều subject.
2. Duyệt độc lập 20–30% dữ liệu bằng annotator thứ hai để đo Cohen's Kappa hoặc adjudication.
3. Xác định subject thật từ metadata nguồn; không coi `ex1/ex2/ex3` là subject mặc định.
4. Giữ 20 `uncertain` ngoài tập train chính; chỉ dùng cho phân tích chất lượng.
5. Sau khi cân bằng và xác định subject, chạy train visual với split theo subject và báo baseline/CI.

## Artifact

- Nhãn người duyệt: `data/annotations/datanew_rep_reviewed.csv`
- Hàng đợi gốc: `data/annotations/datanew_rep_review_queue.csv`
- Validator: `scripts/validate_datanew_reviews.py`
- Nhãn heuristic cũ (không dùng làm ground truth): `data/annotations/datanew_rep_auto_experimental.csv`
