# REHABAI / REHAB-MOTIONNET — MASTER IMPLEMENTATION PROMPT V3.1 — RTX 4060 LAPTOP 8GB — MANUAL UPPER-LIMB EXTRACT

## 0. MỤC TIÊU CUỐI CÙNG

Xây dựng một sản phẩm RehabAI chạy thời gian thực bằng camera RGB, đồng thời đủ chặt chẽ để dùng làm đề tài nghiên cứu khoa học và viết bài báo.

Sản phẩm phải:
- nhận diện bài tập chi trên;
- giữ cố định tên, ID và thứ tự bài tập;
- hiển thị hoàn toàn bằng tiếng Việt;
- theo dõi skeleton;
- đếm lần tập;
- đánh giá trạng thái thực hiện;
- chấm điểm chất lượng nếu có nhãn phù hợp;
- đưa phản hồi có thể giải thích;
- lưu lịch sử buổi tập;
- có frontend và backend triển khai bằng Docker;
- KHÔNG đưa pipeline train, dataset, notebooks, experiments hoặc checkpoints train vào Docker.

Các kết quả nghiên cứu phải có:
- subject-wise split;
- GroupKFold hoặc LOSO khi phù hợp;
- baseline;
- proposed model;
- ablation study;
- confusion matrix;
- Macro-F1, Precision, Recall, Accuracy;
- rep counting MAE/RMSE/F1 nếu có;
- latency/FPS/model size;
- cross-dataset evaluation khi có ý nghĩa;
- seed cố định và khả năng tái lập.

---


# MÔI TRƯỜNG TRAIN BẮT BUỘC — PYTHON / CUDA / GPU LOCK

## Phiên bản chuẩn

Training environment phải dùng:

- OS ưu tiên: Windows 10/11 x64 hoặc Linux x86_64.
- Python: **3.11.x ONLY**.
- Phiên bản chuẩn để tái lập thí nghiệm: **Python 3.11.9**.
- Không dùng Python 3.12/3.13/3.14 cho repository train nếu chưa tạo một experiment environment mới và benchmark lại.
- PyTorch: **2.7.0**.
- torchvision: **0.22.0**.
- torchaudio: **2.7.0**.
- PyTorch CUDA wheel: **cu126 / CUDA 12.6 runtime**.
- MediaPipe: **1.0.1**.
- Package manager: pip trong `.venv-train`.
- Mọi package cuối cùng phải được freeze vào `training/requirements-lock.txt`.

Cài PyTorch CUDA:

```powershell
python -m pip install --upgrade pip
python -m pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu126
python -m pip install mediapipe==1.0.1
```

Không cài PyTorch CPU-only cho môi trường train chính.

## GPU policy bắt buộc

Training chính thức của RehabAI **chỉ được chạy bằng NVIDIA CUDA GPU rời**.

Quy tắc:

1. `torch.cuda.is_available()` phải là `True`.
2. `torch.cuda.device_count()` phải >= 1.
3. Training script phải in:
   - Python version;
   - PyTorch version;
   - CUDA runtime version của PyTorch;
   - NVIDIA GPU name;
   - GPU index;
   - total VRAM;
   - free VRAM trước train;
   - cuDNN version.
4. Nếu không thấy CUDA:
   - DỪNG ngay;
   - exit code != 0;
   - không tự fallback sang CPU;
   - không tự fallback sang Intel/AMD integrated GPU.
5. Nếu có nhiều NVIDIA CUDA GPU:
   - enumerate tất cả;
   - mặc định chọn GPU có `total_memory` lớn nhất;
   - cho phép override bằng `REHABAI_CUDA_DEVICE`;
   - ghi device đã chọn vào experiment metadata.
6. Sau khi chọn:
   ```python
   device = torch.device(f"cuda:{selected_index}")
   ```
   Tất cả model và tensor train phải được chuyển tới device này.
7. Sau batch đầu tiên phải assert:
   ```python
   assert next(model.parameters()).is_cuda
   ```
8. Test startup phải cấp phát một tensor CUDA và chạy phép toán thật trước khi train.
9. Không dùng:
   ```python
   device = "cuda" if torch.cuda.is_available() else "cpu"
   ```
   trong training chính thức vì cách này âm thầm rơi về CPU.
10. CPU chỉ được dùng cho:
    - DataLoader;
    - file/video decode;
    - preprocessing không hỗ trợ CUDA;
    - logging;
    - metric aggregation nhỏ.
    Model forward/backward chính phải chạy trên CUDA.
11. Intel integrated graphics / AMD integrated graphics không được dùng làm training accelerator.
12. Trên laptop có Intel/AMD iGPU + NVIDIA dGPU:
    - PyTorch CUDA training phải chạy trên NVIDIA dGPU;
    - Windows Graphics Settings có thể đặt `python.exe` / IDE thành `High performance` nếu cần;
    - vẫn phải xác nhận bằng log `torch.cuda.get_device_name(...)`.
13. Nếu máy chỉ có iGPU và không có NVIDIA CUDA GPU:
    - training official không được bắt đầu;
    - báo rõ cần NVIDIA GPU/CUDA hoặc chuyển job sang máy GPU khác.
14. Mixed precision:
    - ưu tiên `torch.amp.autocast("cuda")`;
    - dùng GradScaler khi phù hợp;
    - benchmark FP32 vs AMP và ghi cấu hình.
15. Có thể bật:
    ```python
    torch.backends.cudnn.benchmark = True
    ```
    khi input shape ổn định.
    Khi chạy experiment yêu cầu deterministic/reproducibility tuyệt đối thì chuyển sang deterministic config và ghi lại thay đổi.

## Hàm chọn GPU chuẩn

Training repository phải có một hàm duy nhất, ví dụ:

