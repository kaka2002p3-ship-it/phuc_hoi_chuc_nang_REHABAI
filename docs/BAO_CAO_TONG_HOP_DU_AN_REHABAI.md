# BÁO CÁO TỔNG HỢP TOÀN BỘ DỰ ÁN REHABAI

> Ngày rà soát: 16/09/2026  
> Phạm vi: mã nguồn, cấu hình, báo cáo đánh giá, model artifact, manifest dữ liệu, pipeline huấn luyện/suy luận, frontend, backend, Docker và SQLite trong `D:\PhucHoiChucNangTay`.  
> Kết luận ngắn: hệ thống đã có đầy đủ chuỗi dữ liệu → huấn luyện → đánh giá LOSO → đóng gói TorchScript → suy luận web. Mô hình đang triển khai là **RehabMotionNet upper-limb v2**. Kết quả đáng tin cậy nhất của model production là **Accuracy 43,79% ± 23,35%** và **Macro-F1 35,44% ± 27,04%** trên strict subject-wise LOSO 10 fold/387 mẫu. Đây là mức nghiên cứu/demo, chưa đủ cho quyết định lâm sàng.

## 1. Cách đọc các con số trong báo cáo

- **Accuracy**: tỷ lệ dự đoán đúng tổng thể. Ví dụ 43,79% không có nghĩa mọi bệnh nhân đều đạt gần 43,79%, vì độ lệch giữa các fold rất lớn.
- **Macro-F1**: trung bình F1 của từng lớp với trọng số ngang nhau; phù hợp hơn Accuracy khi các lớp mất cân bằng hoặc một số bệnh nhân thiếu lớp.
- **Weighted-F1**: F1 có trọng số theo số mẫu từng lớp.
- Ký hiệu `x% ± y%` là trung bình ± độ lệch chuẩn giữa 10 fold LOSO.
- **LOSO (Leave-One-Subject-Out)**: mỗi fold giữ toàn bộ một bệnh nhân làm test, không để cùng bệnh nhân xuất hiện ở train và test. Đây là kết quả nên dùng để báo cáo khả năng tổng quát hóa.
- Các kết quả 100% ở artifact/model_v1 cũ chỉ phát sinh trên một tập kiểm thử cực nhỏ/không đủ lớp (`per_class_f1` chỉ có lớp 0), vì vậy **không phải độ chính xác production và không được dùng làm tuyên bố hiệu năng**.

## 2. Quy mô và cấu trúc dự án

### 2.1. Kiểm kê

| Khu vực | Số file xấp xỉ | Dung lượng | Vai trò |
|---|---:|---:|---|
| `rehabai/` | 20.753 | 1,382 GB | Mã nguồn, đặc trưng đã xử lý, checkpoint, artifact, báo cáo, app |
| `RehabAI_Datasets_FULL_VERIFIED/` | 10.589 | 157,184 GB | Kho dữ liệu gốc/đối chiếu, video, bảng dữ liệu, auxiliary datasets |
| Python trong phần dự án | 111 | 13.181 dòng | Training, evaluation, backend, test, scripts |
| JSON | 179 | 58.621 dòng | Kết quả, model config, provenance, schema |
| CSV | 90 | 28.541 dòng | Manifest, split, audit, kết quả theo mẫu/fold |
| Frontend TS/TSX/CSS | 10 | khoảng 641 dòng | Giao diện React |
| Test được phát hiện | 144 | — | 143 pass, 1 skip khi chạy đúng thư mục |

Kho dữ liệu nhị phân lớn được kiểm kê theo cây thư mục, manifest và hash/provenance; các file mã nguồn, cấu hình, báo cáo và schema liên quan trực tiếp được đọc/đối chiếu nội dung. Không có ý nghĩa thực tế khi in/đọc byte-by-byte toàn bộ hơn 157 GB video, checkpoint và bảng dữ liệu nhị phân vào báo cáo.

### 2.2. Các mô-đun chính

