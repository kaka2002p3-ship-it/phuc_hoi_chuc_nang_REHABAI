# ⚙️ Scripts Sinh Bộ Tài Liệu Cuộc Thi Samsung Innovation Campus (SIC)

Thư mục này chứa toàn bộ các tập lệnh Python tự động hóa việc xuất sinh các báo cáo, slide thuyết trình, bảng tính WBS, phiếu đánh giá và kế hoạch hành động theo đúng mẫu chuẩn của **Samsung Innovation Campus AI Capstone Project**.

---

## 📂 Danh Sách Scripts

| Tên Script | Mục Đích Xuất Sinh |
| :--- | :--- |
| **`build_pack_eng.py`** | Sinh toàn bộ gói tài liệu tiếng Anh trong `SIC-final/ENG/` (Báo cáo tổng kết `.docx`, Slide thuyết trình 15 trang widescreen `.pptx`, Action Plan `.docx`, WBS có biểu đồ Gantt `.xlsx`, Phiếu đánh giá `.docx`, Kịch bản & Q&A `.docx`). |
| **`build_pack_vn.py`** | Sinh toàn bộ gói tài liệu tiếng Việt trong `SIC-final/VN/` (Báo cáo tổng kết `.docx`, Slide thuyết trình 15 trang `.pptx`, Kế hoạch hành động `.docx`, WBS tiếng Việt `.xlsx`, Phiếu tự đánh giá `.docx`, Kịch bản thuyết trình & Trả lời phản biện `.docx`). |
| **`build_final_report.py`** | Script tạo báo cáo nghiên cứu chi tiết 6 chương với đầy đủ 10 sơ đồ kỹ thuật và 11 bảng đối chuẩn. |
| **`build_presentation.py`** | Script tạo slide thuyết trình theo phong cách Samsung Deep Navy & Blue hiện đại. |
| **`build_action_plan.py`** | Script xuất kế hoạch hành động 6 pha theo biểu mẫu SIC. |
| **`update_wbs.py`** | Script tạo file Excel WBS chuyên nghiệp với các cột WBS ID, Nhiệm vụ, Người phụ trách, Ngày bắt đầu/kết thúc, Trạng thái và thanh Gantt có màu sắc. |
| **`generate_script_qa.py`** | Script xuất kịch bản thuyết trình từng slide kèm 12 câu hỏi phản biện hóc búa của ban giám khảo và câu trả lời mẫu. |

---

## 🚀 Hướng Dẫn Tái Sinh Bộ Tài Liệu

Nếu bạn cần sửa đổi thông tin hoặc cập nhật số liệu và muốn tái sinh toàn bộ hồ sơ, hãy mở terminal từ thư mục gốc của dự án (`d:\PhucHoiChucNangTay`) và chạy:

```bash
# 1. Cài đặt các thư viện cần thiết (nếu chưa có)
python -m pip install python-docx python-pptx openpyxl

# 2. Chạy sinh gói tài liệu tiếng Anh
python SIC-final/scripts/build_pack_eng.py

# 3. Chạy sinh gói tài liệu tiếng Việt
python SIC-final/scripts/build_pack_vn.py
```
Toàn bộ sản phẩm sẽ được tự động ghi đè và cập nhật vào `SIC-final/ENG/` và `SIC-final/VN/`.
