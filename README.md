<div align="center">

# 🩺 RehabAI
### Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên
**RehabAI: Upper-Limb Rehabilitation Exercise Monitoring and Evaluation Support System**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/Frontend-React_19_%2B_Vite-61DAFB.svg)](https://react.dev/)
[![PyTorch](https://img.shields.io/badge/AI_Model-PyTorch_%2B_MediaPipe-EE4C2C.svg)](https://pytorch.org/)
[![Ollama](https://img.shields.io/badge/Chatbot-Ollama_Qwen_2.5_7B-black.svg)](https://ollama.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![SIC Capstone](https://img.shields.io/badge/Samsung_Innovation_Campus-AI_Capstone_2026-0B2265.svg)](https://www.samsung.com/)

---

*Dự án Capstone tham dự chương trình đào tạo trí tuệ nhân tạo **Samsung Innovation Campus (SIC)**.*

</div>

---

## 🌟 1. Giới Thiệu Tổng Quan (Overview)

**RehabAI** là giải pháp y tế số (Digital Health) ứng dụng thị giác máy tính và trí tuệ nhân tạo nhằm hỗ trợ bệnh nhân sau tai biến mạch máu não hoặc chấn thương vận động tự luyện tập phục hồi chức năng chi trên tại nhà hoặc phòng khám.

Hệ thống giải quyết các thách thức lớn trong phục hồi chức năng truyền thống:
1. **Thiếu phản hồi định lượng thời gian thực**: Người bệnh khó tự đánh giá tính chính xác của động tác khi không có kỹ thuật viên bên cạnh.
2. **Nguy cơ quá sức và rủi ro thứ phát**: Thiếu cơ chế giám sát mức độ đau (VAS) và các dấu hiệu nguy hiểm cấp tính (Red Flags).
3. **Quá tải nhân lực y tế**: Giúp bác sĩ và chuyên viên theo dõi tiến trình luyện tập của nhiều bệnh nhân từ xa qua bảng điều khiển số liệu khách quan.

---

## 🏗️ 2. Kiến Trúc Cốt Lõi (System Architecture)

RehabAI được thiết kế tuân thủ nghiêm ngặt **Kiến trúc An toàn 2 Lớp (Two-Layer Clinical Safety Architecture)**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        REHABAI ARCHITECTURE                            │
├───────────────────────────────────┬────────────────────────────────────┤
│   LAYER 1: COMPUTER VISION AI     │   LAYER 2: CLINICAL SAFETY RULES   │
│   (Định lượng cử động khách quan) │   (Bảo vệ người bệnh lâm sàng)     │
├───────────────────────────────────┼────────────────────────────────────┤
│ • MediaPipe Pose & Hand Landmark  │ • Giám sát mức đau trước tập (VAS) │
│ • Chuẩn hóa động học (Body Center)│ • Dừng khẩn cấp khi VAS ≥ 7/10     │
│ • Nhận diện bài tập (Gập duỗi     │ • Bộ lọc dấu hiệu cờ đỏ cấp tính   │
│   khuỷu tay & Mở bàn tay)         │ • Chatbot RAG tri thức y khoa      │
│ • Kiểm định chéo 10-fold LOSO     │ • Khuyến cáo gọi cấp cứu 115       │
└───────────────────────────────────┴────────────────────────────────────┘
```

- **Lớp 1 (Mô hình AI)**: Tập trung nhận dạng cử động, đếm chu kỳ và tính toán biên độ góc khớp dựa trên landmark xương người chuẩn hóa. Không đưa ra chẩn đoán hay kết luận thay thế bác sĩ.
- **Lớp 2 (Hệ thống quy tắc y tế cứng)**: Kiểm soát ranh giới an toàn, tự động ngắt phiên tập nếu bệnh nhân bị đau vượt ngưỡng hoặc xuất hiện dấu hiệu bất thường, đảm bảo chuẩn đạo đức AI y tế.

---

## 📂 3. Cấu Trúc Thư Mục Dự Án (Repository Structure)

```text
PhucHoiChucNangTay/
├── rehabai/                      # Mã nguồn hoàn chỉnh ứng dụng Full-Stack
│   ├── backend/                  # API REST & WebSocket (FastAPI, SQLAlchemy, PyTorch)
│   ├── frontend/                 # Giao diện Web Care (React 19, TypeScript, Vite, Tailwind)
│   ├── chatbot/                  # Tích hợp Ollama Qwen 2.5:7B + RAG + Bộ lọc an toàn
│   ├── artifacts/                # Gói mô hình suy luận nhẹ phục vụ triển khai
│   ├── deployment/               # Cấu hình Docker Compose, Nginx, PostgreSQL
│   └── shared/                   # Schema dữ liệu, hằng số chuẩn hóa động học
│
├── SIC-final/                    # Toàn bộ hồ sơ báo cáo Capstone Samsung Innovation Campus
│   ├── ENG/                      # Bộ hồ sơ tiếng Anh (Report, Slides, WBS, Action Plan, Script & QA)
│   ├── VN/                       # Bộ hồ sơ tiếng Việt (Báo cáo, Slide, WBS, Kế hoạch, Kịch bản & Hỏi đáp)
│   ├── assets/                   # 10 sơ đồ kỹ thuật chất lượng cao (300 DPI)
│   ├── scripts/                  # Scripts Python tự động tái sinh toàn bộ hồ sơ
│   └── HUONG_DAN_BAO_VE_VA_TONG_KET_SIC.md # Cẩm nang hướng dẫn bảo vệ đề tài
│
├── prompts/                      # 28 Master Prompts và báo cáo rà soát từng giai đoạn phát triển
│   └── README.md                 # Mục lục và phân loại chi tiết các prompt kỹ thuật
│
├── docs/                         # Tài liệu kiến trúc chuyên sâu và báo cáo kỹ thuật
│   ├── BAO_CAO_TONG_HOP_DU_AN_REHABAI.md
│   └── TAI_LIEU_MO_HINH_NHAN_DIEN_VA_CANH_BAO_REHABAI.md
│
├── Templates for Capstone Project/ # Biểu mẫu gốc của cuộc thi SIC
├── video/                        # Video mẫu hướng dẫn bài tập phục hồi chức năng
├── start_web.bat                 # Script chạy nhanh toàn bộ hệ thống bằng 1 click
└── .gitignore                    # Bộ lọc gitignore bảo vệ dữ liệu lớn (>170GB)
```

---

## 🚀 4. Hướng Dẫn Khởi Chạy Nhanh (Quickstart)

### Cách 1: Khởi chạy nhanh bằng script (Khuyên dùng trên Windows)
Nhấp đúp chuột vào file:
```bash
start_web.bat
```
Script sẽ tự động kiểm tra môi trường, khởi động backend FastAPI (cổng `8000`) và giao diện frontend Vite (cổng `5173`).

---

### Cách 2: Khởi chạy thủ công từng dịch vụ

#### 1. Khởi động Backend (FastAPI):
```bash
cd rehabai
set PYTHONPATH=.
set JWT_SECRET=local-development-secret-at-least-32-characters
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
- API Health Check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- Swagger API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### 2. Khởi động Frontend (React / Vite):
```bash
cd rehabai/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
- Truy cập giao diện người dùng: [http://127.0.0.1:5173](http://127.0.0.1:5173)

#### 3. Khởi động Chatbot Local (Ollama):
```bash
ollama run qwen2.5:7b
```
Chatbot sẽ tự động kết nối qua `http://127.0.0.1:11434` phục vụ tính năng AI Coach và trợ lý hỏi đáp y tế.

---

### Cách 3: Triển khai bằng Docker Compose
```bash
cd rehabai/deployment
docker compose up -d
```
Hệ thống sẽ chạy trọn vẹn 4 container: Backend, Frontend, Nginx Reverse Proxy (cổng `80`), và cơ sở dữ liệu PostgreSQL (cổng `5432`).

---

## 📊 5. Kết Quả Huấn Luyện & Đối Chuẩn Lâm Sàng (Benchmark)

Hệ thống được huấn luyện và đánh giá trên bộ dữ liệu **491 video lâm sàng thực tế** với quy trình kiểm định chéo bệnh nhân độc lập (**Leave-One-Subject-Out - LOSO 10-Fold Cross-Validation**):

| Chỉ Số Đánh Giá | Kết Quả Thực Nghiệm | Ý Nghĩa Lâm Sàng |
| :--- | :---: | :--- |
| **Độ chính xác LOSO (10-Fold)** | **43.79% ± 23.35%** | Phản ánh tính trung thực khi gặp bệnh nhân hoàn toàn mới (Zero-leakage) |
| **F1-Score vĩ mô (Macro F1)** | **0.421 ± 0.218** | Đảm bảo tính cân bằng giữa các lớp động tác |
| **Độ trễ suy luận (Inference Latency)** | **~18 ms / khung hình** | Đạt chuẩn phản hồi thời gian thực (>30 FPS trên CPU/GPU phổ thông) |
| **Tỷ lệ chặn cờ đỏ (Red Flag Recall)** | **100%** | 100% dấu hiệu đau ngực, méo mặt, ngưng thở được kích hoạt cảnh báo dừng tập |

---

## 📄 6. Hồ Sơ Capstone SIC (Samsung Innovation Campus)

Các tài liệu chính thức theo đúng định dạng cuộc thi SIC được lưu trữ đầy đủ trong thư mục `SIC-final/`:

| Loại Tài Liệu | Tiếng Anh (`SIC-final/ENG/`) | Tiếng Việt (`SIC-final/VN/`) |
| :--- | :--- | :--- |
| **Báo Cáo Tổng Kết** | `Dou_RehabAI_Final_Report_EN.docx` | `Dou_RehabAI_Bao_Cao_Tong_Ket_VN.docx` |
| **Slide Thuyết Trình** | `Dou_RehabAI_Presentation_EN.pptx` | `Dou_RehabAI_Slide_Thuyet_Trinh_VN.pptx` |
| **Kế Hoạch Hành Động** | `Dou_RehabAI_Action_Plan_EN.docx` | `Dou_RehabAI_Ke_Hoach_Hanh_Dong_VN.docx` |
| **Phân Rã Công Việc (WBS)**| `Dou_RehabAI_Work_Breakdown_Structure_EN.xlsx`| `Dou_RehabAI_Phan_Ra_Cong_Viec_WBS_VN.xlsx` |
| **Phiếu Tự Đánh Giá** | `Dou_RehabAI_Evaluation_Sheet_EN.docx` | `Dou_RehabAI_Phieu_Danh_Gia_VN.docx` |
| **Kịch Bản & Q&A Phản Biện**| `Dou_RehabAI_Presentation_Script_and_QA_EN.docx`| `Dou_RehabAI_Kich_Ban_Thuyet_Trinh_va_Phan_Bien_VN.docx`|

---

## 👥 7. Bản Quyền & Tác Giả

- **Dự Án**: RehabAI - Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên
- **Tác giả chính**: Đức Lương (Email: `kaka2002p3@gmail.com`).
- **Giấy phép**: Phát hành theo giấy phép mã nguồn mở [MIT License](LICENSE).