| Thư mục | Nội dung |
|---|---|
| `rehabai/shared/` | Schema đặc trưng, registry bài tập, chuẩn hóa, động học, augmentation, metric và provenance dùng chung |
| `rehabai/training/` | Dataset, loss, model, pretraining SimCLR, trainer, checkpoint, monitoring |
| `rehabai/scripts/` | Trích xuất, xử lý, tạo LOSO, train/evaluate, ablation, ensemble, audit và export |
| `rehabai/artifacts/` | `model_v1`, `model_v2`, ensemble nghiên cứu; TorchScript và metadata/hash |
| `rehabai/backend/` | FastAPI, REST, WebSocket inference, chatbot, SQLite/SQLAlchemy |
| `rehabai/frontend/` | React 19 + TypeScript + Vite; chọn bài, tập webcam, lịch sử, chatbot |
| `rehabai/deployment/`, `release/` | Docker Compose, image backend/frontend và bundle phát hành |
| `rehabai/reports/` | Kết quả LOSO, ablation, baseline, provenance, quyết định model |
| `RehabAI_Datasets_FULL_VERIFIED/` | Nguồn dữ liệu đã tải/xác minh và tài liệu chuẩn bị training |

## 3. Kiến trúc hệ thống và luồng hoạt động

```text
Video/webcam
  → MediaPipe Holistic (pose 33 điểm + tay trái/phải 21 điểm)
  → chuẩn hóa theo tâm vai và độ rộng vai
  → 12 đặc trưng động học
  → cửa sổ 96 frame × 237 feature
  → TorchScript RehabMotionNet v2
  → softmax phân loại 4 bài tập
  → WebSocket trả kết quả + skeleton + bộ đếm rep theo luật
  → React hiển thị thời gian thực
  → REST/SQLAlchemy lưu phiên tập vào SQLite
```

Frontend gửi ảnh JPEG 640×480 qua WebSocket ở mục tiêu 15 FPS. Backend dùng MediaPipe Holistic `model_complexity=1`, duy trì cửa sổ 96 frame và suy luận mỗi 5 frame sau khi đủ cửa sổ. Hệ thống kiểm tra tối thiểu vai, khuỷu, cổ tay; nếu tỷ lệ landmark hợp lệ dưới 60% thì yêu cầu người dùng điều chỉnh vị trí.

Backend có các endpoint:

