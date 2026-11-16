# CẨM NANG BẢO VỆ VÀ TỔNG HỢP TOÀN BỘ BỘ HỒ SƠ CAPSTONE SIC
## Dự án: RehabAI: Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên
**Team Dou**: Đàm Đức Lương & Ngô Quang Minh  
**Chương trình**: Samsung Innovation Campus (SIC) — Khóa Học Trí Tuệ Nhân Tạo (AI Track)

---

## 1. Danh Mục Các File Nộp Bài Trong Thư Mục `SIC-final/`

| STT | File Nộp | Định Dạng | Mô Tả & Tiêu Chuẩn Đáp Ứng |
|:---:|---|:---:|---|
| 1 | `Dou_RehabAI_Final_Report.docx` | Word (.docx) | Báo cáo tổng kết 6 chương theo đúng mẫu của Samsung Innovation Campus, nhúng 10 biểu đồ thực nghiệm và 11 bảng chuẩn hóa. |
| 2 | `Dou_RehabAI_Presentation.pptx` | PowerPoint (.pptx) | Bộ slide 15 trang chuẩn 16:9 widescreen, thiết kế nhận diện Samsung Navy & Cyan, bố cục thẻ card hiện đại, nhúng đầy đủ biểu đồ. |
| 3 | `Dou_RehabAI_Action_Plan.docx` | Word (.docx) | Kế hoạch hành động dự án chuẩn 3 bảng của SIC (Goal, Abstract, Method, Data, Expected Outcome, Vai trò, Tiến độ & Nhận xét). |
| 4 | `Dou_RehabAI_Work_Breakdown_Structure.xlsx` | Excel (.xlsx) | Bảng phân rã công việc WBS gồm Cover Page và Sheet WBS chi tiết 19 đầu việc, ngày bắt đầu/kết thúc, phân công, trạng thái `Done` và Gantt chart. |
| 5 | `Dou_RehabAI_Evaluation_Sheet_Prepared.docx` | Word (.docx) | Phiếu đánh giá của Hội đồng chấm thi, điền sẵn thông tin dự án, tiêu chí 5 phần (100 điểm) và bảng đánh giá TRL (mức 1 - 9). |
| 6 | `Dou_RehabAI_Presentation_Script_and_QA.docx` | Word (.docx) | Kịch bản thuyết trình chi tiết từng slide (phân bổ 15 phút) và bộ câu hỏi phản biện bảo vệ đề tài kèm câu trả lời chuẩn. |
| 7 | `assets/` | Folder ảnh | Thư mục chứa 10 file ảnh sơ đồ kiến trúc, biểu đồ phân tích dữ liệu, ma trận nhầm lẫn, ablation study và UI mockup độ phân giải cao. |

---

## 2. Bảng "Số Liệu Đinh" Bắt Buộc Phải Nhớ Khi Thuyết Trình

Khi Ban giám khảo hỏi về kỹ thuật, các con số sau đây là bằng chứng thép khẳng định tính khoa học và thực chiến của nhóm:

| Chỉ số / Thông số | Giá trị thực tế | Ý nghĩa khoa học |
|---|:---:|---|
| **Tổng số video thô ban đầu** | **491 video** | Thu thập từ 10 bệnh nhân đột quỵ thật (`Sub 01` đến `Sub 10`). |
| **Số mẫu đạt Cổng chất lượng (Quality Gate)** | **387 mẫu (78.82%)** | Đã loại 104 mẫu (21.18%) bị che khuất khớp hoặc tracking visibility < 60%. |
| **Phân bố 4 bài tập** | Ex1: 31.8% \| Ex2: 16.8% \| Ex3: 26.9% \| Ex4: 24.6% | Phản ánh đúng nhu cầu phục hồi cơ năng chi trên thực tế. |
| **Tỷ lệ bài tập hoàn thành (Completeness)** | 187 Complete (48.3%) vs 200 Incomplete (51.7%) | Phản ánh đúng hạn chế vận động của bệnh nhân đột quỵ thực tế. |
| **Giao thức đánh giá (Cross-Validation)** | **Strict 10-Fold Subject-Wise LOSO** | Leave-One-Subject-Out: Không để cùng bệnh nhân xuất hiện ở cả Train và Test (chống rò rỉ dữ liệu). |
| **Accuracy mô hình sản xuất (RehabMotionNet v2)** | **43.79% ± 23.35%** | Vượt gấp 3 lần Majority baseline (15.15%), vượt Linear SVM (36.51%) và MLP (34.51%). |
| **Macro-F1 mô hình sản xuất** | **35.44% ± 27.04%** | F1 trung bình giữa 4 lớp không thiên vị số lượng mẫu. |
| **Độ nhạy từng lớp (Class Recall)** | Ex3: 66.35% \| Ex2: 55.38% \| Ex1: 46.34% \| Ex4: 37.89% | Cổ tay và khuỷu nhận diện tốt nhất; bàn tay và vai có hiện tượng đồng vận. |
| **Kích thước mô hình TorchScript C++** | **451.561 params (1.82 MiB)** | Cực nhẹ, chạy mượt trên CPU không cần card đồ họa rời đắt tiền. |
| **Độ trễ suy luận toàn chu kỳ (End-to-End Latency)** | **~42.5 ms** | MediaPipe (24ms) + TorchScript (11ms) + WebSocket/Render (7.5ms) $\rightarrow$ Đáp ứng 15 FPS (<66.6ms). |
| **Số lượng ca kiểm thử tự động (Test Suite)** | **144 tests (143 passed, 1 skipped)** | Kiểm chứng toàn diện từ schema đặc trưng, WebSocket, database đến guardrails chatbot. |
| **Mức độ sẵn sàng công nghệ hiện tại** | **TRL 5 (Integrated Prototype)** | Nguyên mẫu tích hợp hoàn chỉnh được kiểm chứng trong môi trường mô phỏng. |

