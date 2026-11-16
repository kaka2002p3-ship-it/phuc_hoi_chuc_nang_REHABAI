# Báo cáo đa seed mô hình temporal RehabAI

Ngày: 2026-09-21  
Phạm vi: tập `datanew` đã duyệt, chia video-disjoint cố định, 3 seed `42, 7, 2026`.  
Mô hình: 3-stream CTR-GCN + MS-TCN, 48 frame, học có giám sát theo chuỗi thời gian.

## Kết quả test theo bài tập

| Bài tập | Accuracy (mean ± SD) | Macro-F1 (mean ± SD) | F1 incorrect (mean ± SD) | Recall incorrect (mean ± SD) |
|---|---:|---:|---:|---:|
| ELBOW_FLEXION | 0.6724 ± 0.0517 | 0.5103 ± 0.1107 | 0.2317 ± 0.2164 | 0.1852 ± 0.1697 |
| HAND_OPENING | 0.9430 ± 0.0076 | 0.8517 ± 0.0149 | 0.7353 ± 0.0255 | 0.6000 ± 0.0000 |

Gộp trung bình hai bài theo từng seed: Macro-F1 `0.6810 ± 0.0618`, Accuracy `0.8077 ± 0.0261`.

## Diễn giải

- `HAND_OPENING`: kết quả ổn định giữa các seed; test Macro-F1 0.8344–0.8603 và F1 lớp `incorrect` 0.7059–0.7500. Có thể dùng làm mốc nghiên cứu tiếp theo, nhưng recall `incorrect` mới 0.60 nên chưa phải mức an toàn lâm sàng.
- `ELBOW_FLEXION`: chưa đạt. Macro-F1 dao động 0.4021–0.6234; recall `incorrect` là 0.3333, 0.0000 và 0.2222. Mô hình thường đoán “correct”, bỏ sót các lần tập sai.
- Accuracy tổng thể không đủ để kết luận chất lượng vì dữ liệu lệch lớp mạnh (`correct` nhiều hơn `incorrect`), đặc biệt ở `HAND_OPENING`.

## Kết luận chất lượng

Đây là **supervised temporal learning**, không phải reinforcement learning. Kết quả hiện tại phù hợp cho nghiên cứu/so sánh mô hình, **chưa đủ điều kiện đưa vào sản phẩm hoặc dùng như cảnh báo y khoa**. Cổng triển khai vẫn bị chặn bởi:

1. Recall lớp `incorrect` của `ELBOW_FLEXION` quá thấp và không ổn định.
2. Chưa có kiểm định trên người/buổi quay hoàn toàn mới ngoài split hiện tại.
3. Cần tăng số mẫu `incorrect`, đặc biệt cho `ELBOW_FLEXION`, và đánh giá theo subject/video độc lập.

## Tệp bằng chứng

- Seed 42: `experiments/datanew_rep_temporal_seed42/metrics.json`
- Seed 7: `experiments/datanew_rep_temporal_seed7/metrics.json`
- Seed 2026: `experiments/datanew_rep_temporal_seed2026/metrics.json`
- Log seed 7: `logs/datanew_rep_temporal_seed7_visual.log`
- Log seed 2026: `logs/datanew_rep_temporal_seed2026_visual.log`

## Việc nên làm tiếp theo

Thu thập thêm các rep `ELBOW_FLEXION/incorrect` đã được chuyên gia xác nhận, giữ nguyên video-disjoint split, sau đó huấn luyện lại và báo cáo thêm PR-AUC/recall lớp `incorrect`. Không tự động đổi nhãn hoặc đưa checkpoint hiện tại vào production.