```python
def select_training_device():
    import os
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError(
            "RehabAI training requires a discrete NVIDIA CUDA GPU. "
            "CPU/iGPU fallback is disabled."
        )

    count = torch.cuda.device_count()
    override = os.getenv("REHABAI_CUDA_DEVICE")

    if override is not None:
        idx = int(override)
        if idx < 0 or idx >= count:
            raise RuntimeError(f"Invalid REHABAI_CUDA_DEVICE={idx}")
    else:
        idx = max(
            range(count),
            key=lambda i: torch.cuda.get_device_properties(i).total_memory
        )

    torch.cuda.set_device(idx)
    prop = torch.cuda.get_device_properties(idx)

    print(f"[GPU] cuda:{idx}")
    print(f"[GPU] {prop.name}")
    print(f"[GPU] VRAM={prop.total_memory / 1024**3:.2f} GB")
    print(f"[CUDA] torch={torch.__version__}")
    print(f"[CUDA] runtime={torch.version.cuda}")
    print(f"[cuDNN] {torch.backends.cudnn.version()}")

    test = torch.randn(1024, 1024, device=f"cuda:{idx}")
    _ = test @ test.T
    torch.cuda.synchronize(idx)

    return torch.device(f"cuda:{idx}")
```

Không được định nghĩa logic chọn device ở nhiều file khác nhau.

## GPU metadata bắt buộc trong mỗi experiment

Mỗi experiment phải ghi:

```json
{
  "python": "3.11.9",
  "torch": "2.7.0",
  "torch_cuda_runtime": "12.6",
  "cuda_available": true,
  "cuda_device_index": 0,
  "cuda_device_name": "...",
  "gpu_vram_bytes": 0,
  "cudnn_version": 0,
  "amp_enabled": true
}
```

Giá trị thực phải lấy tự động từ máy, không hardcode tên GPU.

## GPU utilization sanity check

Trong 20 batch đầu:
- ghi GPU allocated memory;
- ghi max allocated memory;
- ghi batch time;
- cảnh báo nếu model/tensor không nằm trên CUDA;
- cảnh báo nếu GPU memory gần như bằng 0 sau forward/backward;
- không coi iGPU activity trong Task Manager là bằng chứng train đúng GPU.

Nguồn xác nhận chính:
- `torch.cuda.get_device_name()`;
- `torch.cuda.memory_allocated()`;
- `nvidia-smi`.

---



# HARDWARE PROFILE CHÍNH THỨC — RTX 4060 LAPTOP 8GB

Máy phát triển/train chuẩn của dự án:

- GPU: **NVIDIA GeForce RTX 4060 Laptop GPU**
- VRAM: **8 GB**
- Loại GPU: **GPU rời NVIDIA trên laptop**
- iGPU Intel/AMD: chỉ dùng hiển thị hệ thống nếu cần, **không dùng để train**
- Training accelerator: **CUDA trên RTX 4060 Laptop GPU**
- Nguồn điện: khi train dài phải cắm sạc và dùng chế độ hiệu năng cao của laptop.
- Windows Graphics Settings/NVIDIA settings: ưu tiên `High performance` cho Python/IDE nếu máy dùng hybrid graphics.

## Kiểm tra đúng GPU trước khi train

Training startup phải kiểm tra:

```python
name = torch.cuda.get_device_name(selected_index)
if "RTX 4060 Laptop GPU" not in name:
    raise RuntimeError(
        f"Expected NVIDIA GeForce RTX 4060 Laptop GPU, got: {name}"
    )
```

Cho phép bỏ strict-name check chỉ khi người dùng chủ động đặt:

```text
REHABAI_ALLOW_OTHER_NVIDIA_GPU=1
```

nhưng vẫn phải là CUDA-capable NVIDIA GPU.

## Cấu hình VRAM mặc định cho 8GB

Default config khởi điểm:

```yaml
device: cuda:0
sequence_length: 96
batch_size: 16
gradient_accumulation_steps: 2
effective_batch_size: 32
amp: true
num_workers: 4
pin_memory: true
persistent_workers: true
prefetch_factor: 2
optimizer: AdamW
learning_rate: 0.0003
weight_decay: 0.0001
dropout: 0.35
gradient_clip_norm: 1.0
early_stopping_patience: 12
```

VRAM policy:

1. Bắt đầu `batch_size=16`.
2. Nếu peak VRAM < 6.5GB và train ổn định:
   - benchmark batch 24;
   - sau đó batch 32 nếu còn đủ VRAM.
3. Nếu CUDA OOM:
   - giảm batch: 16 -> 12 -> 8;
   - tăng gradient accumulation để giữ effective batch.
4. Không giảm sequence/model ngay khi OOM nếu có thể giải quyết bằng batch/accumulation.
5. Giữ ít nhất khoảng 0.8–1.0GB headroom VRAM để tránh OOM do fragmentation/overhead.
6. Dùng AMP để giảm VRAM và tăng throughput.
7. Không preload toàn bộ video/keypoints lên GPU.
8. DataLoader giữ dữ liệu ở RAM/CPU và chuyển batch theo nhu cầu.

## Model budget cho RTX 4060 Laptop 8GB

RehabMotionNet ưu tiên:

- tổng parameters mục tiêu: **0.5M–3M**;
- ST-GCN channels mặc định: **32 -> 64 -> 128**;
- TCN channels: **128**;
- sequence mặc định: **96 frames**;
- không dùng RGB Video Transformer lớn làm model chính;
- không dùng 3D CNN lớn làm model chính;
- Hand branch phải thiết kế lightweight;
- nếu hand branch làm tăng VRAM mạnh, giảm batch trước khi cắt bỏ hand branch.

## Laptop thermal/power monitoring

Do đây là GPU laptop, training phải log thêm:

- GPU temperature;
- GPU utilization;
- GPU memory used;
- power draw nếu `nvidia-smi` cung cấp;
- GPU clocks nếu có;
- batch time.

Có thể monitor ngoài bằng:

```powershell
nvidia-smi -l 2
```

Nếu thermal throttling rõ rệt:
- ghi nhận trong experiment log;
- không so sánh throughput/FPS giữa các run có trạng thái nguồn/nhiệt khác nhau mà không ghi chú;
- ưu tiên cắm sạc;
- đặt chế độ hiệu năng cao;
- đảm bảo tản nhiệt/luồng gió ổn định.

## CUDA sanity check bắt buộc

Trước epoch đầu tiên:

