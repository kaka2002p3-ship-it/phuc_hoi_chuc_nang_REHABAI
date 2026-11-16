# RehabAI - Hệ Thống Hỗ Trợ Phục Hồi Chức Năng Bằng AI

RehabAI là một giải pháp theo dõi và đánh giá bài tập phục hồi chức năng vận động dành cho bệnh nhân đột quỵ, sử dụng trí tuệ nhân tạo (AI) và thị giác máy tính. Hệ thống hoạt động thời gian thực ngay trên trình duyệt (Webcam) mà không cần cảm biến phần cứng chuyên dụng.

## ✨ Tính Năng Nổi Bật
- **100% Cục Bộ (Privacy First)**: Mọi thao tác thu thập landmark đều có thể chạy trên máy tính cá nhân.
- **Theo Dõi Thời Gian Thực**: Tốc độ phản hồi cao (15-30 fps) thông qua WebSocket.
- **Công Nghệ Hiện Đại**: Sự kết hợp hoàn hảo giữa PyTorch (Train/Inference), FastAPI (Backend), và React/Vite (Frontend).
- **Hỗ Trợ Người Việt**: Giao diện tiếng Việt thân thiện, hiển thị to, rõ ràng và dễ thao tác.
- **Docker Hóa Hoàn Toàn**: Sẵn sàng deploy lên bất kỳ server nào với kiến trúc Microservices tinh gọn.

## 📁 Cấu Trúc Mã Nguồn

Dự án được chia thành các phân khu rõ ràng theo chuẩn Software Engineering:

- `data/`: Quản lý raw data, metadata, các phép split (Train/Val/Test) và SQLite lưu trữ lịch sử sessions.
- `shared/`: Các hàm xử lý chung (Preprocessing, Kinematics, Normalization) dùng chung cho cả Training và Inference. Đảm bảo tính nhất quán của luồng dữ liệu (Single Source of Truth).
- `training/`: Môi trường nghiên cứu và huấn luyện (PyTorch Lightning). Định nghĩa kiến trúc RehabMotionNet, Dataset, Dataloader và Scripts chạy huấn luyện/export mô hình.
- `artifacts/`: Nơi lưu trữ các mô hình đã được xuất ra (ONNX, TorchScript hoặc JIT) sẵn sàng cho Inference. Không bị commit lên git.
- `backend/`: API Server phục vụ suy luận thời gian thực (FastAPI + WebSockets) và REST API cho Frontend.
- `frontend/`: Web UI được viết bằng React + TypeScript + Vite với giao diện Glassmorphism hiện đại.
- `deployment/`: Cấu hình Docker và Docker Compose cho toàn bộ hệ thống (ngoại trừ training module).

## 🚀 Hướng Dẫn Sử Dụng (Môi Trường Triển Khai)

Chỉ cần cài đặt Docker và Docker Compose, sau đó chạy:

```bash
# Từ thư mục gốc dự án
cd rehabai/deployment
docker compose up --build -d
```
Truy cập `http://localhost:8080` trên trình duyệt để bắt đầu sử dụng.

> ⚠️ **Lưu ý**: Backend chạy ở port 8000, Frontend/Nginx ở port 8080.

## 🛠️ Hướng Dẫn Phát Triển (Môi Trường Dev)

**1. Backend:**
```bash
# Từ thư mục rehabai/
$env:PYTHONPATH="."
uvicorn backend.main:app --reload --port 8000
```

**2. Frontend:**
```bash
cd frontend
npm install  # Chỉ cần chạy lần đầu
npm run dev
```

**3. Training (từ thư mục rehabai/):**
```bash
python training/train.py --help
```

> 📋 **Lưu ý**: Các thí nghiệm có config riêng trong `experiments/`. Chạy pytest từ thư mục `rehabai/`:
> ```bash
> python -m pytest tests shared/tests -q
> ```

## 📦 Packaging & Distribution

### Cài đặt package (dev mode)
```bash
pip install -e ".[all]"
```

### Chạy tests
```bash
# All tests
pytest

# Unit tests only
pytest -m unit

# Skip slow tests
pytest -m "not slow"
```

### Development tools
```bash
# Format code
black .

# Lint code
ruff check .

# Type check
mypy .
```

### 📦 Công Nghệ Sử Dụng

| Layer | Công nghệ |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, React Router, Recharts |
| Backend | FastAPI, Uvicorn, WebSockets, SQLAlchemy |
| Database | SQLite (runtime), PostgreSQL (production) |
| ML | PyTorch 2.2.2 (inference), 2.7.0 (training) |
| Pose | MediaPipe Holistic 0.10.21 |
| Deployment | Docker, Docker Compose, Nginx |

## 📊 Hiệu Suất Model (LOSO Cross-Validation)

> ⚠️ **Quan trọng**: Đây là kết quả nghiên cứu, phù hợp **demo/nghiên cứu**, chưa đủ cho clinical deployment.

| Chỉ số | Giá trị | Biến thiên (fold) |
|--------|---------|-------------------|
| Accuracy | 43.79% | 5% - 74.58% |
| Macro-F1 | 35.44% | 2.38% - 73.92% |
| Weighted-F1 | 49.85% | 9.52% - 78.79% |

**Dataset**: 387 mẫu, 10 bệnh nhân, 4 bài tập phục hồi chi trên.

## 🏗️ Kiến Trúc Hệ Thống (Phase 1-15)
Hệ thống được phát triển qua 15 Phase nghiêm ngặt:
1. Setup kiến trúc & Shared Module.
2. Thiết kế Dataset & Dataloaders.
3. Feature Engineering (Động học Kinematics).
4. Khởi tạo Mô hình AI (RehabMotionNet).
5. Xây dựng Loss Function.
6. Thiết lập Metric (Completion Score, Accuracy).
7. Tích hợp PyTorch Lightning.
8. Huấn luyện thử nghiệm (Overfit Test).
9. Huấn luyện toàn diện (Full Training).
10. Đánh giá kiểm thử (Evaluation).
11. Đóng gói mô hình (Export Model).
12. Xây dựng Backend API (FastAPI & WebSockets).
13. Xây dựng Web UI Frontend (React + Vite).
14. Đóng gói Docker Compose.
15. Bàn giao mã nguồn.

---
*Dự án được xây dựng và tối ưu hoá bởi Agent.*
