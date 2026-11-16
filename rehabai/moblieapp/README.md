# RehabAI Mobile

Giao diện Android bằng Flutter dành cho hệ thống RehabAI. Phiên bản hiện tại là UI prototype với dữ liệu mẫu, gồm:

- Đăng nhập.
- Trang tổng quan.
- Danh sách bài tập phục hồi.
- Theo dõi tiến trình và lịch sử.
- Hồ sơ, cài đặt và cảnh báo an toàn.

## Chạy ứng dụng

Máy cần cài Flutter SDK và Android Studio/Android SDK.

```powershell
cd D:\PhucHoiChucNangTay\rehabai\moblieapp
flutter pub get
flutter run
```

Kiểm tra build:

```powershell
flutter analyze
flutter test
flutter build apk --debug
```

UI chưa gọi backend. Khi tích hợp, Android Emulator truy cập backend trên máy host bằng `http://10.0.2.2:8000`.

