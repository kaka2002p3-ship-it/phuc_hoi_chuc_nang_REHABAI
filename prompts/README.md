# 📑 Thư Mục Prompt Phát Triển Dự Án RehabAI

Thư mục này lưu trữ toàn bộ **28 Prompt kỹ thuật**, tài liệu chỉ đạo kiến trúc (Master Prompts) và các báo cáo rà soát từng giai đoạn (Stage Audit & Correction Reports) trong suốt quá trình nghiên cứu, xây dựng và hoàn thiện hệ thống **RehabAI: Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên**.

---

## 📌 Phân Loại & Mục Lục Tài Liệu

### 1. Kiến Trúc & Phát Triển Cốt Lõi (Architecture & Core Master Prompts)
- **`RehabAI_Two_Layer_Architecture_Correction_Prompt.md`**: Prompt chuẩn hóa kiến trúc 2 lớp phân tách độc lập: Lớp 1 (Computer Vision AI định lượng cử động khách quan) và Lớp 2 (Hệ thống an toàn y tế dựa trên quy tắc lâm sàng cứng).
- **`RehabAI_3Stream_CTRGCN_MSTCN_Master_Prompt.md`**: Prompt thiết kế mô hình Deep Learning 3 luồng (Joint, Bone, Motion) kết hợp CTR-GCN và MS-TCN cho phân tích chuyển động chuỗi thời gian.
- **`RehabAI_MASTER_PROMPT_V3_1_RTX4060_LAPTOP_MANUAL_EXTRACT.md`**: Hướng dẫn tối ưu hóa pipeline trích xuất landmark MediaPipe và huấn luyện trên GPU máy trạm di động (RTX 4060 Laptop).
- **`RehabAI_Release_Verification_Prompt.md`**: Tiêu chuẩn kiểm thử và tiêu chí nghiệm thu bản phát hành hoàn thiện (Verification & Validation).

---

### 2. Dữ Liệu & Kiểm Thử Tổng Quát Hóa (Data Pipeline & LOSO Generalization)
- **`Prompt Phase 4.5 – Leakage & Generalization Audit cho RehabAI.md`**: Rà soát triệt để hiện tượng rò rỉ dữ liệu (Data Leakage) giữa các bệnh nhân và các buổi tập.
- **`Prompt Phase 4.6 – Full 491 Video Extraction & LOSO Training.md`**: Quy trình trích xuất toàn bộ 491 video lâm sàng và thiết lập pipeline huấn luyện Leave-One-Subject-Out (LOSO) 10-fold.
- **`Prompt Phase 4.7 – Verify Real Data + True LOSO.md`**: Xác thực tính trung thực của dữ liệu thực nghiệm và kết quả đánh giá chéo LOSO nghiêm ngặt (43.79% ± 23.35%).
- **`RehabAI_Local_AI_Data_Collection_Training_Master_Prompt.md`**: Hướng dẫn thu thập, gán nhãn và chuẩn hóa dữ liệu phục hồi chức năng cục bộ.

---

### 3. Trợ Lý Ảo Chatbot AI & RAG Y Tế (Ollama Medical Companion)
- **`RehabAI_Ollama_Chatbot_MASTER_VI_EN.md`**: Master prompt cho Chatbot AI song ngữ (Việt - Anh) chạy mô hình local (Ollama Qwen 2.5:7B), tích hợp RAG tri thức y tế đã duyệt và cơ chế chặn dấu hiệu cờ đỏ (Red Flags / Cấp cứu 115).
- **`RehabAI_GPT56Sol_Ollama_Master_Reviewer.md`**: Prompt đánh giá chéo an toàn và độ tin cậy của câu trả lời từ LLM y tế.

---

### 4. Giao Diện & Tính Năng Mở Rộng (UI/UX & Extension Features)
- **`Prompt cho frontentback.md`**: Yêu cầu kết nối giao diện React/Vite với backend FastAPI qua REST API và WebSocket inference.
- **`RehabAI_WebOnly_Beautiful_UIUX_Implementation_Prompt.md`**: Chỉ đạo thiết kế giao diện Web Care hiện đại, chuẩn tiếp cận cho người sau tai biến/chấn thương.
- **`RehabAI_Homepage_Knowledge_Research_Master_Prompt_V2.md`**: Thiết kế trang chủ, cổng thông tin nghiên cứu và tra cứu kiến thức phục hồi chức năng.
- **`RehabAI_Deep_Breathing_No_Training_Master_Prompt.md`**: Tích hợp tính năng bài tập thở sâu (Deep Breathing) dựa trên động học lồng ngực không cần mô hình AI huấn luyện.
- **`RehabAI_Neck_Lateral_Stretch_No_Training_Master_Prompt.md`**: Thiết kế bài tập nghiêng cổ phục hồi chức năng dựa trên phân tích góc xương cổ và vai.
- **`RehabAI_Neck_Safe_Experimental_Branch_Master_Prompt.md`**: Quy chuẩn an toàn cho nhánh thử nghiệm bài tập cổ.
- **`RehabAI_Neck_Standalone_Prototype_Master_Prompt.md`**: Nguyên mẫu độc lập kiểm chứng bài tập vận động cổ.

---

### 5. Báo Cáo & Sửa Lỗi Giai Đoạn Antigravity (Phase 4.7 Audit & Corrections)
- **`ANTIGRAVITY_PHASE_4_7_STAGE_1_READ_ONLY_AUDIT.md`**: Báo cáo kiểm toán đọc độc lập Giai đoạn 4.7.
- **`ANTIGRAVITY_PHASE_4_7_STAGE_1_CORRECTION_REV2.md`**: Hiệu chỉnh Giai đoạn 4.7 Stage 1.
- **`ANTIGRAVITY_PHASE_4_7_STAGE_2_PIPELINE_HARDENING.md`**: Gia cố pipeline xử lý dữ liệu và kiểm thử tính bất biến của hash provenance.
- **`ANTIGRAVITY_PHASE_4_7_STAGE_2_CORRECTION.md`**: Báo cáo sửa đổi Giai đoạn 4.7 Stage 2.
- **`ANTIGRAVITY_PHASE_4_7_STAGE_2_CORRECTION_REV2.md`**: Hiệu chỉnh lần 2 Stage 2.
- **`ANTIGRAVITY_PHASE_4_7_STAGE_2_CORRECTION_REV3.md`**: Hiệu chỉnh lần 3 Stage 2.
- **`ANTIGRAVITY_PHASE_4_7_STAGE_2_CORRECTION_REV3_1.md`**: Hiệu chỉnh chi tiết Stage 2 Rev 3.1.
- **`ANTIGRAVITY_PHASE_4_7_STAGE_2_CORRECTION_REV3_1_COMPLETION.md`**: Nghiệm thu hoàn tất Stage 2 Rev 3.1.
- **`PHASE_4_7_STAGE_2_CORRECTION_REV3_1_REPORT.md`**: Báo cáo kỹ thuật tổng kết Stage 2 Rev 3.1.
- **`PHASE_4_7_STAGE_2_CORRECTION_REV3_1_COMPLETION_REPORT.md`**: Biên bản hoàn thành rà soát.
- **`PHASE_4_7_STAGE_2_CORRECTION_REV3_1_CODEX_REPORT.md`**: Báo cáo đồng thuận kỹ thuật với tiêu chuẩn Codex.