1. `nvidia-smi` phải thấy RTX 4060 Laptop GPU.
2. `torch.cuda.is_available()` phải True.
3. tên GPU phải đúng.
4. chạy CUDA matrix multiplication smoke test.
5. model parameters phải `is_cuda=True`.
6. chạy forward + backward 1 mini-batch.
7. `torch.cuda.memory_allocated()` phải > 0.
8. ghi peak VRAM.
9. nếu bất kỳ bước nào fail: STOP, không fallback CPU/iGPU.



# QUY TẮC XỬ LÝ ARCHIVE V3.1

- Upper Limb Stroke: người dùng tự giải nén thủ công trước Phase 1.
- `.zip`, `.rar`, `.7z` không bao giờ được coi là training sample.
- Raw archive có thể giữ để backup nhưng phải nằm ngoài processed-data index.
- Dataset index chỉ nhận các file video/annotation đã giải nén.
- Không xóa archive nguồn tự động.
- Không tự giải nén recursive ZIP trong prompt V3.1.
- Nếu có ZIP con bên trong dataset, người dùng tự giải nén hết trước khi chạy audit.
- Sau giải nén phải kiểm tra file count và label distribution, không chỉ kiểm tra thư mục tồn tại.

---
# QUY TẮC BẤT BIẾN — KHÔNG ĐƯỢC PHÁ VỠ

## Canonical Product Exercise Registry

Đây là SINGLE SOURCE OF TRUTH cho 4 bài tập sản phẩm.

| display_order | exercise_id | region_id | Vùng | Tên hiển thị tiếng Việt | slug |
|---:|---:|---:|---|---|---|
| 1 | 1 | 1 | Vai | Vai - Nâng vật | vai_nang_vat |
| 2 | 2 | 2 | Khuỷu tay | Khuỷu tay - Duỗi khuỷu tay | khuyu_tay_duoi |
| 3 | 3 | 3 | Cổ tay | Cổ tay - Nâng cổ tay | co_tay_nang |
| 4 | 4 | 4 | Bàn tay | Bàn tay - Mở bàn tay | ban_tay_mo |

Nguồn Upper Limb Stroke tương ứng:
- 1_Lifting_an_Object
- 2_Extending_the_Elbow
- 3_Lifting_the_Wrist
- 4_Opening_the_Hand

### Luật nhãn bắt buộc
1. Không dùng `LabelEncoder.fit()` để tự quyết định thứ tự class.
2. Không sort class alphabetically.
3. Không lấy thứ tự thư mục của hệ điều hành làm class index.
4. Model output index phải cố định:
   - output index 0 -> exercise_id 1
   - output index 1 -> exercise_id 2
   - output index 2 -> exercise_id 3
   - output index 3 -> exercise_id 4
5. Frontend KHÔNG hardcode tên riêng của model. Frontend lấy registry từ backend.
6. Backend đọc `exercise_registry.json`.
7. Training đọc chính cùng một registry.
8. Mỗi model export phải chứa:
   - `exercise_registry.json`
   - `registry_sha256.txt`
   - `feature_schema.json`
   - `normalization.json`
   - `model_config.json`
   - `metrics.json`
9. Backend phải từ chối load model nếu registry hash không khớp.
10. MobiPhysio và REHAB24-6 có nhãn khác với 4 bài sản phẩm. Không ép các bài khác nhau vào 4 ID này chỉ vì tên gần giống.
11. Trong báo cáo khoa học, giữ đúng nghĩa nhãn nguồn:
    - Upper Limb Stroke: `Complete / Incomplete`.
    - REHAB24-6: có correctness label.
    Không được tự đổi `Incomplete` thành `Incorrect` rồi tuyên bố đó là ground-truth correctness.
12. Nếu muốn sản phẩm cho 4 bài chính hiển thị “Đúng/Sai” và “Sai ở đâu”, phải có phase thu thêm dữ liệu/đánh nhãn lỗi cho chính 4 bài này hoặc có protocol chuyên gia rõ ràng.

---

# KIẾN TRÚC THƯ MỤC MỤC TIÊU

```text
rehabai/
├─ README.md
├─ pyproject.toml
├─ .gitignore
├─ .env.example
│
├─ shared/
│  ├─ exercise_registry.json
│  ├─ feature_schema.json
│  └─ constants.py
│
├─ data/
│  ├─ raw/
│  ├─ interim/
│  ├─ processed/
│  └─ indexes/
│
├─ training/
│  ├─ configs/
│  ├─ datasets/
│  ├─ extract/
│  ├─ features/
│  ├─ models/
│  │  ├─ baselines/
│  │  └─ rehab_motionnet/
│  ├─ losses/
│  ├─ train/
│  ├─ evaluation/
│  └─ export/
│
├─ experiments/
│  ├─ baseline_lstm/
│  ├─ baseline_tcn/
│  ├─ baseline_stgcn/
│  ├─ proposed/
│  └─ ablation/
│
├─ artifacts/
│  └─ model_v1/
│     ├─ model.pt
│     ├─ exercise_registry.json
│     ├─ registry_sha256.txt
│     ├─ feature_schema.json
│     ├─ normalization.json
│     ├─ model_config.json
│     └─ metrics.json
│
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  ├─ inference/
│  │  ├─ services/
│  │  ├─ schemas/
│  │  ├─ db/
│  │  └─ tests/
│  ├─ requirements.txt
│  └─ Dockerfile
│
├─ frontend/
│  ├─ src/
│  ├─ package.json
│  ├─ Dockerfile
│  └─ nginx.conf
│
├─ deployment/
│  ├─ model/
│  └─ compose.yaml
│
├─ research/
│  ├─ tables/
│  ├─ figures/
│  ├─ statistical_tests/
│  └─ paper_notes/
│
└─ scripts/
   ├─ setup_train_env.ps1
   ├─ run_extract.ps1
   ├─ run_train.ps1
   └─ export_model.ps1
```

---

# PHASE 0 — KHỞI TẠO DỰ ÁN VÀ KHÓA NHÃN

## Prompt Phase 0

