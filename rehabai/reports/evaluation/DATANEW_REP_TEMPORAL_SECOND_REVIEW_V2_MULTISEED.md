# Đánh giá temporal model sau second-review — 3 seed

Ngày: 2026-09-22  
Seeds: `42`, `7`, `2026`  
Protocol: split video-disjoint v2, 3-stream CTR-GCN + MS-TCN, 48 frames, supervised temporal learning.

## Kết quả test đa seed

| Bài tập | Accuracy mean ± SD | Macro-F1 mean ± SD | F1 `incorrect` mean ± SD | Recall `incorrect` mean ± SD |
|---|---:|---:|---:|---:|
| ELBOW_FLEXION | **0.9394 ± 0.0546** | **0.9301 ± 0.0603** | **0.9047 ± 0.0790** | **1.0000 ± 0.0000** |
| HAND_OPENING | 0.9386 ± 0.0076 | 0.8366 ± 0.0227 | 0.7075 ± 0.0417 | 0.5667 ± 0.0577 |

Giá trị theo seed của `ELBOW_FLEXION`:

- Macro-F1: `0.9454`, `0.8636`, `0.9812`
- Recall `incorrect`: `1.0000`, `1.0000`, `1.0000`
- Precision `incorrect`: `0.8571`, `0.6923`, `0.9474`

## Đánh giá

- `ELBOW_FLEXION` cải thiện rõ rệt và ổn định về recall lớp `incorrect`; không seed nào bỏ sót mẫu sai trong test v2.
- F1 `incorrect` vẫn dao động vừa phải do precision khác nhau giữa seed; seed 7 có nhiều false positive hơn.
- `HAND_OPENING` vẫn giữ chất lượng tương đương trước, nhưng recall `incorrect` trung bình chỉ `0.5667`.
- Kết quả là bằng chứng nghiên cứu tốt trên bộ nhãn second-review; chưa phải kiểm định lâm sàng hay fresh-subject validation.

## So sánh với baseline cũ

Baseline cũ của `ELBOW_FLEXION`: Macro-F1 `0.5103 ± 0.1107`, recall `incorrect` `0.1852 ± 0.1697`.  
V2: Macro-F1 `0.9301 ± 0.0603`, recall `incorrect` `1.0000 ± 0.0000`.

So sánh này phải ghi chú rằng v2 dùng nhãn đã second-review và split mới, nên không phải phép so sánh cùng test set.

## Quyết định triển khai

**Đạt baseline nghiên cứu để tiếp tục kiểm định. Chưa promote production.** Trước khi tích hợp vào ứng dụng cần:

1. Kiểm thử trên video/người hoàn toàn mới, không nằm trong các split v2.
2. Kiểm tra false positive của seed 7 và chọn threshold trên validation, không tối ưu trên test.
3. Chuẩn hóa tên bài `ELBOW_FLEXION`/`ELBOW_EXTENSION` giữa dataset, artifact, backend và prompt.
4. Tách rõ `incorrect` của mô hình khỏi kết luận kỹ thuật y khoa trong giao diện.

## Artifact

- Seed 42: `experiments/datanew_rep_temporal_second_review_v2_seed42/metrics.json`
- Seed 7: `experiments/datanew_rep_temporal_second_review_v2_seed7/metrics.json`
- Seed 2026: `experiments/datanew_rep_temporal_second_review_v2_seed2026/metrics.json`
- Log seed 42: `logs/datanew_rep_temporal_second_review_v2_seed42_visual.log`
- Log seed 7: `logs/datanew_rep_temporal_second_review_v2_seed7_visual.log`
- Log seed 2026: `logs/datanew_rep_temporal_second_review_v2_seed2026_visual.log`
