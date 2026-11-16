# Hướng Dẫn Chạy Web App RehabAI

## Cách 1: Double-click (Dễ nhất) ⭐

Sau khi tôi đã tạo file `start_web.bat` ở thư mục gốc:

1. Mở File Explorer vào `D:\PhucHoiChucNangTay\`
2. **Double-click** vào `start_web.bat`
3. Đợi 2 terminal windows mở ra
4. Mở trình duyệt: **http://localhost:5173**

## Cách 2: VS Code Tasks ⭐⭐

Tôi đã tạo `.vscode/tasks.json` cho phép chạy qua VS Code:

1. Mở VS Code
2. Mở thư mục `D:\PhucHoiChucNangTay\rehabai\frontend`
3. Nhấn **Ctrl + Shift + P**
4. Gõ: `Tasks: Run Task`
5. Chọn một trong:
   - **"Start frontend dev server"** - chỉ chạy frontend
   - **"Start backend server"** - chỉ chạy backend
   - **"Start both servers"** - chạy cả hai

## Cách 3: VS Code Debug ⭐⭐⭐

Tôi đã tạo `.vscode/launch.json`:

1. Mở VS Code
2. Vào Run and Debug panel (Ctrl + Shift + D)
3. Chọn configuration:
   - **"Run Frontend (Vite Dev Server)"**
   - **"Run Backend (Uvicorn)"**
   - **"Run Both Servers"**

## Cách 4: Terminal thủ công

Nếu các cách trên không hoạt động, mở **2 terminal** trong VS Code:

### Terminal 1 - Backend:
```powershell
cd D:\PhucHoiChucNangTay\rehabai
$env:PYTHONPATH="."
$env:JWT_SECRET="local-development-secret-at-least-32-characters"
$env:APP_ENV="development"
python -m uvicorn backend.main:app --reload --port 8000
```

### Terminal 2 - Frontend:
```powershell
cd D:\PhucHoiChucNangTay\rehabai\frontend
npm install    # Chỉ lần đầu
npm run dev
```

## Kiểm tra

- **Backend API**: http://127.0.0.1:8000/api/health
- **Backend Docs**: http://127.0.0.1:8000/docs
- **Frontend**: http://localhost:5173

## Lỗi thường gặp

### "node not found"
Cài Node.js: https://nodejs.org/

### "python not found"
Cài Python 3.11+: https://www.python.org/

### "port already in use"
```powershell
netstat -ano | findstr :8000
netstat -ano | findstr :5173
# Kill process
taskkill /PID <pid_number> /F
```

### "npm install fails"
```powershell
cd D:\PhucHoiChucNangTay\rehabai\frontend
npm cache clean --force
npm install
```

### "JWT_SECRET required"
Đặt biến môi trường trước khi chạy backend (xem ở trên).