Ngay khi bắt đầu Phase 0, kiểm tra môi trường:
- Python phải là 3.11.x; version chuẩn là 3.11.9.
- Chạy `nvidia-smi`.
- Chạy CUDA smoke test bằng PyTorch.
- Nếu `torch.cuda.is_available()` là False: FAIL Phase 0.
- Không cho phép CPU/iGPU fallback.
- Tạo `training/environment_report.json`.
- Tạo `training/requirements-lock.txt`.
- Tạo `training/device.py` chứa duy nhất logic `select_training_device()`.


Bạn là kỹ sư ML + software architect cho dự án RehabAI.

Hãy tạo repository theo cấu trúc được mô tả trong MASTER PROMPT.

Yêu cầu bắt buộc:
- Tạo `shared/exercise_registry.json`.
- Registry phải giữ chính xác 4 bài theo thứ tự:
  1. Vai - Nâng vật
  2. Khuỷu tay - Duỗi khuỷu tay
  3. Cổ tay - Nâng cổ tay
  4. Bàn tay - Mở bàn tay
- `exercise_id` và `display_order` là immutable.
- Tạo unit test kiểm tra registry:
  - đủ 4 ID;
  - không trùng ID;
  - đúng thứ tự 1,2,3,4;
  - slug không đổi;
  - JSON hợp lệ.
- Tạo hàm tính SHA256 registry.
- Không tạo model train ở phase này.
- Không Docker hóa phase này.
- Viết README hướng dẫn môi trường train chạy local bằng virtual environment.
- Chỉ hoàn thành Phase 0, không tự nhảy sang phase sau.

Acceptance criteria:
- `pytest` pass.
- registry hash được in ra.
- mọi text hiển thị sản phẩm được chuẩn bị bằng tiếng Việt UTF-8.

---

# PHASE 1 — TẢI, GIẢI NÉN THỦ CÔNG UPPER LIMB VÀ AUDIT DATASET

## Prompt Phase 1

Sử dụng dữ liệu do file `RehabAI_Download_Datasets_FULL_VERIFIED_V3_1_MANUAL_FALLBACK.bat` tạo ra.

### Quy tắc V3.1 cho Upper Limb Stroke

Nếu Mendeley API tự động lỗi:

1. Tải thủ công dataset Upper Limb Stroke từ trang Mendeley chính thức.
2. Người dùng **tự giải nén ZIP thủ công**.
3. Đặt dữ liệu đã giải nén vào:

```text
RehabAI_Datasets_FULL_VERIFIED/
└─ 01_Upper_Limb_Stroke/
   └─ dataset/
      └─ <cấu trúc thư mục gốc của dataset>
```

4. Không yêu cầu pipeline tự giải nén ZIP lồng nhau.
5. Không train trực tiếp từ file `.zip`.
6. File `.zip` có thể được giữ ở ngoài `dataset/` để backup/raw archive.
7. Sau khi giải nén, phải audit đúng:
   - tổng video = 491;
   - exercise_id 1 = 123;
   - exercise_id 2 = 127;
   - exercise_id 3 = 121;
   - exercise_id 4 = 120.
8. Nếu không đạt các số trên: dừng Phase 1.
9. Chỉ dùng video đã giải nén làm input preprocessing/train.

### Readiness gate

Trước Phase 2:
- kiểm tra `TRAINING_PREP/dataset_readiness_report.txt`;
- kiểm tra `TRAINING_PREP/READY_FOR_TRAINING.flag` nếu downloader đã tạo;
- nếu flag chưa có nhưng dữ liệu Upper Limb được giải nén tay, Phase 1 được phép chạy **independent audit**;
- independent audit phải tự xác nhận lại Upper Limb 491 và toàn bộ dataset bắt buộc;
- chỉ sau khi audit riêng PASS mới được tạo một project-level readiness marker cho pipeline;
- tuyệt đối không bỏ qua verification chỉ vì tải tay.

Hãy:
1. Kiểm tra tồn tại ba dataset:
   - Upper Limb Stroke Rehabilitation
   - REHAB24-6
   - MobiPhysio
2. Đọc `TRAINING_PREP/exercise_registry.json`.
3. Không thay đổi registry.
4. Xây dựng script audit:
   - bỏ qua `.zip/.rar/.7z` khi đếm sample;
   - archive chỉ là raw backup, không vào train index;
   - số video;
   - số subject;
   - số mẫu theo bài;
   - số Complete/Incomplete;
   - video hỏng;
   - FPS;
   - resolution;
   - duration;
   - missing metadata;
   - duplicate file hash nếu có.
5. Với Upper Limb Stroke:
   - lấy `subject_id`;
   - `exercise_id`;
   - `completion_label`;
   - source train/test split.
6. Với REHAB24-6:
   - đọc Segmentation.csv;
   - kiểm tra start/end frame;
   - correctness;
   - exercise source ID;
   - camera/view;
   - không map cưỡng ép Ex1..Ex6 vào 4 bài sản phẩm.
7. Với MobiPhysio:
   - giữ source label E01-E06;
   - participant;
   - camera angle;
   - variation;
   - score/metadata nếu có.
8. Sinh:
   - `data/indexes/dataset_audit.csv`
   - `data/indexes/upper_limb_master.csv`
   - `data/indexes/rehab24_master.csv`
   - `data/indexes/mobiphysio_master.csv`
   - `research/tables/dataset_statistics.csv`
9. Không train.

Acceptance criteria:
- Không còn sample không biết dataset.
- Upper Limb core có exercise_id chỉ thuộc {1,2,3,4}.
- Báo rõ mọi missing label.
- Không suy diễn nhãn không tồn tại.

---

# PHASE 2 — TRÍCH XUẤT LANDMARK / SKELETON

## Prompt Phase 2

Xây dựng pipeline offline trích xuất keypoint từ video bằng MediaPipe Holistic.

Mục tiêu:
- cùng một feature extraction logic sẽ được tái sử dụng ở backend inference;
- hạn chế train/inference skew.

Yêu cầu:
1. Dùng MediaPipe Holistic ở VIDEO mode cho video offline.
2. Không dùng face features cho model.
3. Lấy:
   - pose landmarks;
   - pose world landmarks nếu ổn định;
   - left hand landmarks;
   - right hand landmarks.
4. Lưu mỗi frame:
   - x,y,z;
   - visibility/confidence khi có;
   - timestamp;
   - frame index.
