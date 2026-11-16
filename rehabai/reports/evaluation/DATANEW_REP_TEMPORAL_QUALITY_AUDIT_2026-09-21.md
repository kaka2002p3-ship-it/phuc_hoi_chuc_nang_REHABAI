# Đánh giá chất lượng temporal model datanew — 2026-09-21

## Phân loại đúng phương pháp

Pipeline vừa chạy là **supervised temporal learning** với nhãn chuyên gia, không phải reinforcement learning (RL). Nó không có agent, environment, action hoặc reward loop. Không nên gọi kết quả này là “đạt RL”.

## Protocol

- 920 repetition đã xác nhận; 1 `uncertain` loại khỏi train/val/test.
- Split cố định theo `video_id`, không có video trùng giữa các split.
- 48 frame/repetition từ NPZ đã trích xuất sẵn.
- 3-stream Joint/Bone/Motion + CTR-GCN/MS-TCN.
- Weighted sampler trên train.
- Threshold được chọn trên validation (`0.25` elbow, `0.35` hand).
- Seed: `42`; device: CUDA.

## Kết quả test

| Bài tập | Accuracy | Macro-F1 | Incorrect F1 | Incorrect recall | Test reps | Test videos |
|---|---:|---:|---:|---:|---:|---:|
| `ELBOW_FLEXION` | 0.7241 | 0.6234 | 0.4286 | 0.3333 | 58 | 7 |
| `HAND_OPENING` | 0.9474 | 0.8603 | 0.7500 | 0.6000 | 76 | 19 |

## So với summary-feature baseline cùng split

| Bài tập | Baseline Macro-F1 | Temporal Macro-F1 | Delta |
|---|---:|---:|---:|
| `ELBOW_FLEXION` | 0.2435 | 0.6234 | +0.3799 |
| `HAND_OPENING` | 0.5177 | 0.8603 | +0.3426 |

Đây là tín hiệu cải thiện rõ ràng của việc dùng chuỗi landmark. Tuy nhiên đây mới là một seed và cùng một bộ dữ liệu đã được gắn nhãn; không phải xác nhận độc lập.

## Đánh giá chất lượng

- **Pipeline kỹ thuật:** PASS.
- **Tín hiệu nghiên cứu:** PROMISING.
- **Đủ để production:** NO.
- **Đủ để gọi là RL:** NO — đây là supervised temporal model.

Lý do chưa production:

1. Mới có một seed và một split cố định.
2. Chưa có fresh-subject validation hoặc kiểm định đa trung tâm.
3. `ELBOW_FLEXION` incorrect recall chỉ `0.3333`; còn bỏ sót 2/3 mẫu incorrect.
4. Nhãn do hai vòng duyệt nhưng chưa có đo Cohen's Kappa/adjudication độc lập có cấu trúc.
5. Feature/model chưa tích hợp vào artifact production 2 bài (`ELBOW_EXTENSION`, `HAND_OPENING`).
6. `ELBOW_FLEXION` vẫn là ontology khác `ELBOW_EXTENSION`.

## Kết luận

Temporal model hiện **đạt chất lượng thử nghiệm tốt hơn baseline**, đặc biệt với `HAND_OPENING`. Nó chưa đạt ngưỡng an toàn để thay thế model production hoặc đưa ra kết luận “động tác đúng/sai” lâm sàng. Bước tiếp theo là chạy thêm seeds `7` và `2026`, kiểm tra calibration/recall lớp incorrect, sau đó mới cân nhắc ablation và fresh-subject test.

Artifact: `experiments/datanew_rep_temporal_seed42/metrics.json`  
Log: `logs/datanew_rep_temporal_seed42_visual.log`