| Phương thức | Endpoint | Mục đích |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/model-info` | Thông tin model đang nạp |
| GET | `/api/exercises` | Danh sách bài tập |
| POST | `/api/sessions` | Tạo phiên tập |
| GET | `/api/sessions` | Danh sách lịch sử |
| GET | `/api/sessions/{uuid}` | Chi tiết phiên |
| POST | `/api/sessions/{uuid}/finish` | Kết thúc phiên, lưu đau/rep/khuyến nghị |
| POST | `/api/chat` | Trợ lý bệnh nhân, có safety rule và OpenAI tùy chọn |
| WS | `/ws/inference` | Nhận frame và trả suy luận thời gian thực |

Chatbot ưu tiên các luật an toàn cục bộ cho dấu hiệu cấp cứu, tự hại, đau hoặc hạn chế vận động. Nếu có `OPENAI_API_KEY`, chatbot gọi Responses API với model mặc định `gpt-5-mini`; nếu không có hoặc gọi lỗi, hệ thống trả lời bằng rule-based local fallback. Model ngôn ngữ này độc lập với model nhận dạng vận động.

## 4. Dữ liệu

### 4.1. Tập chính Upper Limb Stroke

| Chỉ số | Giá trị |
|---|---:|
| Video nguồn trong inventory | 491 |
| Bệnh nhân | 10 (`01`–`10`) |
| Mẫu qua quality gate và xác minh provenance | 387 (78,82% inventory) |
| Mẫu bị loại/không vào đánh giá | 104 (21,18%) |
| Complete | 187 (48,32% của 387) |
| Incomplete | 200 (51,68% của 387) |

Phân bố 387 mẫu hợp lệ:

| Bài tập | Số mẫu | Tỷ lệ |
|---|---:|---:|
| Exercise 1 – Vai/nâng vật | 123 | 31,78% |
| Exercise 2 – Duỗi khuỷu | 65 | 16,80% |
| Exercise 3 – Nâng/gập duỗi cổ tay | 104 | 26,87% |
| Exercise 4 – Mở bàn tay | 95 | 24,55% |

Phân bố theo bệnh nhân sau quality gate: `01=42`, `02=51`, `03=44`, `04=59`, `05=71`, `06=44`, `07=20`, `08=20`, `09=16`, `10=20`. Sự chênh lệch này và việc fold 07–10 bị hạn chế độ phủ lớp là nguyên nhân chính khiến độ lệch chuẩn LOSO cao.

### 4.2. Dữ liệu ngoài dùng cho nghiên cứu pretraining/adapter

| Nguồn | Số feature/sample |
|---|---:|
| MobiPhysio | 2.740 |
| REHAB24-6 | 1.071 |
| Tổng external manifest | 3.811 |

Các nguồn ngoài chỉ được dùng trong các thí nghiệm pretraining/adapter/SSL. Kết quả hiện có không chứng minh chúng cải thiện ổn định so với production v2, nên không được promote.

Kho `RehabAI_Datasets_FULL_VERIFIED/04_Public_Auxiliary_2026` còn chứa IntelliRehabDS, stroke functional reaching, robot-aided kinematics và upper-limb perturbation. Đây là nguồn phụ trợ/audit; không nên cộng thẳng số file của chúng vào 387 mẫu đánh giá production.

### 4.3. Hợp đồng đặc trưng

Mỗi đầu vào model là tensor `96 × 237` float32:

- Pose: `33 × 3 = 99` giá trị `(x,y,z)`.
- Tay trái: `21 × 3 = 63`.
- Tay phải: `21 × 3 = 63`.
- Kinematics: 12 giá trị gồm góc vai trái/phải, góc khuỷu trái/phải, độ nghiêng thân, vận tốc góc tương ứng và vận tốc hai cổ tay.
- Tổng: `99 + 63 + 63 + 12 = 237`.

Pipeline offline còn lưu visibility, world landmark, mask, timestamp và frame index. Đầu vào inference thực tế bỏ visibility, chuẩn hóa tọa độ quanh trung điểm hai vai, chia theo độ rộng vai, chuẩn hóa z-score 12 kinematics bằng thống kê trong artifact, rồi ghép thành 237 chiều.

## 5. Các mô hình đã sử dụng

### 5.1. Mô hình chính RehabMotionNet

`RehabMotionNet` là mạng đa nhánh cho chuỗi chuyển động:

- **PoseGraphBranch**: xử lý cấu trúc đồ thị landmark pose; bản upper-limb chỉ chọn 6 node vai/khuỷu/cổ tay.
- **HandBranch**: Conv1D cho hai bàn tay, tổng cộng 126 chiều đầu vào.
- **KinematicBranch**: Conv1D cho 12 đặc trưng động học.
- **Multi-Scale TCN**: convolution theo thời gian với dilation 1/2/4 và residual để bắt chuyển động nhiều thang thời gian.
- **Attention pooling**: học trọng số frame quan trọng.
- **Hai head**: head phân loại 4 bài tập và head completion 1 giá trị.
- Pretraining contrastive dùng **SimCLR + NT-Xent loss** thông qua shared motion encoder.

Artifact production `model_v2/model.pt`:

| Thuộc tính | Giá trị |
|---|---|
| Tên/signature | `RehabMotionNet`, `rehab_motionnet_upper_limb_v2` |
| Phiên bản | 1.1 |
| Tham số TorchScript | 451.561 |
| Kích thước model | 1.904.228 byte (~1,82 MiB) |
| Input | `96 × 237` |
| Output chính | 4 lớp bài tập |
| Checkpoint đóng gói | Fold 04, test subject 04 |
| Train/val/test của fold đóng gói | 277 / 51 / 59 |
| SHA-256 model | `29350df8777e42e7bcb8f29600173cec3b706fdf8c40c6e305d76f4072c1c5de` |
| Trạng thái | Production/demo hiện tại |

File trong `release/model/model.pt` có cùng kích thước và SHA-256 với `artifacts/model_v2/model.pt`, tức bundle release khớp model production.

### 5.2. Các baseline và mô hình nghiên cứu khác

- Majority baseline.
- Linear SVM trên đặc trưng tổng hợp.
- MLP.
- LSTM và BiLSTM.
- TCN.
- Basic ST-GCN.
- CNN + Transformer (`RehabModel`).
- UpperLimb CTR-GCN.
- RehabMotionNet full, các biến thể ablation và Optimized-v1.
- Ensemble RehabMotionNet v2 + CTR-GCN.
- External-pretrained encoder/adapter với MobiPhysio và REHAB24-6.
- Teacher–student/pseudo-label.
- IntelliRehabDS self-supervised adapter.

## 6. Kết quả “% đạt được”

### 6.1. Kết quả chính thức của model production

Đánh giá trên 387 mẫu thật đã xác minh, strict subject-wise LOSO 10 fold, seed 42:

| Tác vụ/chỉ số | Trung bình | Độ lệch chuẩn | Min–max theo fold |
|---|---:|---:|---:|
| Nhận dạng bài tập – Accuracy | **43,79%** | 23,35% | 5,00–74,58% |
| Nhận dạng bài tập – Macro-F1 | **35,44%** | 27,04% | 2,38–73,92% |
| Nhận dạng bài tập – Weighted-F1 | 49,85% | 22,30% | 9,52–78,79% |
| Completion – Accuracy | 50,24% | 10,32% | 30,00–66,67% |
| Completion – Macro-F1 | 48,28% | 10,83% | 29,29–66,36% |

Ma trận nhầm lẫn gộp của 4 bài tập (`hàng = nhãn thật`, `cột = dự đoán`):

| Thật \ Dự đoán | Ex.1 | Ex.2 | Ex.3 | Ex.4 |
|---|---:|---:|---:|---:|
| Ex.1 | 57 | 12 | 14 | 40 |
| Ex.2 | 28 | 36 | 1 | 0 |
| Ex.3 | 12 | 0 | 69 | 23 |
| Ex.4 | 26 | 6 | 27 | 36 |

Nhìn theo recall từ ma trận trên: Ex.1 ≈46,34%, Ex.2 ≈55,38%, Ex.3 ≈66,35%, Ex.4 ≈37,89%. Ex.4 yếu nhất; Ex.1 thường bị nhầm sang Ex.4; Ex.4 thường bị nhầm sang Ex.1/Ex.3.

Head completion **không được promote lên production** vì không tốt hơn baseline nhị phân cân bằng. WebSocket cố ý không hiển thị/lưu nó như điểm lâm sàng; bộ đếm rep đang dùng luật động học riêng.

### 6.2. So sánh các mô hình chính cùng protocol

| Model | Macro-F1 bài tập | Accuracy bài tập | Ghi chú |
|---|---:|---:|---|
| Majority | 5,47% | 15,15% | Mốc tối thiểu |
| MLP | 27,79% | 34,51% | Baseline neural |
| Linear SVM | 28,80% | 36,51% | Baseline cổ điển |
| LSTM | 32,45% | 39,96% | Completion tốt hơn: F1 53,84%, acc 57,41% |
| **RehabMotionNet v2 production** | **35,44%** | **43,79%** | Model production hiện tại |
| Ensemble v1 research | 37,44% | 43,45% | Research-only; weights khác nhau theo fold |
| Optimized-v1 seed 42 | 39,45% | 48,37% | Tốt nhất một lần chạy nhưng được chọn sau khi xem ablation test |
| Optimized-v1, 3 seed | 38,64% | 47,65% | Trung bình mô tả trên 30 fold-seed; chỉ 10 subject độc lập |
| Ensemble 3 seed Optimized-v1 | 39,04% | 47,76% | Không vượt seed 42; chưa promote |

Optimized-v1 bỏ attention và contrastive trong cấu hình mục tiêu nhưng giữ pose, hand, kinematics và MS-TCN. Mức tăng seed 42 so với full v2 là khoảng **+4,01 điểm Macro-F1** và **+4,57 điểm Accuracy**. Tuy nhiên kiến trúc này được chọn sau khi đã xem kết quả test ablation seed 42, nên báo cáo dự án đúng khi xem đây là exploratory và yêu cầu xác nhận bằng cohort độc lập trước khi thay production.

### 6.3. Ablation RehabMotionNet, seed 42

| Biến thể | Macro-F1 | Accuracy | Completion Macro-F1 |
|---|---:|---:|---:|
| Full v2 | 35,44% | 43,79% | 48,28% |
| Bỏ hand | 28,11% | 35,79% | 49,10% |
| Bỏ kinematic | 33,65% | 46,10% | 52,73% |
| Bỏ contrastive | 36,55% | 50,15% | 50,78% |
| Bỏ MS-TCN | 36,27% | 48,64% | 50,21% |
| Bỏ attention | 37,63% | 46,53% | 47,37% |

Diễn giải: nhánh bàn tay có đóng góp rõ nhất cho nhận dạng bài tập. Attention và contrastive không cho lợi ích ổn định trên cohort nhỏ hiện tại; tuy vậy ablation này chưa đủ để kết luận chúng vô ích trên dữ liệu mới.

### 6.4. External pretraining/adapter

| Thử nghiệm | Macro-F1 bài tập | Accuracy |
|---|---:|---:|
| Pretrain REHAB24-only | 34,58% | 42,29% |
| Pretrain MobiPhysio-only | 33,98% | 41,61% |
| Pretrain combined | 30,03% | 37,68% |
| REHAB24 frozen adapter | 28,32% | 36,62% |
| MobiPhysio frozen adapter | 31,06% | 41,99% |
| Combined adapter | 24,94% | 39,90% |
| IntelliRehabDS SSL adapter | 35,99% | 45,29% |

Không phương án nào vượt rõ và ổn định Optimized-v1/reference. `production_changed=false` trong các báo cáo liên quan là quyết định hợp lý.

### 6.5. Cảnh báo về kết quả cũ 100%

`artifacts/model_v1/metrics.json` và `results/metrics.json` có một số Accuracy/Macro-F1 bằng 100%. Dấu hiệu trực tiếp cho thấy chúng không đại diện:

- `per_class_f1` của model_v1 chỉ chứa lớp `0`.
- AUROC ghi 0.
- Các baseline TCN/ST-GCN/RehabMotionNet cùng đạt 100% trên tập rất nhỏ, trong khi strict LOSO sau đó chỉ đạt 35–44%.
- Model card v2 đã thay thế kết quả cũ bằng 387 mẫu/10 subject.

Vì vậy khi trình bày dự án chỉ nên dùng bảng LOSO ở trên, tuyệt đối không quảng bá “AI chính xác 100%”.

## 7. Giao thức huấn luyện và chống leakage

- 10 fold subject-wise LOSO; mỗi fold có 1 subject test và 1 subject validation, các subject còn lại train.
- Checkpoint được chọn bằng validation, không chọn trực tiếp bằng test fold.
- Normalization được fit riêng trên train partition của từng fold.
- Manifest, normalization, provenance và registry có SHA-256; loader kiểm tra hash trước khi chạy.
- Seed chính 42; xác nhận thêm seed 7 và 2026 cho một số thí nghiệm.
- 387/387 mẫu đánh giá có trạng thái extraction `success` và provenance verified.
- Generalization gap trung bình của full v2 khoảng 36,85 điểm F1; fold 03, 06, 08 bị cảnh báo. Đây là bằng chứng overfitting/domain shift đáng lưu ý.
- Báo cáo nghiên cứu tự đánh dấu quyết định `E_DATASET_TOO_SMALL_OR_INSUFFICIENT_FOR_STRONG_CONCLUSION`.

## 8. Database SQL/SQLite

### 8.1. Công nghệ và vị trí

- ORM: SQLAlchemy 2.0.29.
- Engine: SQLite, `check_same_thread=False` để dùng trong FastAPI.
- File mặc định: `rehabai/backend/data/rehabai_sessions.db`.
- Có thể đổi bằng biến môi trường `REHABAI_DB_PATH`.
- Dung lượng file hiện tại: 16.384 byte.
- Dữ liệu hiện tại: **0 bản ghi**.
- Chỉ có một bảng nghiệp vụ: `sessions`.

### 8.2. Schema ORM mong muốn hiện tại

```sql
CREATE TABLE sessions (
    id               INTEGER PRIMARY KEY,
    session_uuid     VARCHAR NOT NULL UNIQUE,
    exercise_id      INTEGER NOT NULL,
    exercise_name    VARCHAR NOT NULL,
    start_time       DATETIME,
    end_time         DATETIME,
    completion_score FLOAT,
    target_reps      INTEGER,
    pain_before      INTEGER,
    pain_after       INTEGER,
    recommendation   VARCHAR,
    status           VARCHAR DEFAULT 'IN_PROGRESS',
    metrics          JSON
);