5. Hand landmarks đặc biệt quan trọng cho:
   - exercise_id 3;
   - exercise_id 4.
6. Có xử lý missing joints:
   - không tự điền 0 vô điều kiện;
   - lưu mask;
   - interpolation chỉ khi khoảng mất ngắn;
   - khoảng mất dài phải đánh dấu invalid.
7. Có quality gate:
   - tỷ lệ landmark hợp lệ;
   - người ra khỏi frame;
   - hand không nhìn thấy;
   - confidence thấp.
8. Lưu dạng NPZ/Parquet, không dùng hàng triệu CSV nhỏ.
9. Log extractor version + MediaPipe model/version.
10. Cho chạy resume:
    - file đã extract hợp lệ thì skip.
11. Không train.

Output:
- `data/interim/keypoints/...`
- `data/indexes/extraction_quality.csv`
- `shared/feature_schema.json`

Acceptance criteria:
- Có test trên 1 video của mỗi bài.
- Không đảo left/right ngoài ý muốn.
- Dữ liệu UTF-8 và đường dẫn portable.

---

# PHASE 3 — CHUẨN HÓA VÀ FEATURE ENGINEERING

## Prompt Phase 3

Tạo preprocessing dùng chung cho training và inference.

Bắt buộc:
1. Normalize translation theo tâm cơ thể phù hợp.
2. Normalize scale theo shoulder width hoặc torso scale.
3. Không mirror ngẫu nhiên nếu làm mất ý nghĩa trái/phải.
4. Sinh các stream:
   A. Pose coordinate stream.
   B. Hand coordinate stream.
   C. Kinematic stream.
5. Kinematic features:
   - shoulder angle;
   - elbow angle;
   - wrist-related angle khi landmark cho phép;
   - trunk inclination;
   - bone vectors;
   - velocity;
   - angular velocity;
   - acceleration;
   - ROM;
   - symmetry khi phù hợp.
6. Mỗi feature phải có tên trong `feature_schema.json`.
7. Không để code train và backend tự tính feature theo hai công thức khác nhau.
8. Viết package `shared_preprocessing` hoặc module có thể import ở cả training/backend.
9. Sequence:
   - hỗ trợ variable length;
   - có resampling;
   - baseline thử 64/96/128 frames;
   - không hardcode một độ dài mà không benchmark.
10. Augmentation chỉ dùng ở TRAIN:
   - temporal scaling;
   - small rotation;
   - small translation;
   - small scale;
   - Gaussian noise nhẹ;
   - random landmark masking nhẹ.
11. Validation/Test không augmentation.

Output:
- `data/processed/...`
- `shared/normalization_schema.json`
- tests so sánh preprocessing offline và inference.

---

# PHASE 4 — CHIA TRAIN / VALIDATION / TEST ĐÚNG CHUẨN NCKH

## Prompt Phase 4

Tạo split theo SUBJECT/PARTICIPANT.

Cấm:
- random frame split;
- cùng người xuất hiện ở train và test;
- augment trước split.

Yêu cầu:
1. Group split theo `subject_id`.
2. Tạo:
   - train;
   - validation;
   - test.
3. Với dataset ít subject:
   - hỗ trợ GroupKFold 5-fold hoặc LOSO.
4. Lưu split manifest:
   - sample_id;
   - subject_id;
   - dataset;
   - split;
   - exercise_id/source_exercise;
   - label.
5. Tạo test tự động xác nhận intersection subjects = rỗng.
6. Seed cố định.
7. Ghi seed vào experiment config.
8. Không thay đổi canonical exercise registry.

Output:
- `data/indexes/splits/*.csv`
- `training/configs/split.yaml`

---

# PHASE 5 — BASELINE MODELS

## Prompt Phase 5

Train các baseline trước proposed model.

Baselines:
1. MLP trên summary kinematic features.
2. LSTM.
3. BiLSTM.
4. TCN.
5. ST-GCN cơ bản.

Main task của 4 bài Upper Limb:
A. Exercise recognition: 4 classes.
B. Completion classification: Complete / Incomplete.

Quan trọng:
- gọi đúng là completion status đối với Upper Limb Stroke;
- không gọi ground truth này là correctness.

Mỗi baseline:
- cùng split;
- cùng input normalization;
- cùng seed set;
- logging train/val loss;
- early stopping;
- model checkpoint theo Macro-F1 validation;
- metrics test chỉ chạy sau khi chốt model/hyperparameter.

Sinh:
- metrics.json;
- confusion_matrix.png;
- training_curve.png;
- per-class metrics;
- parameter count;
- inference latency.

Không tối ưu proposed model trước khi baseline chạy xong.

---

# PHASE 6 — PRETRAIN / REPRESENTATION LEARNING ĐA DATASET

## Prompt Phase 6

Tận dụng MobiPhysio và REHAB24-6 làm auxiliary/pretraining data mà không làm sai ontology nhãn.

Yêu cầu:
1. Không cưỡng ép source labels thành 4 product exercise IDs.
2. Xây shared motion encoder học representation từ skeleton.
3. Thử:
   - supervised contrastive khi nhãn tương thích;
   - self-supervised temporal augmentation;
   - masked sequence reconstruction hoặc contrastive sequence pairs.
4. Positive pairs:
   - cùng source exercise hoặc cùng sample augmented views;
   - chỉ tạo khi logic nhãn đúng.
5. Negative pairs:
   - khác movement/source class khi chắc chắn.
6. Lưu pretrained encoder riêng.
7. So sánh:
   - train from scratch;
   - pretrained then fine-tune.
8. Báo Macro-F1 và generalization gap.

Không trộn label semantics.

---

# PHASE 7 — PROPOSED MODEL: REHAB-MOTIONNET

## Prompt Phase 7

Cài đặt mô hình đề xuất `RehabMotionNet`.

Kiến trúc mục tiêu:
- Pose Graph Branch:
  lightweight ST-GCN.
- Hand Branch:
  graph/temporal encoder cho left + right hand.
- Kinematic Branch:
  lightweight MLP/TCN cho angle/ROM/velocity.
- Temporal Fusion:
  Multi-Scale TCN.
- Attention/Gated fusion.
- Shared embedding.

