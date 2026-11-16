# Đánh giá temporal model sau second-review — seed 42

Ngày: 2026-09-22  
Protocol: video-disjoint, 3-stream CTR-GCN + MS-TCN, 48 frames, supervised temporal learning.

## Kết quả test

| Bài tập | Accuracy | Macro-F1 | F1 `incorrect` | Recall `incorrect` | Số mẫu test |
|---|---:|---:|---:|---:|---:|
| ELBOW_FLEXION | **0.9545** | **0.9454** | **0.9231** | **1.0000** | 66 |
| HAND_OPENING | 0.9474 | 0.8603 | 0.7500 | 0.6000 | 76 |

### Ma trận nhầm lẫn ELBOW_FLEXION

```text
                 Dự đoán incorrect   Dự đoán correct
Thực incorrect              18                  0
Thực correct                 3                 45
```

Mô hình phát hiện đủ 18/18 mẫu `incorrect` trong test; có 3 mẫu `correct` bị cảnh báo nhầm.

## So với lần train trước

Lần trước trên bộ nhãn/split cũ, `ELBOW_FLEXION` có Macro-F1 `0.5103 ± 0.1107` và recall `incorrect` `0.1852 ± 0.1697` qua ba seed. Lượt hiện tại đạt Macro-F1 `0.9454`, recall `incorrect` `1.0000` ở seed 42.

Không được coi đây là so sánh hoàn toàn cùng điều kiện: nhãn đã được second-review và split v2 được tạo lại theo video. Vì vậy kết quả cho thấy tín hiệu rất tích cực, nhưng chưa chứng minh khả năng tổng quát hóa trên người/video mới.

## Đánh giá

- **Nghiên cứu:** đạt tốt ở seed 42; dữ liệu `ELBOW_FLEXION` sau duyệt có khả năng phân biệt rõ hơn.
- **Độ tin cậy:** chưa đủ kết luận vì mới có một seed và chỉ có 18 mẫu incorrect trong test.
- **Production:** chưa được phép promote. Cần chạy seed `7` và `2026`, sau đó đánh giá trên người/buổi quay mới hoàn toàn.
- **An toàn:** không diễn giải `incorrect` thành chẩn đoán hoặc khẳng định kỹ thuật y khoa nếu chưa có kiểm định chuyên gia độc lập.

## Artifact và log

- Metrics: `experiments/datanew_rep_temporal_second_review_v2_seed42/metrics.json`
- Checkpoint ELBOW_FLEXION: `experiments/datanew_rep_temporal_second_review_v2_seed42/elbow_flexion.pth`
- Checkpoint HAND_OPENING: `experiments/datanew_rep_temporal_second_review_v2_seed42/hand_opening.pth`
- Log terminal: `logs/datanew_rep_temporal_second_review_v2_seed42_visual.log`

## Bước kế tiếp bắt buộc

Chạy lại cùng split v2 với seed `7` và `2026`, không thay đổi test manifest hay threshold protocol. Chỉ xem xét checkpoint ổn định nếu cả ba seed giữ recall `incorrect` cao và không có seed collapse.
