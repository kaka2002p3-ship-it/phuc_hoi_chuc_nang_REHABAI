# RehabAI – frontend/backend

Ứng dụng React/Vite giao tiếp với FastAPI qua HTTP và WebSocket. Đây là prototype nghiên cứu/demo, không phải thiết bị chẩn đoán hay bằng chứng hiệu quả lâm sàng.

## Chạy phát triển

```powershell
cd D:\PhucHoiChucNangTay\rehabai
$env:PYTHONPATH="."
$env:JWT_SECRET="local-development-secret-at-least-32-characters"
uvicorn backend.main:app --reload --port 8000
```

Terminal khác:

```powershell
cd D:\PhucHoiChucNangTay\rehabai\frontend
npm run dev
```

Tạo tài khoản tại `/login`. Các API chứa dữ liệu người dùng yêu cầu `Authorization: Bearer <token>`. WebSocket dùng `/ws/inference?token=<token>` và chỉ được truy cập session thuộc tài khoản đó.

## API canonical

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/users/me`
- `GET /api/users/me/export`, `DELETE /api/users/me` để xuất/xóa dữ liệu cá nhân
- `POST /api/exercise/session/start`, `POST /api/exercise/session/end`
- `POST /api/pain/before`, `POST /api/pain/after`
- `GET /api/exercise/history`
- `GET /api/reports/summary`, `GET /api/reports/progress`
- `GET /api/settings`, `PUT /api/settings`
- `POST /api/chat`
- WebSocket `/ws/inference?token=...`

Các route `/api/sessions*` chỉ là alias tương thích tạm thời, có header `Deprecation` và sẽ ngừng sau ngày 31/12/2026.

## Database và migration

SQLite dùng cho phát triển; PostgreSQL dùng trong Docker. Production không tự chạy `create_all` hay vá schema khi import. Container backend chạy `alembic upgrade head` trước Uvicorn.

## Docker

```powershell
cd D:\PhucHoiChucNangTay\rehabai\deployment
Copy-Item .env.example .env
# Thay POSTGRES_PASSWORD, DATABASE_URL, JWT_SECRET và CORS_ORIGINS.
docker compose up --build -d
```

Compose từ chối khởi động nếu thiếu `JWT_SECRET`. Artifact production được mount read-only vào `/app/artifacts/model_v2`; model loader kiểm tra feature contract và SHA-256 trước khi phục vụ.

## Kiểm thử

```powershell
cd D:\PhucHoiChucNangTay\rehabai
$env:PYTHONPATH="."
python -m pytest tests shared/tests -q
cd frontend
npm run build
```

Model production hiện chỉ là kết quả nghiên cứu trên 10 subject. Không quảng bá độ chính xác 100%; completion head không được dùng làm điểm lâm sàng.