Heads:
1. `exercise_head`: 4 classes.
2. `completion_head`: 2 classes cho Upper Limb core.
3. `phase_head`: temporal segmentation khi dataset hỗ trợ.
4. `quality_head`: regression chỉ với dataset có score hợp lệ.
5. `correctness_head`: chỉ với dataset có ground-truth correctness.
6. `error_head`: chỉ bật khi có error-type labels thật.

Dùng masked multi-task loss:
- task không có label thì loss weight = 0 cho sample đó.
- không tự chế label.

Giới hạn:
- ưu tiên model nhỏ khoảng 0.5–3M parameters.
- không dùng video transformer lớn làm model chính.
- mọi output phải map qua registry rõ ràng.

Loss:
- classification: weighted CE hoặc focal nếu imbalance.
- label smoothing nhỏ nếu cần.
- quality regression: Huber/MSE benchmark.
- segmentation: CE + temporal smoothing nếu hợp lý.
- contrastive loss nếu phase pretraining dùng.

Sinh ablation hooks để có thể bật/tắt:
- hand branch;
- kinematic branch;
- contrastive pretraining;
- MS-TCN;
- attention.

---

# PHASE 8 — TRAINING CHỐNG OVERFIT / UNDERFIT

## Prompt Phase 8

Tạo trainer nghiên cứu có reproducibility.

Default starting configuration:

RTX 4060 Laptop 8GB defaults:
- batch size: 16;
- gradient accumulation: 2;
- effective batch: 32;
- sequence: 96 frames;
- num_workers: 4;
- AMP: enabled;
- target peak VRAM: <= 7.0–7.2GB;
- keep VRAM headroom for runtime overhead;
- device: CUDA NVIDIA discrete GPU REQUIRED;
- CPU/iGPU fallback: DISABLED;
- device selection: largest-VRAM CUDA GPU unless `REHABAI_CUDA_DEVICE` is set;
- optimizer: AdamW;
- lr search around 1e-4 đến 1e-3;
- starting point 3e-4;
- weight decay starting point 1e-4;
- dropout benchmark 0.2/0.35/0.5;
- batch size tùy VRAM;
- early stopping 10–15 epochs;
- cosine scheduler hoặc OneCycle benchmark;
- mixed precision nếu GPU hỗ trợ;
- gradient clipping;
- fixed seeds;
- deterministic mode khi phù hợp.

Theo dõi:
- train loss;
- val loss;
- train Macro-F1;
- val Macro-F1;
- per-class recall;
- learning rate.

Overfit detector:
- train tăng nhưng val giảm nhiều;
- tự ghi warning vào experiment summary.

Underfit detector:
- cả train và val thấp;
- ghi warning.

Không tự thay hyperparameter trong test set.
Không dùng test để chọn model.

---

# PHASE 9 — ĐÁNH GIÁ NCKH

## Prompt Phase 9

Tạo evaluation pipeline chuẩn paper.

Classification:
- Accuracy;
- Macro Precision;
- Macro Recall;
- Macro F1;
- per-class F1;
- confusion matrix;
- AUROC nếu thích hợp.

Rep/segmentation:
- MAE;
- RMSE;
- temporal F1;
- rep detection precision/recall/F1.

Quality:
- MAE;
- RMSE;
- Pearson;
- Spearman.

System:
- model parameters;
- model size MB;
- CPU latency;
- GPU latency nếu có;
- end-to-end FPS;
- preprocessing latency;
- inference latency.

Research comparisons:
1. MLP.
2. LSTM.
3. BiLSTM.
4. TCN.
5. ST-GCN.
6. RehabMotionNet.

Ablation:
- Full.
- minus hand.
- minus kinematic.
- minus contrastive.
- minus MS-TCN.
- minus attention.

Cross-dataset:
- chỉ làm task nào có semantics đủ tương thích.
- không báo metric đánh tráo label.

Statistical reporting:
- mean ± std qua folds/seeds khi có;
- lưu raw fold metrics;
- tạo bảng LaTeX/CSV.

Output:
- `research/tables/`
- `research/figures/`
- `research/statistical_tests/`

---

# PHASE 10 — THU THÊM DỮ LIỆU CHO “ĐÚNG/SAI Ở ĐÂU” (NẾU LÀM PAPER MẠNH)

## Prompt Phase 10

Thiết kế extension dataset riêng cho 4 bài sản phẩm.

Không thu dữ liệu người thật trước khi hoàn thành quy trình đồng thuận/đạo đức phù hợp của cơ sở nghiên cứu.

Mục tiêu label:
- correct;
- incomplete;
- error_type;
- quality_score nếu chuyên gia đánh giá.

Canonical exercises:
1. Vai - Nâng vật.
2. Khuỷu tay - Duỗi khuỷu tay.
3. Cổ tay - Nâng cổ tay.
4. Bàn tay - Mở bàn tay.

Error taxonomy phải do protocol/chuyên gia xác nhận.
Không tự tuyên bố ngưỡng y khoa.

Dữ liệu cần:
- subject_id ẩn danh;
- exercise_id;
- rep_id;
- camera view;
- label;
- error_type;
- score;
- annotator;
- timestamp/protocol version.

Tính inter-rater agreement nếu nhiều annotator.

Nếu phase này chưa có dữ liệu:
- backend không được giả vờ xuất error_type từ model chưa train.
- UI hiển thị “Chưa có đánh giá lỗi chi tiết”.

---

# PHASE 11 — EXPORT MODEL CHO SẢN PHẨM

## Prompt Phase 11

Export duy nhất model đã chốt sau evaluation.

Tạo artifact directory:

```text
artifacts/model_v1/
├─ model.pt
├─ exercise_registry.json
├─ registry_sha256.txt
├─ feature_schema.json
├─ normalization.json
├─ model_config.json
├─ metrics.json
└─ model_card.md
```

`model_card.md` phải ghi:
- dataset;
- task;
- label semantics;
- split;
- metrics;
- limitations;
- intended use;
- không thay thế chuyên gia y tế;
- registry version/hash.

Backend chỉ được load thư mục artifact này.
Backend không import package train.
Không copy raw dataset vào artifact.

---

