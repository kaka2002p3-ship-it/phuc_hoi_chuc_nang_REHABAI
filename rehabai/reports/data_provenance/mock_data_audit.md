# Báo cáo Kiểm tra Dữ liệu (Mock Data Audit)

## 1. Phương pháp Kiểm tra
Theo yêu cầu của quy trình **RehabAI - Phase 4.7**, tiến hành rà soát mã nguồn tiền xử lý và trích xuất dữ liệu:
- Quét các từ khóa: `random`, `np.random`, `synthetic`, `mock` trong toàn bộ quy trình sinh file đặc trưng `.npz` và `.h5`.
- Kiểm tra mã nguồn tệp: `scripts/mock_extraction.py`.

## 2. Kết quả Phát hiện
Phát hiện mã nguồn trực tiếp sử dụng hàm sinh số ngẫu nhiên để tạo đặc trưng khung xương 3D thay vì trích xuất từ video thật:
```python
# Trích xuất từ scripts/mock_extraction.py
pose = np.random.normal(base_val, 0.1, size=(n_frames, 33, 4)).astype(np.float32)
lh = np.random.normal(base_val, 0.1, size=(n_frames, 21, 3)).astype(np.float32)
rh = np.random.normal(base_val, 0.1, size=(n_frames, 21, 3)).astype(np.float32)
```

Tất cả các tệp tính năng (features `.h5`) hiện tại trong hệ thống đều được dẫn xuất từ dữ liệu tạo bằng đoạn mã trên. Việc thay đổi biến `base_val` giúp mô hình dễ dàng học được một số sự khác biệt cơ bản (nhằm test luồng chạy), nhưng hoàn toàn **không mang đặc điểm động học cơ thể thực tế (kinematics)**.

## 3. Kết luận
Tình trạng dữ liệu:
> **SYNTHETIC**

Dựa trên nguyên tắc nghiêm ngặt của dự án, mọi đánh giá và suy diễn hiệu suất (Metrics, Confusion Matrix) trên tập dữ liệu hiện tại đều bị vô hiệu. Dừng quá trình huấn luyện/đánh giá mô hình cho đến khi Dữ liệu Thật (Real Data) được trích xuất hoàn chỉnh.
