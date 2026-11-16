# Kiểm toán dữ liệu bài tập `datanew`

**Ngày kiểm toán:** 2026-09-20  
**Phạm vi:** video cục bộ `ex1`, `ex2`, `ex3`; EHW RGB; kết quả trích xuất và SSL hiện có.  
**Kết luận:** dữ liệu đã được trích xuất; không cần chạy lại. Dữ liệu chưa có nhãn đúng/sai đã kiểm duyệt nên không được dùng trực tiếp để train bộ phân loại độ chính xác động tác.

## 1. Kho video cục bộ

Catalog chuẩn hóa có 238 video. Tên thư mục nguồn được giữ nguyên, SHA-256 của video được lưu để truy xuất nguồn gốc.

| Bài tập chuẩn hóa | Tổng | Ready | Thiếu pose quá mức | Quá ngắn/không mở được |
|---|---:|---:|---:|---:|
| `HAND_OPENING` | 159 | 127 | 9 | 23 |
| `ELBOW_FLEXION` | 79 | 52 | 12 | 15 |
| **Tổng** | **238** | **179** | **21** | **38** |

`Gập khuỷu tay` được ánh xạ thành `ELBOW_FLEXION` (gập khuỷu), không phải `ELBOW_EXTENSION` (duỗi khuỷu). Vì vậy 52 mẫu ready này không được nhập vào lớp duỗi khuỷu hiện tại.

Các trường `completion_label` vẫn là `unknown` và `label_status` là `pending`. Trạng thái `ready` chỉ nói rằng đặc trưng pose đạt tiêu chuẩn kỹ thuật; nó không có nghĩa là người tập thực hiện đúng.

## 2. EHW

- Có 240 video RGB, gồm 10 chủ thể: `X02`, `X03`, `X04`, `X06`, `X07`, `X09`, `X10`, `X11`, `X12`, `X13`.
- Sáu mã protocol `OCF1`, `OCF2`, `OCN1`, `OCN2`, `OCS1`, `OCS2` có 40 video mỗi mã.
- File trigger hiện có thuộc `X01`, `X05`, `X08`; tập chủ thể này không giao với chủ thể video.
- Do không thể nối trigger với video tương ứng, `exercise=UNKNOWN`, `completion_label=unknown` và `boundary_label_status=unlinked_pending` được giữ nguyên.
- Trường `Gesture` trong trigger không được diễn giải thành nhãn đúng/sai.

## 3. Trạng thái trích xuất

Manifest tổng có 619 mẫu `ready`, gồm các thư mục đặc trưng:

| Nguồn đặc trưng | Số mẫu |
|---|---:|
| `features` | 200 |
| `features_ehw` | 240 |
| `features_ex1` | 36 |
| `features_ex2` | 114 |
| `features_ex3` | 29 |
| **Tổng** | **619** |

`features_local` có 12 bản sao kiểm tra và không được cộng thêm vào manifest 619 mẫu. Không chạy lại trích xuất để tránh tốn thời gian và tạo artifact trùng.

## 4. Kết quả SSL đa seed hiện có

| Mô hình | Exercise Macro-F1 | Exercise accuracy | Completion Macro-F1 | Completion accuracy |
|---|---:|---:|---:|---:|
| Baseline v2 | 0.3544 | 0.4379 | 0.4828 | 0.5024 |
| Trung bình seed 42, 7, 2026 | 0.3460 | 0.4353 | 0.5444 | 0.5663 |
| Chênh lệch | -0.0084 | -0.0027 | +0.0616 | +0.0638 |

Nhánh completion là ứng viên nghiên cứu vì kết quả tăng ở cả ba seed, nhưng kiểm định Wilcoxon trên 10 chủ thể có `p=0.1055`; chưa đủ bằng chứng để đưa vào production. Nhánh exercise không thay được baseline.

## 5. Quyết định và bước tiếp theo

1. Giữ 127 mẫu `HAND_OPENING` ready cho SSL/pretraining hoặc nghiên cứu chất lượng; không tự tạo nhãn đúng/sai.
2. Xây `ELBOW_FLEXION` thành bài tập mới nếu sản phẩm cần bài gập khuỷu; không trộn với `ELBOW_EXTENSION`.
3. Muốn train supervised đúng/sai, phải duyệt và gán nhãn từng lần lặp theo người tập, đồng thời tách train/test theo subject.
4. EHW chỉ có thể dùng cho boundary có giám sát sau khi có trigger đúng chủ thể/video hoặc annotation mới.
5. Chưa promote model hiện tại lên production; cần đánh giá trên chủ thể mới theo protocol định trước.

## 6. Artifact kiểm toán

- `data/datanew_unlabeled/datanew_exercise_catalog.csv`: catalog 238 video, hash nguồn và trạng thái trích xuất.
- `data/datanew_unlabeled/ehw_video_catalog.csv`: catalog 240 video EHW.
- `data/datanew_unlabeled/combined_ready_manifest.csv`: 619 mẫu ready dùng cho SSL hiện tại.
- `reports/evaluation/DATANEW_MULTISEED_EVALUATION.md`: đánh giá ba seed và production gate.

Lệnh dựng lại catalog (nhẹ, không phải trích xuất/train):

```powershell
cd D:\PhucHoiChucNangTay\rehabai
python scripts\catalog_datanew_exercises.py `
  --source-root ..\datanew `
  --output data\datanew_unlabeled\datanew_exercise_catalog.csv `
  --manifest data\datanew_unlabeled\extraction_ex1_manifest.csv `
             data\datanew_unlabeled\extraction_ex2_manifest.csv `
             data\datanew_unlabeled\extraction_ex3_manifest.csv
```