# PHASE 12 — BACKEND INFERENCE

## Prompt Phase 12

Xây backend FastAPI cho RehabAI.

Backend chỉ phục vụ inference và session history.
KHÔNG chứa trainer.

API:
- `GET /api/health`
- `GET /api/model-info`
- `GET /api/exercises`
- `POST /api/sessions`
- `GET /api/sessions/{id}`
- `GET /api/sessions`
- `WS /ws/inference`

`GET /api/exercises`:
- trả đúng thứ tự 1,2,3,4;
- tên tiếng Việt lấy từ registry;
- không sort alphabetically.

WebSocket inference:
1. frontend capture camera;
2. gửi JPEG/WebP frame + timestamp + session id;
3. backend decode;
4. MediaPipe Holistic;
5. dùng CÙNG preprocessing với training;
6. buffer sequence;
7. model inference;
8. smoothing prediction;
9. trả:
   - exercise_id;
   - exercise_name_vi;
   - region_vi;
   - confidence;
   - completion status nếu head hỗ trợ;
   - rep_count;
   - phase;
   - quality score nếu head hỗ trợ;
   - feedback_vi nếu có evidence/model;
   - skeleton landmarks để overlay nếu cần.

Không trả tên class bằng cách lấy `argmax` rồi index vào một list hardcode khác.
Phải dùng:
`output_index -> exercise_id -> registry`.

Runtime checks:
- model registry hash phải khớp;
- feature schema version phải khớp;
- normalization version phải khớp;
- mismatch => backend fail fast.

Storage:
- SQLAlchemy.
- mặc định SQLite cho demo/local.
- DB path từ env.
- thiết kế để sau này đổi PostgreSQL.

Tests:
- registry order;
- model hash;
- inference schema;
- API Vietnamese labels;
- WebSocket basic flow.

---

# PHASE 13 — FRONTEND TIẾNG VIỆT

## Prompt Phase 13

Xây frontend React + TypeScript + Vite.

Toàn bộ giao diện người dùng bằng tiếng Việt.

Không hardcode thứ tự bài.
Khi load:
- gọi `/api/exercises`;
- render theo `display_order`.

Màn hình:
1. Trang chủ.
2. Chọn bài tập:
   1. Vai - Nâng vật
   2. Khuỷu tay - Duỗi khuỷu tay
   3. Cổ tay - Nâng cổ tay
   4. Bàn tay - Mở bàn tay
3. Màn hình luyện tập:
   - camera;
   - skeleton overlay;
   - tên bài hiện tại;
   - rep;
   - trạng thái;
   - score nếu có;
   - feedback tiếng Việt;
   - confidence không cần phô quá kỹ cho người dùng.
4. Kết quả buổi tập.
5. Lịch sử.
6. Biểu đồ tiến triển.

Camera:
- browser `getUserMedia`;
- resize frame hợp lý;
- stream qua WebSocket;
- có reconnect;
- có trạng thái “Đang kết nối / Đã kết nối / Mất kết nối”.

UX:
- không đổi vị trí card khi prediction thay đổi;
- danh sách bài luôn 1→4;
- không dùng key theo tên;
- dùng exercise_id làm key.

Accessibility:
- font rõ;
- nút lớn;
- contrast tốt;
- trạng thái bằng cả text, không chỉ màu.

Không viết logic y khoa ở frontend.
Frontend chỉ hiển thị kết quả backend.

---

# PHASE 14 — DOCKER CHỈ CHO FRONTEND + BACKEND

## Prompt Phase 14

Docker hóa phần deployment.

BẮT BUỘC:
- Docker chỉ cho frontend và backend inference.
- KHÔNG Docker hóa training.
- KHÔNG copy:
  - `training/`
  - `data/`
  - `experiments/`
  - `notebooks/`
  - raw checkpoints
  - dataset archives
  vào image.

Tạo:
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `deployment/compose.yaml`
- `.dockerignore`

Backend image:
- Python runtime;
- FastAPI;
- MediaPipe/runtime dependencies;
- inference dependencies;
- backend code;
- shared preprocessing cần cho inference.

Model:
- mount read-only:
  `./deployment/model:/app/model:ro`
- không copy toàn bộ training repo vào image.

Frontend image:
- build React;
- production serve bằng Nginx.

Compose services tối thiểu:
- backend;
- frontend.

Backend persistence:
- named volume cho SQLite/history hoặc bind mount `./runtime-data:/app/data`.

Healthcheck:
- backend `/api/health`.

Frontend reverse proxy:
- `/api` -> backend;
- `/ws` -> backend với WebSocket upgrade.

Port example:
- frontend: `8080:80`.
- backend có thể chỉ expose nội bộ, không bắt buộc publish ra host.

`.dockerignore` root:
```text
data/
training/
experiments/
research/
notebooks/
*.ipynb
**/checkpoints/
**/*.ckpt
**/wandb/
RehabAI_Datasets_FULL_VERIFIED/
```

Acceptance:
- `docker compose up --build` chạy sản phẩm.
- train env không cần Docker.
- xóa training folder khỏi deployment machine vẫn chạy được nếu model artifact còn.
- camera browser kết nối được backend.
- label vẫn đúng 1→4.

---

# PHASE 15 — END-TO-END TEST VÀ ĐÓNG GÓI SẢN PHẨM

## Prompt Phase 15

Tạo end-to-end verification.

Test:
1. Registry:
   - đúng 4 ID.
2. Model:
   - output dimension đúng.
3. Backend:
   - exercise API đúng thứ tự.
4. Frontend:
   - thứ tự không đổi.
5. Camera:
   - frame flow.
6. Inference:
   - prediction mapping chính xác.
7. Session:
   - lưu DB.
8. Docker:
   - restart vẫn giữ lịch sử.
9. UTF-8:
   - không lỗi chữ “Khuỷu”, “Cổ”, “Bàn”.
10. Performance:
   - FPS;
   - latency.
11. Research mode:
   - export một session raw inference log để kiểm chứng.

Tạo release:
```text
release/
├─ compose.yaml
├─ frontend/
├─ backend/
├─ model/
├─ .env.example
└─ README_DEPLOY.md
```

Không chứa dataset/train code.

---