CREATE INDEX ix_sessions_id ON sessions (id);
CREATE UNIQUE INDEX ix_sessions_session_uuid ON sessions (session_uuid);
```

Ý nghĩa cột:

| Cột | Ý nghĩa |
|---|---|
| `id` | Khóa chính tăng theo SQLite |
| `session_uuid` | UUID duy nhất dùng trong API/WebSocket |
| `exercise_id`, `exercise_name` | Bài tập người dùng chọn |
| `start_time`, `end_time` | Thời điểm bắt đầu/kết thúc |
| `completion_score` | Điểm completion cũ/nullable; hiện không dùng làm điểm lâm sàng |
| `target_reps` | Số rep mục tiêu |
| `pain_before`, `pain_after` | Mức đau trước/sau do người dùng nhập |
| `recommendation` | Khuyến nghị rule-based sau buổi tập |
| `status` | `IN_PROGRESS` hoặc `COMPLETED` |
| `metrics` | JSON mở rộng, hiện lưu `rep_count` khi kết thúc |

### 8.3. Trạng thái schema vật lý được kiểm tra trực tiếp

File `.db` hiện có schema cũ:

```sql
CREATE TABLE sessions (
    id INTEGER NOT NULL,
    session_uuid VARCHAR NOT NULL,
    exercise_id INTEGER NOT NULL,
    exercise_name VARCHAR NOT NULL,
    start_time DATETIME,
    end_time DATETIME,
    completion_score FLOAT,
    status VARCHAR,
    metrics JSON,
    PRIMARY KEY (id)
);
```

Nó chưa có bốn cột `target_reps`, `pain_before`, `pain_after`, `recommendation`. Khi module `backend.core.db` được import/ứng dụng khởi động, code chạy `PRAGMA table_info` và `ALTER TABLE ... ADD COLUMN` cho bốn cột còn thiếu. Đây là migration ad-hoc, không phải hệ thống migration có version như Alembic. Do DB đang rỗng, việc đồng bộ schema hiện tại ít rủi ro, nhưng production nên có migration version hóa và backup.

### 8.4. Luồng ghi/đọc dữ liệu

- `POST /api/sessions`: sinh UUID, lưu bài tập, target reps, pain before, trạng thái `IN_PROGRESS`.
- WebSocket tra session để biết bài tập đã chọn và trả cờ `matches_selected`; code hiện không lưu completion score chưa được xác minh.
- `POST /api/sessions/{uuid}/finish`: lưu `pain_after`, thời gian kết thúc, `COMPLETED`, `metrics.rep_count`, và tạo khuyến nghị theo mức tăng đau.
- `GET /api/sessions`: trả lịch sử giảm dần theo `id`; frontend lấy tối đa 10 mục đầu để hiển thị danh sách gần đây và tổng hợp biểu đồ theo ngày.

### 8.5. Đánh giá thiết kế database

Điểm tốt:

- Schema nhỏ, phù hợp demo cục bộ.
- UUID unique, có index; JSON cho metric mở rộng.
- Docker bind-mount thư mục runtime giúp dữ liệu tồn tại sau khi container khởi động lại.

Hạn chế/rủi ro:

- Không có bảng `users/patients`, `clinicians`, kế hoạch điều trị hoặc audit log; mọi phiên dùng chung một kho.
- Không có foreign key cho bài tập; tên bài tập bị copy vào session.
- Không có validation DB-level cho `pain` (ví dụ 0–10), `target_reps`, trạng thái hoặc exercise 1–4.
- Không có timezone trong `DateTime`; code dùng UTC nhưng frontend phải hiểu đúng.
- Migration bằng `ALTER TABLE` thủ công không có version/rollback.
- Không có phân trang ở endpoint danh sách; sẽ chậm khi lịch sử lớn.
- SQLite phù hợp một máy/demo, không phù hợp tải ghi đồng thời cao hoặc hệ thống bệnh viện nhiều người dùng.
- CORS đang `allow_origins=["*"]`; cần khóa domain khi production.
- Database chứa dữ liệu sức khỏe (mức đau/lịch sử tập) nhưng chưa thấy authentication, authorization hay mã hóa cấp ứng dụng.

## 9. Frontend, backend và triển khai

### Frontend

- React 19.2.8, React Router 7.18.3, Recharts 3.10.1, Lucide React, TypeScript 6, Vite 8.
- Trang: Home, Exercise Selection, Practice, History; component PatientChat.
- Practice xin quyền webcam, tạo session, truyền frame, vẽ skeleton, đếm rep và ghi đau trước/sau.

### Backend

- FastAPI 0.110, Uvicorn 0.29, WebSockets 12, SQLAlchemy 2.0.29.
- MediaPipe 0.10.21, OpenCV headless, NumPy <2, PyTorch 2.2.2 CPU trong image inference.
- Training lock dùng PyTorch 2.7.0 CUDA 12.6; môi trường train và runtime khác phiên bản, nhưng artifact TorchScript hiện tải được trong môi trường kiểm tra.

### Docker

- Backend mount read-only `artifacts/model_v2` và bind-mount SQLite runtime.
- Backend port 8000, frontend/Nginx port 8080.
- Healthcheck `/api/health` mỗi 30 giây.
- Model bundle có registry hash và bundle hash; loader fail-fast khi config, feature contract hoặc hash sai.

## 10. Kiểm thử và trạng thái kỹ thuật

Lệnh xác minh chạy ngày 16/09/2026 từ `rehabai/`:

```powershell
python -m pytest tests shared/tests -q
```

Kết quả: **143 passed, 1 skipped, 15 warnings trong 11,40 giây**. Cảnh báo chủ yếu là deprecation từ Matplotlib/PyParsing và một cảnh báo tối ưu Transformer `batch_first`.

Nếu chạy pytest từ thư mục cha mà không đặt `PYTHONPATH`/working directory, collection lỗi vì import tuyệt đối `training`, `shared`, `scripts`, `backend`. README cũng yêu cầu chạy ứng dụng với `PYTHONPATH=.` từ thư mục dự án. Nên đóng gói project bằng `pyproject.toml` hoặc cấu hình pytest để việc chạy test không phụ thuộc cwd.

Audit compliance V3.1 hiện ghi **8/8 check pass** (registry, upper-limb LOSO, artifact v2, backend, frontend, compose, release, reproducibility manifest). “Pass” này là pass về sự tồn tại/tuân thủ pipeline, không đồng nghĩa model đạt độ chính xác lâm sàng.

## 11. Vấn đề và rủi ro quan trọng

1. **Dữ liệu quá nhỏ:** chỉ 10 subject độc lập; 387 sample không thay thế số lượng bệnh nhân. Các window/video từ cùng bệnh nhân có tương quan cao.
2. **Biến thiên rất lớn:** Accuracy LOSO có fold từ 5% đến 74,58%; Macro-F1 từ 2,38% đến 73,92%. Model chưa ổn định trên bệnh nhân mới.
3. **Thiếu lớp theo subject:** các fold 07–10 có restricted exercise coverage, khiến metric theo fold và trung bình dễ dao động.
4. **Overfitting:** generalization gap trung bình ~36,85 điểm, nhiều fold bị cảnh báo.
5. **Completion chưa hợp lệ để dùng lâm sàng:** accuracy khoảng mức ngẫu nhiên/cân bằng; đã được tắt đúng cách ở production response.
6. **Không có nhãn lỗi động tác từ chuyên gia:** hệ thống không thể tuyên bố sửa lỗi kỹ thuật hay chấm đúng/sai lâm sàng.
7. **Model production là checkpoint một fold:** bundle chọn fold 04 để demo; metric báo cáo là trung bình LOSO, không phải metric riêng của một “model cuối” được train trên toàn bộ cohort. Cần chiến lược final training/calibration rõ trước triển khai thật.
8. **Schema database lệch phiên bản:** code có tự vá cột, nhưng thiếu migration chính thức.
9. **Bảo mật ứng dụng còn mức demo:** CORS mở, chưa có đăng nhập/phân quyền, chưa có chính sách dữ liệu sức khỏe.
10. **Encoding tài liệu/source hiển thị mojibake ở một số công cụ:** nhiều chuỗi UTF-8 tiếng Việt bị đọc như Latin-1 trong output terminal. Cần chuẩn hóa UTF-8 và kiểm tra UI/container.
11. **README có lệnh training cũ:** README trỏ `training/scripts/train.py` và config mặc định không trùng layout hiện tại (`training/train.py`, các config/eval riêng). Tài liệu vận hành cần cập nhật.

## 12. Khuyến nghị theo mức ưu tiên

### P0 – trước mọi thử nghiệm với bệnh nhân thật

- Gắn rõ nhãn “research/demo, không dùng chẩn đoán hoặc thay chuyên viên”.
- Không công bố số 100%; dùng strict LOSO 43,79% Accuracy / 35,44% Macro-F1 cùng khoảng biến thiên.
- Thêm authentication, phân quyền bệnh nhân/chuyên viên, HTTPS, giới hạn CORS, consent và chính sách lưu/xóa dữ liệu.
- Thêm validation pain 0–10, target rep hợp lý; không để chatbot/model tạo chỉ định điều trị cá nhân.

### P1 – cải thiện khoa học mô hình

- Thu thập cohort độc lập lớn hơn, cân bằng đủ 4 bài cho từng subject và đa dạng camera/ánh sáng/mức suy giảm.
- Đóng băng trước protocol/model selection; xác nhận Optimized-v1 trên tập bệnh nhân hoàn toàn mới.
- Báo cáo confidence interval theo subject/bootstrap và metric per-class/per-subject.
- Có chuyên gia phục hồi chức năng gán nhãn chất lượng/lỗi động tác và đánh giá inter-rater agreement.
- Calibrate confidence; cho phép “không chắc/không thuộc 4 lớp” thay vì luôn ép dự đoán một bài.
- Đánh giá latency end-to-end trên phần cứng mục tiêu, không chỉ latency model cũ.

### P2 – cải thiện phần mềm/vận hành

- Dùng Alembic; version schema và backup DB.
- Khi nhiều người dùng, chuyển PostgreSQL; thêm bảng patient/user/program/session-event/model-version.
- Đóng gói Python bằng `pyproject.toml`, cấu hình pytest và CI để không phụ thuộc working directory.
- Đồng bộ/kiểm thử chéo phiên bản Torch training 2.7 và inference 2.2.
- Cập nhật README, thêm model registry/version hiển thị trong mỗi session và log inference có kiểm soát riêng tư.
- Thêm pagination, retention policy, export/delete dữ liệu bệnh nhân và monitoring lỗi model/data drift.

## 13. Kết luận cuối

RehabAI là một prototype nghiên cứu khá hoàn chỉnh về mặt kỹ thuật: có provenance, quality gate, subject-wise LOSO, nhiều baseline/ablation, hash artifact, TorchScript inference, web realtime, chatbot safety fallback, Docker và test suite đang pass. Điểm mạnh lớn nhất là dự án đã tự sửa cách đánh giá từ kết quả cũ dễ gây leakage/ảo tưởng 100% sang strict LOSO trên dữ liệu thật.

Tuy nhiên hiệu năng hiện tại vẫn thấp và rất không ổn định giữa bệnh nhân. Con số đại diện cần ghi nhớ là **43,79% Accuracy và 35,44% Macro-F1 cho nhận dạng 4 bài tập**; completion chỉ khoảng **50,24% Accuracy** và không được dùng production. Do chỉ có 10 bệnh nhân, hệ thống phù hợp cho **demo/nghiên cứu**, chưa đủ bằng chứng cho triển khai lâm sàng hoặc đưa ra đánh giá chất lượng phục hồi.

## 14. Nguồn nội bộ chính đã đối chiếu

- `rehabai/artifacts/model_v2/{model_card.md,metrics.json,model_config.json,fold_metadata.json}`
- `rehabai/release/model/` và hash của model release/production
- `rehabai/reports/evaluation/phase_4_7_real_data_summary.json`
- `rehabai/reports/evaluation/phase_4_7_baseline_summary.json`
- `rehabai/reports/evaluation/ablation_summary.json`
- `rehabai/reports/evaluation/optimized_v1_summary.json`
- `rehabai/reports/evaluation/multiseed_confirmation_summary.json`
- `rehabai/reports/evaluation/optimized_v1_multiseed_ensemble_summary.json`
- `rehabai/reports/evaluation/{external_pretraining_ablation_summary.json,external_adapter_summary.json,intellirehab_ssl_adapter_summary.json}`
- `rehabai/data/indexes/upper_limb_master.csv`
- `rehabai/data/stage3_upper_limb/indexes/provenance_verified.csv`
- `rehabai/data/external_pretraining_v1/*.csv`
- `rehabai/training/models/*.py`, trainer/dataset/loss/pretraining code
- `rehabai/shared/` preprocessing, metrics, schema, registry và test
- `rehabai/backend/` REST, WebSocket, model loader, MediaPipe extractor, rep counter và database
- `rehabai/frontend/src/`, package config và Docker Compose
- SQLite vật lý `rehabai/backend/data/rehabai_sessions.db`, kiểm tra bằng `sqlite_master` và `PRAGMA table_info`