---

## 3. Chiến Lược "Ghi Điểm Tuyệt Đối" Theo 5 Tiêu Chí Đánh Giá Của Samsung

### Tiêu chí 1: Ý TƯỞNG (IDEA - 10 Điểm)
* **Điểm nhấn**: Nhấn mạnh tính cấp bách của hơn 200.000 ca đột quỵ/năm tại Việt Nam, sự quá tải của chuyên viên phục hồi chức năng (1:50) và tỷ lệ bỏ tập tại nhà >60%.
* **Khác biệt**: Không sử dụng cảm biến đeo hay găng tay đắt tiền hàng nghìn USD. Hệ thống chỉ cần webcam thông thường, giúp mọi gia đình đều có thể tiếp cận.

### Tiêu chí 2: ỨNG DỤNG CÔNG NGHỆ (APPLICATION - 30 Điểm)
* **Điểm nhấn**:
  1. Trích xuất đặc trưng chuẩn hóa không gian: Dời gốc tọa độ về tâm hai vai và chia cho khoảng cách hai vai giúp bất biến với khoảng cách ngồi xa/gần camera.
  2. Kiến trúc mạng đa nhánh tiên tiến: Kết hợp PoseGraph (khớp vai/khuỷu/cổ tay), Hand Conv1D (42 điểm bàn tay) và MS-TCN (tích chập thời gian đa tỷ lệ với dilation 1, 2, 4).
  3. Đóng gói TorchScript C++ cho độ trễ <45ms.
  4. Kiến trúc 2 tầng bảo mật: Tách biệt Public Portal giáo dục và Protected `/app` cho phiên tập.

### Tiêu chí 3: KẾT QUẢ KHOA HỌC & ĐẠO ĐỨC AI (RESULT - 30 Điểm)
* **Điểm nhấn**:
  1. **Tính liêm chính khoa học**: Dũng cảm loại bỏ tuyên bố ảo 100% của mô hình cũ, công bố trung thực kết quả 10-fold LOSO trên bệnh nhân thật (43.79% Acc, 35.44% F1).
  2. **Quyết định an toàn y tế**: Vô hiệu hóa nhánh Completion Head (chỉ đạt 50.24% acc - ngang ngửa đoán mò) để không đánh lừa bệnh nhân; chuyển giao việc đếm rep cho máy trạng thái động học FSM đo góc thực tế.
  3. **Độ trễ thời gian thực**: Hoạt động mượt mà ở 15 FPS trên máy tính thông thường.

### Tiêu chí 4: QUẢN LÝ DỰ ÁN (PROJECT MANAGEMENT - 10 Điểm)
* **Điểm nhấn**:
  1. Phân chia vai trò rõ ràng: Đàm Đức Lương (Lead Dev/AI Core/Web) và Ngô Quang Minh (Researcher/Data Audit/Docs).
  2. Khả năng thích ứng vượt khó: Phát hiện sớm lỗi rò rỉ dữ liệu (data leakage) và tái cấu trúc toàn bộ quy trình kiểm thử.
  3. Hoàn thành 100% các mốc WBS trong 4 tuần.

### Tiêu chí 5: BÁO CÁO & THUYẾT TRÌNH (PRESENTATION & REPORT - 20 Điểm)
* **Điểm nhấn**: Slide thiết kế chuyên nghiệp, có đồ thị trực quan cho mọi luận điểm; báo cáo dày dặn, văn phong học thuật chuẩn mực, sẵn sàng phản biện xuất sắc.

---

## 4. Hướng Dẫn Mở & Kiểm Tra Hồ Sơ

Bạn có thể mở trực tiếp các file trong thư mục `SIC-final/` bằng các phần mềm tương ứng:
- File Word (`.docx`): Mở bằng Microsoft Word, Google Docs hoặc WPS Office.
- File PowerPoint (`.pptx`): Mở bằng Microsoft PowerPoint hoặc Google Slides để trình chiếu thử (F5).
- File Excel (`.xlsx`): Mở bằng Microsoft Excel hoặc Google Sheets để xem bảng tiến độ và biểu đồ Gantt.
- File ảnh (`assets/`): Mở xem trực tiếp để dùng cho poster hoặc tài liệu in ấn bổ sung nếu cần.