# PHASE 16 — TỰ ĐỘNG TẠO KẾT QUẢ CHO BÁO CÁO / PAPER

## Prompt Phase 16

Tạo script tái tạo bảng và hình cho bài báo từ experiment artifacts, không nhập số liệu bằng tay.

Tạo:
- dataset statistics;
- baseline comparison;
- proposed comparison;
- ablation table;
- per-class F1;
- confusion matrix;
- train/val curves;
- model size;
- latency/FPS;
- fold mean/std;
- error analysis.

Mỗi bảng phải truy vết được tới experiment ID/config/checkpoint.

Tạo `research/reproducibility_manifest.json` gồm:
- git commit;
- Python version (expected 3.11.x; canonical 3.11.9);
- PyTorch version;
- PyTorch CUDA runtime;
- NVIDIA driver version;
- CUDA GPU name/index/VRAM;
- cuDNN version;
- AMP enabled/disabled;
- library versions;
- seeds;
- split manifest hash;
- registry hash;
- feature schema hash;
- model artifact hash.

Không làm đẹp số liệu.
Không bỏ fold xấu nếu không có lý do đã định trước.

---

# THỨ TỰ CHẠY THỰC TẾ

1. Chạy `RehabAI_Download_Datasets_FULL_VERIFIED_V3_1_MANUAL_FALLBACK.bat`.
2. Nếu Upper Limb/Mendeley tự động lỗi:
   - tải dataset bằng tay;
   - tự giải nén toàn bộ ZIP/ZIP con;
   - đặt dữ liệu đã giải nén vào `RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke/dataset/`.
3. Kiểm tra `RehabAI_Datasets_FULL_VERIFIED/TRAINING_PREP`.
4. Hoàn thành Phase 0.
5. Phase 1 audit độc lập và xác nhận:
   - Upper Limb = 491;
   - bài 1/2/3/4 = 123/127/121/120;
   - REHAB24-6 annotation hợp lệ;
   - MobiPhysio đủ dữ liệu bắt buộc.
6. Phase 2 extract.
7. Phase 3 features.
8. Phase 4 split.
9. Phase 5 baselines.
10. Phase 6 pretraining.
11. Phase 7 RehabMotionNet.
12. Phase 8 training/tuning.
13. Phase 9 evaluation.
14. Nếu cần đúng/sai + error feedback mạnh: Phase 10.
15. Phase 11 export model.
16. Phase 12 backend.
17. Phase 13 frontend.
18. Phase 14 Docker deployment.
19. Phase 15 E2E.
20. Phase 16 paper artifacts.

---

# CÁC ĐIỀU AI CODING AGENT PHẢI LÀM SAU MỖI PHASE

Sau mỗi phase, luôn trả:
1. Danh sách file đã tạo/sửa.
2. Cách chạy.
3. Cách test.
4. Expected output.
5. Lỗi thường gặp.
6. Những acceptance criteria đã đạt/chưa đạt.
7. Không tự nhảy phase tiếp theo nếu phase hiện tại chưa pass.
8. Không đổi canonical IDs.
9. Không xóa dữ liệu nguồn.
10. Không ghi đè artifact nghiên cứu cũ; experiment phải versioned.
11. Các phase có training phải xác nhận model parameters đang ở CUDA device.
12. Nếu CUDA fail thì dừng phase; không đổi sang CPU/iGPU để tiếp tục.

---

# ĐÁNH GIÁ THIẾT KẾ PROMPT

## Điểm mạnh
- Khóa ontology/label ngay từ đầu.
- Ngăn class swap giữa train/backend/frontend.
- Phân biệt đúng semantics `Complete/Incomplete` và `Correct/Incorrect`.
- Tách raw dataset label và canonical product label.
- Subject-wise split để tránh leakage.
- Có baseline + ablation + reproducibility cho NCKH.
- Có model research nhưng vẫn giữ giới hạn parameter để giảm overfit.
- Dùng chung preprocessing giữa offline và realtime.
- Docker chỉ deployment, không Docker hóa train.
- Frontend tiếng Việt lấy label từ backend.
- Có model artifact contract và hash validation.
- Có phase thu dữ liệu riêng nếu muốn phản hồi lỗi chi tiết thật sự.

## Rủi ro còn lại
- Ba dataset không cùng ontology, không thể trộn nhãn thẳng.
- Upper Limb Stroke chỉ có 10 volunteer và Complete/Incomplete; không đủ để tuyên bố clinical correctness.
- Hand opening cần hand landmarks ổn định và camera nhìn rõ ngón tay.
- Domain shift giữa camera dataset và camera người dùng thật có thể giảm accuracy.
- Nếu paper có người tham gia mới, cần quy trình đạo đức/đồng thuận phù hợp.
- “Chấm điểm 0–100” chỉ nên bật khi có nhãn/ground-truth chất lượng đủ mạnh.

## Đánh giá tổng thể
- Kiến trúc sản phẩm: 9/10.
- Tính tái lập nghiên cứu: 9.5/10.
- Khả năng tránh label mix-up: 10/10 nếu tuân thủ registry/hash.
- Khả năng chống data leakage: 9.5/10 nếu subject split tests luôn pass.
- Giá trị bài báo: 8.5–9/10 trước khi có dataset riêng; cao hơn nếu có expert-labeled error dataset và cross-subject validation.
- Rủi ro lớn nhất không nằm ở code mà nằm ở label quality, số subject và domain shift.


---

# GHI CHÚ PHIÊN BẢN V3.1

Prompt này được thiết kế cho:
`RehabAI_Download_Datasets_FULL_VERIFIED_V3_1_MANUAL_FALLBACK.bat`

Khác V3.2:
- không phụ thuộc recursive ZIP extraction;
- người dùng tự giải nén Upper Limb;
- pipeline chỉ audit và train trên dữ liệu đã giải nén;
- model/CUDA/RTX 4060 Laptop/frontend/backend/Docker giữ nguyên thiết kế V3.

Không đổi:
1 = Vai - Nâng vật
2 = Khuỷu tay - Duỗi khuỷu tay
3 = Cổ tay - Nâng cổ tay
4 = Bàn tay - Mở bàn tay
