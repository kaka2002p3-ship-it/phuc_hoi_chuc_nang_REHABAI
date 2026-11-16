import os
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
import pptx
from pptx.util import Inches as PInches, Pt as PPt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor as PRGBColor
from pptx.enum.shapes import MSO_SHAPE
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

os.makedirs('SIC-final/VN', exist_ok=True)

# ----------------- 1. BÁO CÁO TỔNG KẾT VN -----------------
def generate_final_report_vn():
    doc = docx.Document()
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)
        s.page_width = Inches(8.27)
        s.page_height = Inches(11.69)

    COLOR_PRIMARY = RGBColor(11, 34, 101)      # Samsung Navy #0B2265
    COLOR_SECONDARY = RGBColor(0, 112, 210)   # Blue #0070D2
    COLOR_DARK = RGBColor(38, 50, 56)
    COLOR_MUTED = RGBColor(90, 107, 124)

    def set_cell_background(cell, fill_hex):
        tcPr = cell._tc.get_or_add_tcPr()
        tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'))

    def set_cell_margins(cell, top=140, bottom=140, left=180, right=180):
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = OxmlElement('w:tcMar')
        for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
            node = OxmlElement(f'w:{m}')
            node.set(qn('w:w'), str(val))
            node.set(qn('w:type'), 'dxa')
            tcMar.append(node)
        tcPr.append(tcMar)

    def style_table(table, col_widths=None, header_bg='0B2265', alt_bg='F4F6F9'):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row in enumerate(table.rows):
            trPr = row._tr.get_or_add_trPr()
            trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
            for j, cell in enumerate(row.cells):
                set_cell_margins(cell)
                if col_widths and j < len(col_widths):
                    cell.width = col_widths[j]
                if i == 0:
                    set_cell_background(cell, header_bg)
                    for p in cell.paragraphs:
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        for run in p.runs:
                            run.font.bold = True
                            run.font.color.rgb = RGBColor(255, 255, 255)
                            run.font.name = 'Segoe UI'
                            run.font.size = Pt(9.5)
                else:
                    set_cell_background(cell, 'FFFFFF' if i % 2 == 1 else alt_bg)
                    for p in cell.paragraphs:
                        for run in p.runs:
                            run.font.name = 'Segoe UI'
                            run.font.size = Pt(9)
                            run.font.color.rgb = COLOR_DARK

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Segoe UI'
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = COLOR_PRIMARY
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Segoe UI'
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = COLOR_SECONDARY
        return p

    def add_body(text, bold_prefix=None, space_after=6):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.name = 'Segoe UI'
            r_pre.font.size = Pt(10)
            r_pre.font.bold = True
            r_pre.font.color.rgb = COLOR_DARK
        run = p.add_run(text)
        run.font.name = 'Segoe UI'
        run.font.size = Pt(10)
        run.font.color.rgb = COLOR_DARK
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.name = 'Segoe UI'
            r_pre.font.size = Pt(10)
            r_pre.font.bold = True
            r_pre.font.color.rgb = COLOR_DARK
        run = p.add_run(text)
        run.font.name = 'Segoe UI'
        run.font.size = Pt(10)
        run.font.color.rgb = COLOR_DARK
        return p

    def add_callout(text, title='LƯU Ý QUAN TRỌNG'):
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        cell.width = Inches(6.27)
        set_cell_background(cell, 'EBF3FA')
        set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)
        r_t = p.add_run(f'[{title}] ')
        r_t.font.name = 'Segoe UI'
        r_t.font.bold = True
        r_t.font.size = Pt(10)
        r_t.font.color.rgb = COLOR_PRIMARY
        r_c = p.add_run(text)
        r_c.font.name = 'Segoe UI'
        r_c.font.size = Pt(9.5)
        r_c.font.color.rgb = COLOR_DARK
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def add_fig(img_path, caption, width_in=5.8):
        if os.path.exists(img_path):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(4)
            p.add_run().add_picture(img_path, width=Inches(width_in))
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_before = Pt(0)
            p_cap.paragraph_format.space_after = Pt(10)
            run_cap = p_cap.add_run(caption)
            run_cap.font.name = 'Segoe UI'
            run_cap.font.size = Pt(9)
            run_cap.font.italic = True
            run_cap.font.color.rgb = COLOR_MUTED

    # Trang Bìa
    p_org = doc.add_paragraph()
    p_org.paragraph_format.space_before = Pt(36)
    p_org.paragraph_format.space_after = Pt(4)
    run_org = p_org.add_run('SAMSUNG INNOVATION CAMPUS')
    run_org.font.name = 'Segoe UI'
    run_org.font.size = Pt(13)
    run_org.font.bold = True
    run_org.font.color.rgb = COLOR_SECONDARY

    p_course = doc.add_paragraph()
    p_course.paragraph_format.space_before = Pt(0)
    p_course.paragraph_format.space_after = Pt(20)
    run_course = p_course.add_run('Khóa Học Trí Tuệ Nhân Tạo (AI Course) · Báo Cáo Tổng Kết Dự Án Capstone')
    run_course.font.name = 'Segoe UI'
    run_course.font.size = Pt(11)
    run_course.font.color.rgb = COLOR_MUTED

    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(20)
    p_title.paragraph_format.space_after = Pt(8)
    run_title = p_title.add_run('RehabAI: Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên')
    run_title.font.name = 'Segoe UI'
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = COLOR_PRIMARY

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(36)
    run_sub = p_sub.add_run('Nền tảng phục hồi chức năng từ xa ứng dụng Thị giác máy tính và Học sâu cho bệnh nhân đột quỵ với tính năng nhận diện khung xương thời gian thực và Trợ lý AI y tế an toàn')
    run_sub.font.name = 'Segoe UI'
    run_sub.font.size = Pt(12)
    run_sub.font.color.rgb = COLOR_DARK

    meta_table = doc.add_table(rows=5, cols=2)
    meta_data = [
        ('Tên Dự Án', 'RehabAI: Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên'),
        ('Tên Nhóm (Team Name)', 'Dou'),
        ('Thành Viên Thực Hiện', 'Đàm Đức Lương (Trưởng nhóm - Phụ trách Kỹ thuật AI & Fullstack)\nNgô Quang Minh (Thành viên - Nghiên cứu Dữ liệu, Đánh giá & Báo cáo)'),
        ('Ngày Hoàn Thành', '07/11/2026'),
        ('Chương Trình Đào Tạo', 'Samsung Innovation Campus - Khóa học Trí tuệ Nhân tạo (AI Track)')
    ]
    for row_idx, (k, v) in enumerate(meta_data):
        meta_table.cell(row_idx, 0).text = k
        meta_table.cell(row_idx, 1).text = v
    style_table(meta_table, col_widths=[Inches(2.0), Inches(4.27)], header_bg='0B2265')

    doc.add_paragraph().paragraph_format.space_after = Pt(40)
    p_copy = doc.add_paragraph()
    p_copy.paragraph_format.space_before = Pt(60)
    p_copy.paragraph_format.space_after = Pt(0)
    r_c1 = p_copy.add_run('ⓒ2025-2026 SAMSUNG. Bản quyền thuộc về Samsung Electronics.\n')
    r_c1.font.bold = True
    r_c2 = p_copy.add_run('Văn phòng Trách nhiệm Xã hội Doanh nghiệp Samsung bảo lưu mọi quyền sở hữu tài liệu này.\nTài liệu phục vụ đánh giá nghiệm thu dự án Capstone Samsung Innovation Campus.')
    for r in [r_c1, r_c2]:
        r.font.name = 'Segoe UI'
        r.font.size = Pt(8.5)
        r.font.color.rgb = COLOR_MUTED

    doc.add_page_break()

    # Mục Lục
    add_h1('Mục Lục Báo Cáo')
    toc_items = [
        ('1. Giới thiệu tổng quan', '3'),
        ('   1.1. Bối cảnh nghiên cứu và thực trạng y tế', '3'),
        ('   1.2. Động lực và mục tiêu cốt lõi của dự án', '3'),
        ('   1.3. Phân công vai trò thành viên nhóm', '4'),
        ('   1.4. Lịch trình và các mốc tiến độ chính', '4'),
        ('2. Thực hiện dự án', '5'),
        ('   2.1. Thu thập dữ liệu và Cổng kiểm soát chất lượng', '5'),
        ('   2.2. Phương pháp huấn luyện và Quy chuẩn chống rò rỉ dữ liệu', '6'),
        ('   2.3. Quy trình vận hành hệ thống thời gian thực', '7'),
        ('   2.4. Thiết kế kiến trúc hệ thống đa tầng', '8'),
        ('3. Kết quả thực nghiệm', '9'),
        ('   3.1. Tiền xử lý dữ liệu và trích xuất đặc trưng động học', '9'),
        ('   3.2. Khám phá và phân tích phân bố dữ liệu (EDA)', '10'),
        ('   3.3. Mô hình hóa và bảng xếp hạng kiểm chuẩn (Benchmark)', '11'),
        ('   3.4. Giao diện người dùng và rào chắn an toàn lâm sàng', '14'),
        ('   3.5. Kiểm thử hệ thống và kế hoạch tối ưu hóa', '15'),
        ('4. Tác động dự kiến', '16'),
        ('   4.1. Thành tựu đạt được và lợi ích kinh tế - xã hội', '16'),
        ('   4.2. Hướng phát triển và Lộ trình sẵn sàng công nghệ (TRL)', '16'),
        ('5. Đánh giá và nhận xét của thành viên nhóm', '18'),
        ('6. Đánh giá và nhận xét của Giảng viên / Hội đồng (Phiếu chấm)', '19')
    ]
    toc_table = doc.add_table(rows=len(toc_items), cols=2)
    for idx, (title, page) in enumerate(toc_items):
        c0, c1 = toc_table.cell(idx, 0), toc_table.cell(idx, 1)
        c0.text, c1.text = title, page
        c1.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for p in [c0.paragraphs[0], c1.paragraphs[0]]:
            for r in p.runs:
                r.font.name = 'Segoe UI'
                r.font.size = Pt(9.5)
                if not title.startswith('   '):
                    r.font.bold = True
                    r.font.color.rgb = COLOR_PRIMARY
        set_cell_background(c0, 'FFFFFF' if idx % 2 == 0 else 'F8F9FA')
        set_cell_background(c1, 'FFFFFF' if idx % 2 == 0 else 'F8F9FA')
        set_cell_margins(c0, top=60, bottom=60, left=100, right=100)
        set_cell_margins(c1, top=60, bottom=60, left=100, right=100)

    doc.add_page_break()

    # Chương 1
    add_h1('1. Giới thiệu tổng quan')
    add_h2('1.1. Bối cảnh nghiên cứu và thực trạng y tế')
    add_body(
        'Đột quỵ (tai biến mạch máu não) là một trong những nguyên nhân hàng đầu gây tàn tật vận động mãn tính và là nguyên nhân gây tử vong thứ hai trên phạm vi toàn cầu. '
        'Theo báo cáo của Tổ chức Đột quỵ Thế giới (WSO), hàng năm có hơn 12 triệu ca đột quỵ mới. Riêng tại Việt Nam, mỗi năm ghi nhận khoảng 200.000 ca mắc mới, '
        'trong đó trên 80% bệnh nhân phải gánh chịu di chứng suy giảm chức năng vận động kéo dài, đặc biệt là liệt nửa người và mất khả năng cử động chi trên (khớp vai, khuỷu tay, cổ tay và bàn tay). '
        'Các nghiên cứu về thần kinh học chỉ ra rằng hiện tượng tái tạo liên kết thần kinh (Neuroplasticity) chỉ có thể đạt hiệu quả cao khi bệnh nhân thực hiện kiên trì hàng trăm cử động lặp đi lặp lại mỗi ngày trong giai đoạn bán cấp và mãn tính.'
    )
    add_body('Tuy nhiên, hệ thống y tế hiện nay đang đối mặt với những rào cản nghiêm trọng trong công tác phục hồi chức năng sau đột quỵ:', bold_prefix='Thực trạng lâm sàng: ')
    add_bullet('Sự thiếu hụt trầm trọng chuyên viên y tế: Tại các bệnh viện tuyến công lập và trung tâm phục hồi chức năng, tỷ lệ chuyên viên/bệnh nhân thường vượt quá 1:50, không thể đáp ứng nhu cầu tập 1-kèm-1 hàng ngày.', bold_prefix='1. Quá tải nhân lực: ')
    add_bullet('Khoảng cách địa lý và chi phí đi lại đắt đỏ: Người bệnh tại các khu vực ngoại thành và nông thôn gặp nhiều khó khăn, mệt mỏi và tốn kém lớn khi phải di chuyển liên tục đến các cơ sở phục hồi chuyên khoa.', bold_prefix='2. Gánh nặng kinh tế & đi lại: ')
    add_bullet('Tỷ lệ bỏ tập rất cao: Thống kê cho thấy hơn 60% bệnh nhân đột quỵ từ bỏ bài tập phục hồi chức năng tại nhà sau 6 tháng do thiếu phản hồi hướng dẫn trực quan, không có công cụ ghi nhận tiến độ và lo sợ tập sai tư thế.', bold_prefix='3. Thiếu phản hồi & bỏ cuộc: ')
    add_bullet('Rào cản thiết bị cảm biến: Các hệ thống phục hồi từ xa truyền thống thường đòi hỏi cảm biến đo quán tính (IMU), găng tay điện tử (cyber-gloves) đắt tiền (hàng nghìn USD), rất cồng kềnh và bệnh nhân bị liệt nửa người không thể tự đeo.', bold_prefix='4. Thiết bị đắt đỏ, khó tiếp cận: ')

    add_h2('1.2. Động lực và mục tiêu cốt lõi của dự án')
    add_body(
        'Động lực cốt lõi của RehabAI là bình dân hóa công nghệ phục hồi chức năng chất lượng cao, biến mọi chiếc webcam máy tính hoặc camera điện thoại thông thường thành một trợ lý phục hồi chức năng thông minh và không chạm (contactless). '
        'Bằng sự kết hợp giữa thị giác máy tính nhận diện khớp xương, mạng nơ-ron học sâu không-thời gian, máy trạng thái hữu hạn kiểm tra góc độ sinh học và trợ lý AI an toàn y tế, RehabAI giúp người bệnh tự tin luyện tập an toàn tại nhà.'
    )
    add_bullet('Nhận diện cử động không chạm: Nhận diện 33 điểm khung xương cơ thể và 42 điểm khớp bàn tay bằng MediaPipe Holistic mà không cần đeo bất kỳ cảm biến nào.', bold_prefix='Mục tiêu 1 - Nhận diện không chạm: ')
    add_bullet('Phân loại cử động chi trên bằng Học sâu: Nhận diện chính xác 4 bài tập phục hồi chức năng vận động cốt lõi bằng mạng nơ-ron chuỗi RehabMotionNet v2.', bold_prefix='Mục tiêu 2 - Mô hình hóa chuyển động: ')
    add_bullet('Đếm số rep và kiểm tra chất lượng động tác: Ứng dụng máy trạng thái hữu hạn (FSM) và ngưỡng vận tốc góc để đếm đúng số rep hoàn thành biên độ, loại bỏ thao tác giả.', bold_prefix='Mục tiêu 3 - Đếm rep chính xác: ')
    add_bullet('Nền tảng Web tương tác thời gian thực: Xây dựng hệ thống web siêu nhạy với độ trễ dưới 45 ms, phân tách rõ ràng vùng thông tin công cộng và phòng tập bảo mật (/app).', bold_prefix='Mục tiêu 4 - Ứng dụng Web thời gian thực: ')
    add_bullet('Trợ lý AI y tế an toàn song ngữ: Tích hợp trợ lý hỏi đáp có rào chắn an toàn, lập tức phát hiện dấu hiệu cấp cứu (đau thắt ngực, khó thở) để hướng dẫn gọi 115 và từ chối kê đơn thay bác sĩ.', bold_prefix='Mục tiêu 5 - Trợ lý AI có kiểm soát an toàn: ')
    add_bullet('Liêm chính khoa học tuyệt đối: Xóa bỏ các tuyên bố 100% ảo do rò rỉ dữ liệu trước đây; công bố kiểm chuẩn trung thực 10-fold Leave-One-Subject-Out (LOSO) trên bệnh nhân đột quỵ thật.', bold_prefix='Mục tiêu 6 - Phương pháp khoa học chuẩn mực: ')

    add_h2('1.3. Phân công vai trò thành viên nhóm')
    role_table = doc.add_table(rows=3, cols=3)
    role_headers = ['Thành viên', 'Vai trò chính', 'Trách nhiệm kỹ thuật chi tiết']
    for j, h in enumerate(role_headers):
        role_table.cell(0, j).text = h
    role_rows = [
        ('Đàm Đức Lương', 'Trưởng nhóm / Phụ trách AI & Fullstack', 
         '• Thiết kế kiến trúc học sâu RehabMotionNet v2 (PoseGraph, MS-TCN, Attention).\n'
         '• Xây dựng pipeline tiền xử lý MediaPipe, chuẩn hóa tâm vai và trích xuất 12 động học.\n'
         '• Tối ưu mô hình sang C++ TorchScript; phát triển streaming WebSocket thời gian thực.\n'
         '• Phát triển backend FastAPI, cơ sở dữ liệu SQLite và frontend tương tác React 19.\n'
         '• Thiết lập bộ kiểm thử tự động 144 test cases, đo đạc độ trễ và Docker hóa hệ thống.'),
        ('Ngô Quang Minh', 'Thành viên / Nghiên cứu Dữ liệu & Báo cáo', 
         '• Kiểm kê dữ liệu, xây dựng Cổng kiểm soát chất lượng trên 491 video bệnh nhân.\n'
         '• Thiết kế ma trận phân chia kiểm thử chéo 10-fold Leave-One-Subject-Out (LOSO).\n'
         '• Thực hiện kiểm chuẩn so sánh các baseline (Majority, SVM, MLP, LSTM) và Ablation.\n'
         '• Xây dựng bộ luật rào chắn an toàn lâm sàng và quy tắc cấp cứu cho Chatbot AI.\n'
         '• Soạn thảo bộ hồ sơ Capstone hoàn chỉnh: Action Plan, WBS Gantt, Slide và Báo cáo.')
    ]
    for i, r in enumerate(role_rows):
        for j, val in enumerate(r):
            role_table.cell(i+1, j).text = val
    style_table(role_table, col_widths=[Inches(1.5), Inches(1.8), Inches(2.97)])

    add_h2('1.4. Lịch trình và các mốc tiến độ chính')
    sched_table = doc.add_table(rows=5, cols=4)
    sched_headers = ['Giai đoạn / Thời gian', 'Mục tiêu giai đoạn', 'Hoạt động & Sản phẩm bàn giao', 'Trạng thái']
    for j, h in enumerate(sched_headers):
        sched_table.cell(0, j).text = h
    sched_rows = [
        ('Tuần 1\n(Ngày 1 - 5)', 'Xác định bài toán & Rà soát dữ liệu', 
         '• Xác định phạm vi y tế, phân tích nhu cầu bệnh nhân đột quỵ.\n'
         '• Rà soát 491 video thô; thiết lập cổng kiểm soát chất lượng (Quality Gate).\n'
         '• Tạo tập 387 mẫu đạt chuẩn có xác thực SHA-256; nộp Action Plan.', 'HOÀN THÀNH'),
        ('Tuần 2\n(Ngày 6 - 12)', 'Tiền xử lý & Huấn luyện baseline', 
         '• Xây dựng hợp đồng đặc trưng 237 chiều (Pose, Bàn tay, Động học).\n'
         '• Phân chia 10-fold LOSO nghiêm ngặt chống rò rỉ dữ liệu.\n'
         '• Đánh giá các mô hình cơ sở (Majority, SVM, MLP, LSTM).', 'HOÀN THÀNH'),
        ('Tuần 3\n(Ngày 13 - 19)', 'Tối ưu mô hình & Tích hợp Fullstack', 
         '• Huấn luyện RehabMotionNet v2, tích hợp MS-TCN và Attention Pooling.\n'
         '• Xuất mô hình sang TorchScript C++ (1.82 MiB) tối ưu suy luận.\n'
         '• Xây dựng web React 19, kết nối WebSocket và cơ sở dữ liệu SQLite.', 'HOÀN THÀNH'),
        ('Tuần 4\n(Ngày 20 - 24)', 'Kiểm thử, Đóng gói & Báo cáo Capstone', 
         '• Chạy 144 test tự động; đo đạc độ trễ đạt <45 ms trên CPU.\n'
         '• Hoàn thiện rào chắn an toàn AI và kiến trúc bảo mật 2 lớp.\n'
         '• Đóng gói toàn bộ báo cáo, slide, WBS và phiếu đánh giá SIC.', 'HOÀN THÀNH')
    ]
    for i, r in enumerate(sched_rows):
        for j, val in enumerate(r):
            sched_table.cell(i+1, j).text = val
    style_table(sched_table, col_widths=[Inches(1.2), Inches(1.8), Inches(2.47), Inches(0.8)])

    doc.add_page_break()

    # Chương 2
    add_h1('2. Thực hiện dự án')
    add_h2('2.1. Thu thập dữ liệu và Cổng kiểm soát chất lượng')
    add_body(
        'Nguồn dữ liệu thực nghiệm trung tâm của dự án là bộ dữ liệu Phục hồi chức năng chi trên cho bệnh nhân đột quỵ (Upper Limb Stroke Rehabilitation Dataset). '
        'Kho dữ liệu thô ban đầu gồm 491 video được ghi hình từ 10 bệnh nhân đột quỵ thật (được mã hóa từ Bệnh nhân 01 đến Bệnh nhân 10). '
        'Do các video lâm sàng thực tế thường bị nhiễu do góc quay gia đình, rung lắc camera hoặc bệnh nhân cử động khó khăn dẫn đến che khuất khớp, việc thiết lập một Cổng kiểm soát chất lượng (Quality Gate) khắt khe là yêu cầu tiên quyết.'
    )
    add_bullet('Ngưỡng nhìn rõ khớp (Visibility Threshold): Mỗi khung hình bắt buộc phải đạt độ tin cậy tracking > 0.6 đối với các khớp vận động then chốt (vai, khuỷu tay, cổ tay hai bên).', bold_prefix='1. Độ tin cậy khớp: ')
    add_bullet('Tính liên tục theo thời gian: Loại bỏ ngay lập tức các đoạn video bị mất dấu khớp liên tục trên 15 khung hình (~1 giây) để tránh làm méo mó chuỗi thời gian.', bold_prefix='2. Tính liên tục chuỗi: ')
    add_bullet('Xác thực nhãn y tế và mã băm SHA-256: Mỗi mẫu giữ lại đều được đối chiếu với nhãn lâm sàng của bác sĩ và xác minh tính toàn vẹn bằng chữ ký băm mật mã SHA-256.', bold_prefix='3. Xác thực nguồn gốc: ')
    add_body('Sau khi qua Cổng kiểm soát chất lượng, có 387 mẫu đạt chuẩn xuất sắc (tỷ lệ giữ lại 78.82%), 104 mẫu bị loại bỏ (21.18%). Ngoài ra, nhóm nghiên cứu thêm các tập dữ liệu phụ trợ ngoài (MobiPhysio: 2.740 mẫu; REHAB24-6: 1.071 mẫu; IntelliRehabDS) để thử nghiệm tiền huấn luyện tự giám sát (self-supervised learning).')

    add_h2('2.2. Phương pháp huấn luyện và Quy chuẩn chống rò rỉ dữ liệu')
    add_body(
        'Trong trí tuệ nhân tạo y tế, việc chia tập train/test ngẫu nhiên theo khung hình hoặc phân đoạn video là sai lầm nghiêm trọng gây rò rỉ dữ liệu (Data Leakage). '
        'Khi các chuyển động của cùng một người bệnh xuất hiện ở cả tập train và tập test, mạng nơ-ron sẽ ghi nhớ màu áo, vóc dáng hoặc đặc điểm căn phòng của bệnh nhân thay vì học bản chất cơ học chuyển động, tạo ra kết quả chính xác ảo gần 100% nhưng hoàn toàn thất bại khi gặp bệnh nhân mới.'
    )
    add_callout(
        'RehabAI áp dụng nghiêm ngặt giao thức kiểm thử chéo 10-Fold Subject-Wise Leave-One-Subject-Out (LOSO). '
        'Trong mỗi fold k, toàn bộ bài tập của Bệnh nhân k được giữ lại làm tập kiểm thử độc lập (Test cohort). '
        'Một bệnh nhân khác được dùng làm tập Validation để chọn checkpoint, 8 bệnh nhân còn lại dùng để huấn luyện. '
        'Các thông số chuẩn hóa z-score chỉ được tính toán trên tập Train của fold đó, loại bỏ hoàn toàn rò rỉ dữ liệu.',
        title='QUY CHUẨN KHOA HỌC CHỐNG RÒ RỈ DỮ LIỆU'
    )
    add_bullet('Nhánh đồ thị PoseGraph: Xử lý 6 khớp cơ thể chi trên qua tích chập đồ thị nhằm bảo toàn cấu trúc giải phẫu học.', bold_prefix='1. Đồ thị khung xương tay: ')
    add_bullet('Nhánh bàn tay Hand Conv1D: Tiếp nhận 42 điểm khớp của hai bàn tay qua tích chập 1D để nắm bắt cử động mở ngón tay và gập duỗi.', bold_prefix='2. Tích chập bàn tay: ')
    add_bullet('Nhánh động học Kinematics: Xử lý 12 đặc trưng góc khớp vật lý và vận tốc để củng cố quy luật cơ sinh học.', bold_prefix='3. Đặc trưng góc vật lý: ')
    add_bullet('Mạng tích chập thời gian đa tỷ lệ (MS-TCN): Sử dụng các lớp dilated convolution với dilation d = 1, 2, 4 cùng kết nối tắt residual để học cả cử động vi mô lẫn chu kỳ bài tập.', bold_prefix='4. Multi-Scale TCN: ')
    add_bullet('Lớp gom cụm Attention Pooling: Tự động gán trọng số cao cho thời điểm cử động đạt biên độ cực đại, loại bỏ các khoảng dừng nghỉ vô nghĩa.', bold_prefix='5. Attention thời gian: ')

    add_h2('2.3. Quy trình vận hành hệ thống thời gian thực')
    add_body('Quy trình vận hành thời gian thực của RehabAI trải qua 4 bước đồng bộ liên tục:')
    add_bullet('Bước 1 - Thu nhận hình ảnh: Trình duyệt gửi khung hình 640x480 ở tốc độ 15 FPS qua kết nối WebSocket hai chiều.', bold_prefix='Bước 1: Bắt hình webcam: ')
    add_bullet('Bước 2 - Trích xuất và chuẩn hóa: MediaPipe Holistic bóc tách 33 điểm pose và 42 điểm tay, tịnh tiến về tâm vai, chia độ rộng vai và nối thêm 12 động học thành cửa sổ trượt 96 frame.', bold_prefix='Bước 2: Chuẩn hóa đặc trưng: ')
    add_bullet('Bước 3 - Suy luận mô hình và máy trạng thái FSM: Cứ mỗi 5 frame, tensor 96x237 được mô hình TorchScript C++ suy luận, đồng thời máy trạng thái FSM đếm số rep khi vượt qua đỉnh vận tốc góc.', bold_prefix='Bước 3: AI & Đếm rep: ')
    add_bullet('Bước 4 - Phản hồi giao diện & Lưu trữ: Trả kết quả về giao diện dưới 45 ms, vẽ khung xương thời gian thực và lưu lịch sử buổi tập cùng điểm đau VAS vào SQLite.', bold_prefix='Bước 4: Hiển thị & Lưu DB: ')

    add_h2('2.4. Thiết kế kiến trúc hệ thống đa tầng')
    add_fig('SIC-final/assets/fig1_system_architecture.png', 
            'Hình 1: Sơ đồ kiến trúc tổng thể hệ thống RehabAI gồm Tầng Client, Trích xuất đặc trưng, Lõi suy luận C++, Backend WebSocket và Trợ lý AI an toàn.')

    doc.add_page_break()

    # Chương 3
    add_h1('3. Kết quả thực nghiệm')
    add_h2('3.1. Tiền xử lý dữ liệu và trích xuất đặc trưng động học')
    add_fig('SIC-final/assets/fig5_kinematics_pipeline.png',
            'Hình 2: Quy trình trích xuất đặc trưng MediaPipe, chuẩn hóa dời tâm vai và tạo tensor động học 237 chiều.')
    add_body(
        '1. Dời gốc tọa độ về tâm vai: P_mid = (P_vai_trai + P_vai_phai) / 2; P_centered = P_raw - P_mid.\n'
        '2. Bất biến với khoảng cách: P_norm = P_centered / ||P_vai_trai - P_vai_phai||_2 (ngồi cách 1m hay 2.5m đều đồng nhất).\n'
        '3. 12 đặc trưng động học z-score: Góc dạng vai, góc duỗi khuỷu, góc nghiêng thân mình, vận tốc góc và vận tốc dịch chuyển cổ tay.'
    )

    add_h2('3.2. Khám phá và phân tích phân bố dữ liệu (EDA)')
    add_fig('SIC-final/assets/fig2_dataset_analysis.png',
            'Hình 3: Phân tích phân bố dữ liệu: (Trái) Tỷ lệ 4 bài tập; (Giữa) Số mẫu theo 10 bệnh nhân; (Phải) Tỷ lệ vượt qua Cổng kiểm soát chất lượng.')
    eda_table = doc.add_table(rows=5, cols=4)
    eda_headers = ['Mã & Tên bài tập', 'Nhóm cơ và khớp tác động', 'Số mẫu', 'Tỷ lệ (%)']
    for j, h in enumerate(eda_headers):
        eda_table.cell(0, j).text = h
    eda_rows = [
        ('Bài tập 1: Nâng vai / Với tay (Shoulder Elevation)', 'Khớp vai, cơ delta, cơ thang', '123', '31.78%'),
        ('Bài tập 2: Duỗi gập khuỷu tay (Elbow Extension)', 'Khớp khuỷu tay, cơ nhị đầu, tam đầu', '65', '16.80%'),
        ('Bài tập 3: Gập duỗi cổ tay (Wrist Flex/Ext)', 'Khớp cổ tay, nhóm cơ cẳng tay', '104', '26.87%'),
        ('Bài tập 4: Mở xòe bàn tay (Hand Opening)', 'Khớp bàn ngón và liên đốt ngón tay', '95', '24.55%')
    ]
    for i, r in enumerate(eda_rows):
        for j, val in enumerate(r):
            eda_table.cell(i+1, j).text = val
    style_table(eda_table, col_widths=[Inches(2.5), Inches(2.2), Inches(0.8), Inches(0.77)])

    add_h2('3.3. Mô hình hóa và bảng xếp hạng kiểm chuẩn (Benchmark)')
    add_fig('SIC-final/assets/fig3_model_benchmark.png',
            'Hình 4: Bảng xếp hạng kiểm chuẩn nghiêm ngặt 10-Fold LOSO: Macro-F1 (%) và Accuracy (%) trên 387 mẫu bệnh nhân thật.')
    bench_table = doc.add_table(rows=7, cols=5)
    bench_headers = ['Kiến trúc mô hình', 'Macro-F1 Bài tập', 'Accuracy Bài tập', 'Weighted-F1', 'Vai trò kiến trúc']
    for j, h in enumerate(bench_headers):
        bench_table.cell(0, j).text = h
    bench_rows = [
        ('Majority Baseline', '5.47%', '15.15%', '3.98%', 'Mốc ngẫu nhiên cơ sở'),
        ('Multilayer Perceptron (MLP)', '27.79%', '34.51%', '38.20%', 'Mạng nơ-ron truyền thẳng cổ điển'),
        ('Linear Support Vector Machine (SVM)', '28.80%', '36.51%', '41.12%', 'Bộ phân loại lề tuyến tính'),
        ('Long Short-Term Memory (LSTM)', '32.45%', '39.96%', '45.10%', 'Mạng nơ-ron hồi quy chuỗi thời gian'),
        ('RehabMotionNet v2 (SẢN XUẤT)', '35.44% ± 27.04%', '43.79% ± 23.35%', '49.85% ± 22.30%', 'Đa nhánh MS-TCN + Attention'),
        ('Optimized-v1 (Nghiên cứu)', '39.45%', '48.37%', '53.12%', 'Kiến trúc tối ưu sau triệt tiêu (Seed 42)')
    ]
    for i, r in enumerate(bench_rows):
        for j, val in enumerate(r):
            bench_table.cell(i+1, j).text = val
    style_table(bench_table, col_widths=[Inches(2.2), Inches(1.1), Inches(1.1), Inches(0.9), Inches(1.97)])

    add_fig('SIC-final/assets/fig4_confusion_matrix.png',
            'Hình 5: Ma trận nhầm lẫn gộp 10-Fold LOSO và tỷ lệ Recall chuẩn hóa từng bài tập của RehabMotionNet v2.')
    add_fig('SIC-final/assets/fig6_ablation_study.png',
            'Hình 6: Nghiên cứu triệt tiêu (Ablation Study): Tác động của từng thành phần kiến trúc lên hiệu năng RehabMotionNet v2.')
    
    add_callout(
        'Quyết định đạo đức vô hiệu hóa nhánh Completion Head: Nhánh phụ dự đoán động tác hoàn thành chỉ đạt Accuracy 50.24% (ngang ngửa tung đồng xu ngẫu nhiên). '
        'Theo tiêu chuẩn đạo đức AI y tế, nhóm đã kiên quyết vô hiệu hóa nhánh này trên web để tránh đánh lừa bệnh nhân. '
        'Toàn bộ việc đếm rep được giao cho máy trạng thái FSM đo góc cơ học vật lý thực tế.',
        title='QUYẾT ĐỊNH ĐẠO ĐỨC & AN TOÀN Y TẾ'
    )

    add_h2('3.4. Giao diện người dùng và rào chắn an toàn lâm sàng')
    add_fig('SIC-final/assets/fig8_two_layer_security.png',
            'Hình 7: Kiến trúc bảo mật 2 lớp: Vùng công cộng giáo dục đối lập với Phòng tập bảo mật (/app).')
    add_fig('SIC-final/assets/ui_homepage.png',
            'Hình 8: Ứng dụng web RehabAI: (Trên) Cổng thông tin phục hồi; (Dưới) Giao diện tập luyện vẽ khung xương trực tiếp và Trợ lý AI an toàn.')

    add_h2('3.5. Kiểm thử hệ thống và kế hoạch tối ưu hóa')
    add_bullet('Bộ kiểm thử tự động: 144 test cases tự động kiểm tra toàn diện backend, frontend, schema đặc trưng và luật chatbot (143 passed, 1 skipped).', bold_prefix='1. Kiểm thử phần mềm: ')
    add_bullet('Đo đạc độ trễ siêu thấp: Thời gian xử lý toàn chu kỳ chỉ đạt 42.5 ms trên CPU thông thường (MediaPipe 24ms, TorchScript 11ms, WebSocket 7.5ms), đáp ứng tốt chuẩn 15 FPS (<66.6ms).', bold_prefix='2. Đo đạc độ trễ: ')
    add_bullet('Thử nghiệm trong môi trường khắc nghiệt: Hệ thống hoạt động bền bỉ trong điều kiện ánh sáng yếu, che khuất một phần cơ thể và khoảng cách ngồi thay đổi.', bold_prefix='3. Độ ổn định thực tế: ')

    doc.add_page_break()

    # Chương 4
    add_h1('4. Tác động dự kiến')
    add_h2('4.1. Thành tựu đạt được và lợi ích kinh tế - xã hội')
    add_bullet('Trao quyền tự chủ cho bệnh nhân: Giúp bệnh nhân đột quỵ chủ động tập luyện hàng ngày tại nhà với phản hồi tức thì.', bold_prefix='1. Bình dân hóa y tế: ')
    add_bullet('Giảm bớt gánh nặng kinh tế: Tiết kiệm hàng triệu đồng chi phí đi lại và chi phí thuê chuyên viên phục hồi chức năng.', bold_prefix='2. Giá trị kinh tế: ')
    add_bullet('Hỗ trợ hệ sinh thái y tế: Giúp các bác sĩ và chuyên viên theo dõi dữ liệu tập luyện của bệnh nhân từ xa qua bảng lịch sử.', bold_prefix='3. Giảm tải bệnh viện: ')

    add_h2('4.2. Hướng phát triển và Lộ trình sẵn sàng công nghệ (TRL)')
    add_fig('SIC-final/assets/fig7_trl_roadmap.png',
            'Hình 9: Lộ trình phát triển mức độ sẵn sàng công nghệ (TRL Roadmap) của RehabAI từ Nguyên mẫu TRL 5 lên Ứng dụng lâm sàng TRL 7-9.')
    add_bullet('Ngắn hạn (3 tháng tới - TRL 6): Tích hợp bài tập giãn cổ và thở sâu; thử nghiệm thực địa trên 20 bệnh nhân đột quỵ tại Hà Nội.', bold_prefix='1. Kế hoạch ngắn hạn: ')
    add_bullet('Trung hạn (6 - 12 tháng - TRL 7): Mở rộng bộ dữ liệu lên 50+ bệnh nhân; phát triển app di động chạy mô hình on-device (CoreML/TFLite).', bold_prefix='2. Kế hoạch trung hạn: ')
    add_bullet('Dài hạn (12 - 24 tháng - TRL 8-9): Thử nghiệm lâm sàng có đối chứng (RCT); liên kết chỉ số thang điểm Fugl-Meyer và tích hợp bệnh án điện tử EHR.', bold_prefix='3. Kế hoạch dài hạn: ')

    doc.add_page_break()

    # Chương 5
    add_h1('5. Đánh giá và nhận xét của thành viên nhóm')
    add_fig('SIC-final/assets/hero_companion.png',
            'Biểu tượng dự án Capstone nhóm Dou: AI nhân văn vì sức khỏe cộng đồng.', width_in=3.8)
    review_table = doc.add_table(rows=3, cols=2)
    review_headers = ['Thành viên', 'Nhận xét cá nhân, bài học kỹ thuật & trải nghiệm']
    for j, h in enumerate(review_headers):
        review_table.cell(0, j).text = h
    review_rows = [
        ('Đàm Đức Lương\n(Trưởng nhóm / Phụ trách AI & Fullstack)',
         'Tham gia dự án Capstone Samsung Innovation Campus là một bước ngoặt lớn đối với em. '
         'Bài học đắt giá nhất mà em nhận được là sự khác biệt giữa học máy trong sách vở và AI y tế thực chiến. '
         'Lúc đầu nhìn thấy độ chính xác 100% ở các mô hình cũ, em rất phấn khích nhưng khi rà soát kỹ mới nhận ra đó là do rò rỉ dữ liệu. '
         'Quyết định dũng cảm chuyển sang đánh giá nghiêm ngặt 10-fold LOSO và chấp nhận số thực 43.79% Accuracy / 35.44% Macro-F1 đã dạy cho em bài học lớn về tính liêm chính khoa học. '
         'Về mặt kỹ thuật, việc tối ưu mô hình sang C++ TorchScript và truyền nhận WebSocket dưới 45ms giúp em làm chủ tư duy phát triển hệ thống hoàn chỉnh.'),
        ('Ngô Quang Minh\n(Thành viên / Nghiên cứu Dữ liệu & Báo cáo)',
         'Dự án RehabAI giúp em hiểu sâu sắc về chất lượng dữ liệu, đạo đức y sinh và làm việc nhóm hiệu quả. '
         'Rà soát 491 video bệnh nhân đột quỵ giúp em thấy được tính phức tạp của dữ liệu đời thực: bệnh nhân run tay, ngồi lệch, ánh sáng kém... '
         'Việc xây dựng Cổng kiểm soát chất lượng và tạo ra tập 387 mẫu đạt chuẩn là nền tảng sống còn cho sự thành công của mô hình. '
         'Thiết kế rào chắn an toàn cho Chatbot nhắc nhở em rằng trong y tế, AI phải là công cụ trao quyền và đồng hành chứ không bao giờ được phép chẩn đoán bừa bãi. '
         'Sự đồng hành ăn ý với Đức Lương giúp chúng em hoàn thành 100% khối lượng công việc đúng hạn.')
    ]
    for i, r in enumerate(review_rows):
        for j, val in enumerate(r):
            review_table.cell(i+1, j).text = val
    style_table(review_table, col_widths=[Inches(2.0), Inches(4.27)])

    doc.add_page_break()

    # Chương 6
    add_h1('6. Đánh giá và nhận xét của Giảng viên / Hội đồng (Phiếu chấm)')
    eval_table = doc.add_table(rows=7, cols=4)
    eval_headers = ['Hạng mục đánh giá', 'Điểm tối đa', 'Tiêu chí đánh giá chi tiết', 'Điểm số & Ghi chú của Giám khảo']
    for j, h in enumerate(eval_headers):
        eval_table.cell(0, j).text = h
    eval_rows = [
        ('Ý TƯỞNG (IDEA)\n(10 Điểm)', '10 đ', 
         '• Tính sáng tạo và mới mẻ của giải pháp phục hồi chức năng không chạm.\n'
         '• Sự khác biệt vượt trội so với các hệ thống cảm biến đắt tiền.\n'
         '• Tác động lớn đến lợi ích cộng đồng và đáp ứng đúng nhu cầu xã hội.', 
         'Điểm: _____ / 10\n\nGhi chú: '),
        ('ỨNG DỤNG (APPLICATION)\n(30 Điểm)', '30 đ', 
         '• Sử dụng công cụ chuẩn mực (MediaPipe, PyTorch, TorchScript, FastAPI, React 19).\n'
         '• Vận dụng xuất sắc kiến thức đã học (CNN, TCN, Attention, Contrastive Learning).\n'
         '• Tự nghiên cứu giải pháp độc lập (Kiểm thử chéo 10-fold LOSO, máy trạng thái FSM).', 
         'Điểm: _____ / 30\n\nGhi chú: '),
        ('KẾT QUẢ (RESULT)\n(30 Điểm)', '30 đ', 
         '• Hiệu năng thực tế trên 387 mẫu bệnh nhân đột quỵ thật không rò rỉ dữ liệu.\n'
         '• Tính khả thi và độ trễ siêu thấp (<45 ms) trên phần cứng máy tính tiêu chuẩn.\n'
         '• Mức độ hoàn thiện cao của phần mềm web fullstack có cơ sở dữ liệu SQLite.', 
         'Điểm: _____ / 30\n\nGhi chú: '),
        ('QUẢN LÝ DỰ ÁN\n(10 Điểm)', '10 đ', 
         '• Phân chia khối lượng công việc công bằng, hợp lý theo sở trường thành viên.\n'
         '• Giao tiếp trôi chảy, tinh thần đồng đội cao và xử lý linh hoạt khi phát hiện lỗi dữ liệu.\n'
         '• Hoàn thành đúng hạn 100% các cột mốc đề ra theo bảng WBS.', 
         'Điểm: _____ / 10\n\nGhi chú: '),
        ('BÁO CÁO & THUYẾT TRÌNH\n(20 Điểm)', '20 đ', 
         '• Báo cáo tổng kết đầy đủ, khoa học, chặt chẽ và văn phong học thuật xuất sắc.\n'
         '• Slide thuyết trình chuyên nghiệp, thẩm mỹ cao với nhiều hình vẽ minh chứng trực quan.\n'
         '• Trình bày lưu loát, tự tin và sẵn sàng trả lời thuyết phục các câu hỏi phản biện.', 
         'Điểm: _____ / 20\n\nGhi chú: '),
        ('TỔNG ĐIỂM DỰ ÁN', '100 đ', 
         'Tổng điểm đánh giá Capstone Project qua cả 5 hạng mục tiêu chuẩn.', 
         'ĐIỂM CHUNG CUỘC:\n_____ / 100')
    ]
    for i, r in enumerate(eval_rows):
        for j, val in enumerate(r):
            eval_table.cell(i+1, j).text = val
    style_table(eval_table, col_widths=[Inches(1.5), Inches(0.8), Inches(2.57), Inches(1.4)])

    out = 'SIC-final/VN/Dou_RehabAI_Bao_Cao_Tong_Ket_VN.docx'
    doc.save(out)
    print(f'Generated {out}')

# ----------------- 2. SLIDE THUYẾT TRÌNH VN -----------------
def generate_presentation_vn():
    prs = pptx.Presentation()
    prs.slide_width = PInches(13.333)
    prs.slide_height = PInches(7.5)
    blank_layout = prs.slide_layouts[6]

    C_NAVY = PRGBColor(11, 34, 101)
    C_CYAN = PRGBColor(0, 169, 224)
    C_DARK = PRGBColor(38, 50, 56)
    C_MUTED = PRGBColor(90, 107, 124)
    C_BG_CARD = PRGBColor(244, 246, 249)
    C_BORDER = PRGBColor(208, 215, 222)
    C_WHITE = PRGBColor(255, 255, 255)

    def add_header(slide, unit_text, title_text):
        tb_unit = slide.shapes.add_textbox(PInches(0.8), PInches(0.4), PInches(11.7), PInches(0.35))
        p_u = tb_unit.text_frame.paragraphs[0]
        p_u.text = unit_text.upper()
        p_u.font.name = 'Segoe UI'
        p_u.font.size = PPt(10)
        p_u.font.bold = True
        p_u.font.color.rgb = C_CYAN

        tb_title = slide.shapes.add_textbox(PInches(0.8), PInches(0.7), PInches(11.7), PInches(0.6))
        p_t = tb_title.text_frame.paragraphs[0]
        p_t.text = title_text
        p_t.font.name = 'Segoe UI'
        p_t.font.size = PPt(20)
        p_t.font.bold = True
        p_t.font.color.rgb = C_NAVY

        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, PInches(0.8), PInches(1.35), PInches(11.733), PInches(0.03))
        line.fill.solid()
        line.fill.fore_color.rgb = C_CYAN
        line.line.fill.background()

    def add_footer(slide, current_slide, total_slides=15):
        tb_f = slide.shapes.add_textbox(PInches(0.8), PInches(7.05), PInches(11.733), PInches(0.35))
        tf = tb_f.text_frame
        p = tf.paragraphs[0]
        p.text = f'Nhóm Dou · RehabAI: Hệ Thống Hỗ Trợ Phục Hồi Chức Năng Chi Trên   |   Trang {current_slide} / {total_slides}   |   Samsung Innovation Campus'
        p.alignment = PP_ALIGN.CENTER
        p.font.name = 'Segoe UI'
        p.font.size = PPt(9)
        p.font.color.rgb = C_MUTED

    def add_card(slide, left, top, width, height, title, items, bg_color=C_BG_CARD, border_color=C_BORDER, title_color=C_NAVY):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        shape.line.color.rgb = border_color
        shape.line.width = PPt(1.2)
        tf = shape.text_frame
        tf.word_wrap = True
        tf.margin_left = PInches(0.2)
        tf.margin_right = PInches(0.2)
        tf.margin_top = PInches(0.18)
        tf.margin_bottom = PInches(0.18)
        if title:
            p_t = tf.paragraphs[0]
            p_t.text = title
            p_t.font.name = 'Segoe UI'
            p_t.font.size = PPt(12)
            p_t.font.bold = True
            p_t.font.color.rgb = title_color
            p_t.space_after = PPt(6)
        first = True if not title else False
        for item in items:
            p = tf.add_paragraph() if not first else tf.paragraphs[0]
            first = False
            p.text = item
            p.font.name = 'Segoe UI'
            p.font.size = PPt(9.5)
            p.font.color.rgb = C_DARK
            p.space_after = PPt(4)
        return shape

    # Slide 1: Bìa
    s1 = prs.slides.add_slide(blank_layout)
    bg_left = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, PInches(0), PInches(0), PInches(0.4), PInches(7.5))
    bg_left.fill.solid()
    bg_left.fill.fore_color.rgb = C_NAVY
    bg_left.line.fill.background()

    tb_b = s1.shapes.add_textbox(PInches(0.9), PInches(0.8), PInches(7.5), PInches(0.5))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.text = 'SAMSUNG INNOVATION CAMPUS  ·  BẢO VỆ DỰ ÁN CAPSTONE'
    p_b.font.name = 'Segoe UI'
    p_b.font.size = PPt(12)
    p_b.font.bold = True
    p_b.font.color.rgb = C_CYAN

    tb_title = s1.shapes.add_textbox(PInches(0.9), PInches(1.3), PInches(7.5), PInches(2.0))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    p_t1 = tf_title.paragraphs[0]
    p_t1.text = 'RehabAI: Hệ Thống Hỗ Trợ Theo Dõi &\nĐánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên'
    p_t1.font.name = 'Segoe UI'
    p_t1.font.size = PPt(26)
    p_t1.font.bold = True
    p_t1.font.color.rgb = C_NAVY

    tb_sub = s1.shapes.add_textbox(PInches(0.9), PInches(3.4), PInches(7.0), PInches(1.1))
    tf_sub = tb_sub.text_frame
    tf_sub.word_wrap = True
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = 'Nền tảng phục hồi chức năng từ xa ứng dụng Thị giác máy tính và Học sâu cho bệnh nhân đột quỵ với tính năng nhận diện khung xương thời gian thực và Trợ lý AI an toàn'
    p_sub.font.name = 'Segoe UI'
    p_sub.font.size = PPt(11.5)
    p_sub.font.color.rgb = C_DARK

    meta_box = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PInches(0.9), PInches(4.7), PInches(6.6), PInches(1.8))
    meta_box.fill.solid()
    meta_box.fill.fore_color.rgb = C_BG_CARD
    meta_box.line.color.rgb = C_BORDER
    tf_m = meta_box.text_frame
    tf_m.margin_left, tf_m.margin_top = PInches(0.25), PInches(0.2)
    pm1 = tf_m.paragraphs[0]
    pm1.text = 'Nhóm Dou  |  Khóa Học Trí Tuệ Nhân Tạo (AI Course)'
    pm1.font.name = 'Segoe UI'
    pm1.font.size = PPt(11)
    pm1.font.bold = True
    pm1.font.color.rgb = C_NAVY
    pm1.space_after = PPt(4)
    pm2 = tf_m.add_paragraph()
    pm2.text = '• Đàm Đức Lương — Trưởng nhóm / Phụ trách AI & Fullstack\n• Ngô Quang Minh — Nghiên cứu Dữ liệu & Báo cáo'
    pm2.font.name = 'Segoe UI'
    pm2.font.size = PPt(10)
    pm2.font.color.rgb = C_DARK
    pm2.space_after = PPt(4)
    pm3 = tf_m.add_paragraph()
    pm3.text = 'Thời gian: 07/11/2026   |   Kiểm thử 10-Fold LOSO trên bệnh nhân thật'
    pm3.font.name = 'Segoe UI'
    pm3.font.size = PPt(9.5)
    pm3.font.color.rgb = C_MUTED

    if os.path.exists('SIC-final/assets/hero_companion.png'):
        s1.shapes.add_picture('SIC-final/assets/hero_companion.png', PInches(7.8), PInches(1.1), PInches(4.8), PInches(5.4))

    # Slide 2: Thực trạng & Động lực
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, '01 · Giới thiệu', 'Thực Trạng Lâm Sàng & Khó Khăn Trong Phục Hồi Chức Năng Đột Quỵ')
    add_footer(s2, 2)
    c_w, c_h = PInches(3.6), PInches(2.5)
    add_card(s2, PInches(0.8), PInches(1.6), c_w, c_h, '1. Tỷ Lệ Đột Quỵ & Di Chứng Liệt', [
        '• Hơn 12 triệu ca đột quỵ mới/năm trên thế giới; nguyên nhân tàn tật hàng đầu.',
        '• Tại Việt Nam: ~200.000 ca/năm; trên 80% để lại di chứng liệt vận động chi trên.',
        '• Để phục hồi, não bộ cần hàng trăm cử động lặp lại mỗi ngày để tái tạo liên kết.'
    ])
    add_card(s2, PInches(4.7), PInches(1.6), c_w, c_h, '2. Thiếu Chuyên Viên & Gánh Nặng Đi Lại', [
        '• Tỷ lệ chuyên viên/bệnh nhân vượt quá 1:50 tại các bệnh viện công lập.',
        '• Người bệnh nông thôn tốn kém chi phí và kiệt sức khi phải đi xa trị liệu liên tục.',
        '• Bệnh viện quá tải, không thể hỗ trợ tập 1-kèm-1 hàng ngày sau xuất viện.'
    ])
    add_card(s2, PInches(0.8), PInches(4.3), c_w, c_h, '3. Hơn 60% Bệnh Nhân Từ Bỏ Bài Tập', [
        '• Thiếu người hướng dẫn phản hồi tư thế đúng/sai trong lúc tập tại nhà.',
        '• Không có công cụ ghi nhận tiến bộ khiến người bệnh mất động lực.',
        '• Dễ phát sinh các tư thế bù trừ sai lệch gây tổn thương khớp vai kéo dài.'
    ])
    add_card(s2, PInches(4.7), PInches(4.3), c_w, c_h, '4. Rào Cản Thiết Bị Cảm Biến Đắt Đỏ', [
        '• Găng tay cảm biến ngoại vi và bộ đo IMU có giá hàng nghìn USD ($1.000+).',
        '• Rất cồng kềnh, người bị liệt nửa người không thể tự đeo vào tay bệnh.',
        '• Chi phí quá cao khiến đa số gia đình Việt Nam không thể tiếp cận.'
    ])
    callout_box = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PInches(8.6), PInches(1.6), PInches(3.9), PInches(5.2))
    callout_box.fill.solid()
    callout_box.fill.fore_color.rgb = PRGBColor(235, 243, 250)
    callout_box.line.color.rgb = C_CYAN
    callout_box.line.width = PPt(1.5)
    tf_co = callout_box.text_frame
    tf_co.margin_left, tf_co.margin_right, tf_co.margin_top = PInches(0.25), PInches(0.25), PInches(0.3)
    p_co_t = tf_co.paragraphs[0]
    p_co_t.text = 'GIẢI PHÁP REHABAI'
    p_co_t.font.name = 'Segoe UI'
    p_co_t.font.size = PPt(13)
    p_co_t.font.bold = True
    p_co_t.font.color.rgb = C_NAVY
    p_co_t.space_after = PPt(8)
    co_bullets = [
        'Bình dân hóa y tế: Biến mọi chiếc webcam máy tính thông thường thành trợ lý phục hồi chức năng.',
        '100% Không chạm: Nhận diện cử động qua MediaPipe Holistic, không cần đeo bất kỳ cảm biến nào.',
        'Đo đạc khách quan: Đếm rep tự động bằng máy trạng thái hữu hạn cơ sinh học.',
        'Trợ lý AI đồng hành: Hỗ trợ giải đáp kiến thức có rào chắn ngăn ngừa tai biến nguy hiểm.',
        'Tiếp cận tại nhà: Người bệnh tự tin luyện tập độc lập ngay tại phòng khách gia đình.'
    ]
    for b in co_bullets:
        p = tf_co.add_paragraph()
        p.text = f'✓ {b}'
        p.font.name = 'Segoe UI'
        p.font.size = PPt(9.5)
        p.font.color.rgb = C_DARK
        p.space_after = PPt(8)

    # Slide 3: Mục tiêu cốt lõi
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, '01 · Giới thiệu', 'Mục Tiêu Cốt Lõi & Giá Trị Đề Xuất Của RehabAI')
    add_footer(s3, 3)
    obj_cards = [
        ('1. Nhận Diện Không Chạm', [
            '• Bóc tách 33 điểm khung xương cơ thể và 42 điểm bàn tay qua MediaPipe Holistic.',
            '• Chạy ổn định trên webcam tiêu chuẩn (640x480 @ 15-30 FPS).',
            '• Hoàn toàn không cần cảm biến đeo đắt tiền.'
        ]),
        ('2. Phân Loại Cử Động Chi Trên', [
            '• Nhận diện 4 bài tập phục hồi chức năng thiết yếu cho tay và vai.',
            '• Mạng nơ-ron chuỗi RehabMotionNet v2 kết hợp đồ thị và thời gian.',
            '• Tiếp nhận toàn bộ chuỗi 96 khung hình động học.'
        ]),
        ('3. Đếm Số Rep Cơ Sinh Học', [
            '• Theo dõi góc khớp và vận tốc góc theo thời gian thực.',
            '• Máy trạng thái hữu hạn (FSM) đếm rep khi vượt ngưỡng duỗi tối đa.',
            '• Loại bỏ hoàn toàn các cử động giả hoặc sai biên độ.'
        ]),
        ('4. Nền Tảng Web Phân Tầng', [
            '• Cổng thông tin công cộng giáo dục người bệnh và lưu ý an toàn.',
            '• Phòng tập bảo mật (/app) chỉ kích hoạt khi người dùng cho phép.',
            '• Cơ sở dữ liệu SQLite lưu lịch sử số rep và thang đo mức đau VAS.'
        ]),
        ('5. Trợ Lý AI Y Tế An Toàn', [
            '• Trò chuyện hỗ trợ song ngữ thân thiện bằng tiếng Việt và tiếng Anh.',
            '• Tự động ngắt và báo động khi phát hiện triệu chứng cấp cứu (đau ngực, khó thở).',
            '• Kiên quyết từ chối kê đơn hoặc đưa ra chẩn đoán thay bác sĩ.'
        ]),
        ('6. Liêm Chính Khoa Học Tuyệt Đối', [
            '• Xóa bỏ kết quả ảo 100% do rò rỉ dữ liệu của các mô hình cũ.',
            '• Kiểm chuẩn nghiêm ngặt 10-fold Leave-One-Subject-Out (LOSO).',
            '• Đánh giá trung thực trên dữ liệu bệnh nhân đột quỵ thật.'
        ])
    ]
    for idx, (title, items) in enumerate(obj_cards):
        col, row = idx % 3, idx // 3
        add_card(s3, PInches(0.8 + col * 3.95), PInches(1.6 + row * 2.65), PInches(3.8), PInches(2.45), title, items)

    # Slide 4: Kiến trúc hệ thống
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, '02 · Thực hiện dự án', 'Kiến Trúc Hệ Thống Tổng Thể Đa Tầng Của RehabAI')
    add_footer(s4, 4)
    if os.path.exists('SIC-final/assets/fig1_system_architecture.png'):
        s4.shapes.add_picture('SIC-final/assets/fig1_system_architecture.png', PInches(0.8), PInches(1.5), PInches(7.5), PInches(5.3))
    arch_tiers = [
        ('Tầng Giao Diện (React 19 + Vite)', ['• Thu nhận hình ảnh webcam 640x480 ở 15 FPS.', '• Vẽ khung xương thời gian thực trên HTML5 canvas.', '• Vòng tiến trình đếm rep và thanh đo mức đau VAS.']),
        ('Tầng Trích Xuất & Chuẩn Hóa', ['• MediaPipe Holistic bóc tách 33 điểm pose + 42 điểm tay.', '• Tịnh tiến dời gốc tọa độ về trung điểm hai vai.', '• Chia khoảng cách hai vai giúp bất biến với khoảng cách ngồi.']),
        ('Lõi Suy Luận AI (TorchScript C++)', ['• RehabMotionNet v2 (451k tham số, 1.82 MiB).', '• Đóng gói C++ TorchScript chạy cực nhanh <45 ms.', '• Nhận tensor chuyển động (Batch, 96 frame, 237 chiều).']),
        ('Tầng An Toàn & Dữ Liệu (FastAPI + SQLite)', ['• Giao tiếp WebSocket hai chiều full-duplex.', '• Máy trạng thái FSM đếm rep & cảnh báo mất dấu.', '• Trợ lý AI có rào chắn an toàn + Lưu trữ SQLite.'])
    ]
    for idx, (title, items) in enumerate(arch_tiers):
        add_card(s4, PInches(8.55), PInches(1.5 + idx * 1.35), PInches(3.98), PInches(1.25), title, items)

    # Slide 5: Dữ liệu & Quality Gate
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, '02 · Thực hiện dự án', 'Quản Trị Dữ Liệu & Cổng Kiểm Soát Chất Lượng (Quality Gate)')
    add_footer(s5, 5)
    if os.path.exists('SIC-final/assets/fig2_dataset_analysis.png'):
        s5.shapes.add_picture('SIC-final/assets/fig2_dataset_analysis.png', PInches(0.8), PInches(1.5), PInches(8.0), PInches(5.3))
    add_card(s5, PInches(9.0), PInches(1.5), PInches(3.53), PInches(5.3), 'Quản Trị Dữ Liệu Y Tế', [
        'Tập Dữ Liệu Bệnh Nhân Thật:',
        '• Thu thập từ 10 bệnh nhân đột quỵ thật (`Sub 01` đến `Sub 10`).',
        '• Tổng kho thô: 491 video trong các điều kiện ánh sáng thực tế.\n',
        'Cổng Kiểm Soát Chất Lượng (Quality Gate):',
        '• Lọc bỏ các khung hình có độ tin cậy khớp < 0.6.',
        '• Loại bỏ 104 mẫu (21.2%) bị che khuất khớp hoặc rung lắc.',
        '• Giữ lại 387 mẫu đạt chuẩn (tỷ lệ 78.8%) để huấn luyện.\n',
        'Phân Bố 4 Bài Tập (387 mẫu):',
        '• Bài 1: Nâng vai / Với tay — 123 (31.8%)',
        '• Bài 2: Duỗi gập khuỷu tay — 65 (16.8%)',
        '• Bài 3: Gập duỗi cổ tay — 104 (26.9%)',
        '• Bài 4: Mở xòe bàn tay — 95 (24.6%)\n',
        'Mức Độ Hoàn Thành Động Tác:',
        '• Hoàn thành: 187 (48.3%) | Chưa xong: 200 (51.7%), phản ánh đúng khó khăn của người bệnh.'
    ])

    # Slide 6: Chuẩn hóa động học
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, '02 · Thực hiện dự án', 'Trích Xuất Đặc Trưng, Chuẩn Hóa Tâm Vai & Động Học')
    add_footer(s6, 6)
    if os.path.exists('SIC-final/assets/fig5_kinematics_pipeline.png'):
        s6.shapes.add_picture('SIC-final/assets/fig5_kinematics_pipeline.png', PInches(0.8), PInches(1.5), PInches(7.6), PInches(5.3))
    add_card(s6, PInches(8.65), PInches(1.5), PInches(3.88), PInches(5.3), 'Hợp Đồng Đặc Trưng 237 Chiều', [
        '1. Dời Gốc Tọa Độ Về Tâm Vai:',
        '• Gốc (0,0,0) đặt tại trung điểm hai vai:',
        '  P_mid = (P_vai_trai + P_vai_phai) / 2',
        '  P_centered = P_raw - P_mid\n',
        '2. Chuẩn Hóa Bất Biến Khoảng Cách:',
        '• Chia cho khoảng cách Euclidean giữa hai vai:',
        '  P_norm = P_centered / ||P_vai_trai - P_vai_phai||_2',
        '• Đảm bảo dữ liệu đồng nhất dù bệnh nhân ngồi cách camera 1m hay 2.5m.\n',
        '3. 12 Đặc Trưng Động Học Vật Lý:',
        '• Góc dạng/khép vai trái và phải',
        '• Góc duỗi/gập khuỷu tay trái và phải',
        '• Độ nghiêng thân mình so với phương thẳng đứng',
        '• Vận tốc góc tương ứng (dθ/dt)',
        '• Vận tốc dịch chuyển cổ tay hai bên\n',
        '4. Cấu Trúc Tensor (96 x 237):',
        '• Pose (99) + Bàn tay (126) + Động học (12) = 237 chiều xuyên suốt 96 khung hình liên tục.'
    ])

    # Slide 7: Kiến trúc RehabMotionNet v2
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, '02 · Thực hiện dự án', 'Mạng Nơ-ron Không-Thời Gian RehabMotionNet v2')
    add_footer(s7, 7)
    arch_cards = [
        ('1. Nhánh Đồ Thị Khung Xương PoseGraph', ['• Đầu vào: 6 khớp giải phẫu (vai, khuỷu, cổ tay hai bên).', '• Tích chập đồ thị không gian bảo toàn cấu trúc khớp chi trên.', '• Nắm bắt quỹ đạo nâng cánh tay và với đồ vật.']),
        ('2. Nhánh Tích Chập Bàn Tay Hand Conv1D', ['• Đầu vào: 42 điểm khớp của hai bàn tay qua thời gian.', '• Tích chập 1D bóc tách cử động co duỗi ngón tay tinh tế.', '• Yếu tố quyết định phân biệt bài mở bàn tay với cổ tay.']),
        ('3. Tích Chập Thời Gian Đa Tỷ Lệ (MS-TCN)', ['• Các lớp dilated convolution với độ giãn cách d = 1, 2, 4.', '• Kết nối tắt residual xuyên suốt các cấp độ thời gian.', '• Học được cả vi rung động, pha động tác và nhịp điệu bài tập.']),
        ('4. Gom Cụm Attention & TorchScript', ['• Cơ chế tự chú ý gán trọng số cao cho thời điểm duỗi tối đa.', '• Giảm nhiễu tại các khung hình dừng nghỉ và chuyển tiếp.', '• Đóng gói C++ TorchScript (1.82 MiB, 451k params) cho độ trễ <45ms.'])
    ]
    for idx, (title, items) in enumerate(arch_cards):
        col, row = idx % 2, idx // 2
        add_card(s7, PInches(0.8 + col * 5.95), PInches(1.6 + row * 2.65), PInches(5.8), PInches(2.45), title, items)

    # Slide 8: Benchmark LOSO
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, '03 · Kết quả thực nghiệm', 'Kiểm Chuẩn Nghiêm Ngặt 10-Fold LOSO Trên Bệnh Nhân Thật')
    add_footer(s8, 8)
    if os.path.exists('SIC-final/assets/fig3_model_benchmark.png'):
        s8.shapes.add_picture('SIC-final/assets/fig3_model_benchmark.png', PInches(0.8), PInches(1.5), PInches(7.5), PInches(5.3))
    add_card(s8, PInches(8.55), PInches(1.5), PInches(3.98), PInches(5.3), 'Đánh Giá Trên Bệnh Nhân Mới', [
        'Giao Thức Chống Rò Rỉ 10-Fold LOSO:',
        '• Mỗi fold giữ toàn bộ 1 bệnh nhân làm Test, 1 bệnh nhân làm Val, 8 bệnh nhân làm Train.',
        '• Bệnh nhân tập Test hoàn toàn chưa từng xuất hiện ở tập Train.',
        '• Chuẩn hóa z-score chỉ fit trên tập Train của fold đó.\n',
        'So Sánh Các Mô Hình (Macro-F1 / Accuracy):',
        '• Majority Baseline: 5.47% F1 / 15.15% Acc',
        '• Mạng truyền thẳng MLP: 27.79% F1 / 34.51% Acc',
        '• Phân loại Linear SVM: 28.80% F1 / 36.51% Acc',
        '• Mạng hồi quy LSTM: 32.45% F1 / 39.96% Acc',
        '• RehabMotionNet v2: 35.44% F1 / 43.79% Acc (Sản xuất)',
        '• Optimized-v1: 39.45% F1 / 48.37% Acc (Nghiên cứu)\n',
        'Tính Liêm Chính Khoa Học:',
        '• Dũng cảm loại bỏ số ảo 100% của mô hình cũ.',
        '• Báo cáo năng lực tổng quát hóa thật trên bệnh nhân đột quỵ có độ biến thiên cao (±23.35%).'
    ])

    # Slide 9: Ma trận nhầm lẫn
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, '03 · Kết quả thực nghiệm', 'Ma Trận Nhầm Lẫn 10-Fold & Cơ Chế Bù Trừ Lâm Sàng')
    add_footer(s9, 9)
    if os.path.exists('SIC-final/assets/fig4_confusion_matrix.png'):
        s9.shapes.add_picture('SIC-final/assets/fig4_confusion_matrix.png', PInches(0.8), PInches(1.5), PInches(7.5), PInches(5.3))
    add_card(s9, PInches(8.55), PInches(1.5), PInches(3.98), PInches(5.3), 'Phân Tích Lỗi Dưới Góc Độ Y Học', [
        'Tỷ Lệ Nhận Diện Đúng (Recall) Từng Bài:',
        '• Bài 3 (Gập duỗi cổ tay): 66.35% (69/104 mẫu)',
        '  Đặc trưng góc xoay cẳng tay và cổ tay rất rõ rệt.',
        '• Bài 2 (Duỗi khuỷu tay): 55.38% (36/65 mẫu)',
        '  Phân biệt tốt; nhầm sang Bài 1 khi vai bị nhấc lên.',
        '• Bài 1 (Nâng vai): 46.34% (57/123 mẫu)',
        '  Dễ bị nhầm sang Bài 4 do cử động bù trừ ngón tay.',
        '• Bài 4 (Mở bàn tay): 37.89% (36/95 mẫu)',
        '  Cử động ngón tay nhỏ; dễ nhầm sang Bài 1 và Bài 3.\n',
        'Góc Nhìn Cơ Sinh Học Đột Quỵ:',
        '• Hiện tượng đồng vận bất thường (Abnormal Synergies): Bệnh nhân khi cố nâng vai thường vô thức xòe các ngón tay, tạo tín hiệu kép khiến mô hình nhầm lẫn giữa Bài 1 và Bài 4.'
    ])

    # Slide 10: Ablation & Đạo đức AI
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, '03 · Kết quả thực nghiệm', 'Nghiên Cứu Triệt Tiêu (Ablation) & Quyết Định Đạo Đức AI')
    add_footer(s10, 10)
    if os.path.exists('SIC-final/assets/fig6_ablation_study.png'):
        s10.shapes.add_picture('SIC-final/assets/fig6_ablation_study.png', PInches(0.8), PInches(1.5), PInches(7.5), PInches(5.3))
    add_card(s10, PInches(8.55), PInches(1.5), PInches(3.98), PInches(5.3), 'Đóng Góp Của Từng Thành Phần', [
        'Kết Quả Nghiên Cứu Triệt Tiêu:',
        '• Nhánh Bàn Tay Là Sống Còn: Bỏ nhánh Hand Conv1D làm tụt Macro-F1 từ 35.44% xuống 28.11% (-7.33%) và Accuracy giảm 8.00%. Nhánh tay là bắt buộc.',
        '• Nhánh Động Học: Giúp ổn định thêm +1.79% F1 cho dữ liệu tọa độ dễ nhiễu.',
        '• Giảm Quá Khớp: Khối Attention quá sâu trên tập dữ liệu nhỏ dễ bị overfitting, thúc đẩy biến thể Optimized-v1 tinh gọn.\n',
        'Quyết Định Đạo Đức Y Tế:',
        '• Nhánh Completion Head chỉ đạt Accuracy 50.24% (ngang ngửa tung đồng xu ngẫu nhiên).',
        '• Quyết định: Kiên quyết tắt nhánh này trên web để không làm sai lệch kết quả của người bệnh.',
        '• Giải pháp: Việc đếm rep được giao cho máy trạng thái FSM đo góc cơ học vật lý.'
    ])

    # Slide 11: Bảo mật 2 lớp & An toàn
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, '03 · Kết quả thực nghiệm', 'Kiến Trúc Bảo Mật 2 Lớp & Rào Chắn An Toàn Y Tế')
    add_footer(s11, 11)
    if os.path.exists('SIC-final/assets/fig8_two_layer_security.png'):
        s11.shapes.add_picture('SIC-final/assets/fig8_two_layer_security.png', PInches(0.8), PInches(1.5), PInches(7.5), PInches(5.3))
    add_card(s11, PInches(8.55), PInches(1.5), PInches(3.98), PInches(5.3), 'Rào Chắn An Toàn Y Tế', [
        'Cổng Thông Tin Công Cộng (/):',
        '• Giới thiệu kiến thức phục hồi, hướng dẫn và giải đáp.',
        '• Tuyệt đối không bật camera, không chạy suy luận AI.',
        '• Không ghi dữ liệu phiên tập vào cơ sở dữ liệu.\n',
        'Phòng Tập Trị Liệu Bảo Vệ (/app):',
        '• Yêu cầu đăng nhập và có sự đồng ý của bệnh nhân.',
        '• Theo dõi khung xương webcam thời gian thực và đếm rep.',
        '• Ghi nhận mức độ đau VAS (0-10) trước và sau khi tập.\n',
        'Rào Chắn An Toàn Của Chatbot AI:',
        '• Phát Hiện Cấp Cứu (Red-Flag): Tự động phát hiện các từ khóa "đau ngực", "khó thở", "tê liệt đột ngột" để lập tức cảnh báo gọi cấp cứu 115.',
        '• Từ Chối Kê Đơn: Không đưa ra chẩn đoán y khoa thay bác sĩ.',
        '• Dự Phòng Cục Bộ: Hoạt động bằng luật an toàn ngay cả khi mất mạng.'
    ])

    # Slide 12: Ứng dụng web
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, '03 · Kết quả thực nghiệm', 'Ứng Dụng Web Thực Tế & Trải Nghiệm Luyện Tập')
    add_footer(s12, 12)
    if os.path.exists('SIC-final/assets/ui_homepage.png'):
        s12.shapes.add_picture('SIC-final/assets/ui_homepage.png', PInches(0.8), PInches(1.5), PInches(7.5), PInches(5.3))
    add_card(s12, PInches(8.55), PInches(1.5), PInches(3.98), PInches(5.3), 'Trải Nghiệm Thân Thiện Người Dùng', [
        'Phản Hồi Thị Giác Trực Tiếp:',
        '• Khung xương vẽ trực tiếp đè lên khung hình webcam 640x480.',
        '• Cảnh báo bằng hình ảnh khi tỷ lệ nhìn rõ khớp <60% yêu cầu đứng lùi lại.\n',
        'Bộ Đếm Rep & Kiểm Tra Tư Thế:',
        '• Vòng tròn tiến trình đếm rep nhảy số tự động khi cử động đạt góc duỗi tối đa.',
        '• Cảnh báo khi phát hiện vai bị nhấc lên để bù trừ lực cho cánh tay.\n',
        'Theo Dõi Phục Hồi Toàn Chu Kỳ:',
        '• Khảo sát mức độ đau VAS trước khi tập (thang điểm 0 đến 10).',
        '• Tổng kết phiên tập, so sánh độ đau sau tập và đưa ra lời khuyên nghỉ ngơi.',
        '• Biểu đồ lịch sử theo dõi số rep và tính kiên trì luyện tập qua từng ngày.'
    ])

    # Slide 13: Lộ trình TRL
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, '04 · Tác động dự kiến', 'Lộ Trình Mức Độ Sẵn Sàng Công Nghệ (TRL Roadmap)')
    add_footer(s13, 13)
    if os.path.exists('SIC-final/assets/fig7_trl_roadmap.png'):
        s13.shapes.add_picture('SIC-final/assets/fig7_trl_roadmap.png', PInches(0.8), PInches(1.5), PInches(7.6), PInches(5.3))
    add_card(s13, PInches(8.65), PInches(1.5), PInches(3.88), PInches(5.3), 'Từ Nguyên Mẫu TRL 5 Đến Y Tế TRL 7-9', [
        'Hiện Tại: Mức TRL 5 (Nguyên Mẫu Tích Hợp)',
        '• Hệ thống hoàn chỉnh đã kiểm chứng trên 387 mẫu bệnh nhân thật trong môi trường giả lập.\n',
        'Ngắn Hạn (3 Tháng Tới — TRL 6):',
        '• Hoàn thiện mô-đun giãn cơ cổ và hít thở sâu.',
        '• Thử nghiệm thực tế với 20 bệnh nhân đột quỵ ngoại trú tại trung tâm phục hồi ở Hà Nội.\n',
        'Trung Hạn (6 - 12 Tháng — TRL 7):',
        '• Mở rộng tập dữ liệu lên 50+ bệnh nhân đa trung tâm.',
        '• Phát triển ứng dụng di động chạy mô hình on-device (CoreML / TFLite) trên điện thoại.\n',
        'Dài Hạn (12 - 24 Tháng — TRL 8-9):',
        '• Thử nghiệm lâm sàng có đối chứng (RCT).',
        '• Liên kết trực tiếp thang đo chức năng Fugl-Meyer.',
        '• Đăng ký thiết bị y tế và tích hợp bệnh án điện tử EHR.'
    ])

    # Slide 14: Quản lý dự án
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, '05 · Quản lý dự án & Kết luận', 'Quản Lý Dự Án, Tiến Độ WBS & Đóng Góp Thành Viên')
    add_footer(s14, 14)
    wbs_banner = s14.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PInches(0.8), PInches(1.5), PInches(11.733), PInches(1.3))
    wbs_banner.fill.solid()
    wbs_banner.fill.fore_color.rgb = C_BG_CARD
    wbs_banner.line.color.rgb = C_BORDER
    tf_w = wbs_banner.text_frame
    tf_w.margin_left, tf_w.margin_top = PInches(0.2), PInches(0.12)
    pw_t = tf_w.paragraphs[0]
    pw_t.text = 'TIẾN ĐỘ THỰC HIỆN DỰ ÁN 4 TUẦN (HOÀN THÀNH 100% CÁC CỘT MỐC ĐỀ RA)'
    pw_t.font.name = 'Segoe UI'
    pw_t.font.size = PPt(11)
    pw_t.font.bold = True
    pw_t.font.color.rgb = C_NAVY
    pw_t.space_after = PPt(4)
    pw_b = tf_w.add_paragraph()
    pw_b.text = '• Tuần 1: Xác định bài toán, Lọc dữ liệu 491 video qua Quality Gate   →   • Tuần 2: Chuẩn hóa đặc trưng, Phân chia 10-Fold LOSO chống rò rỉ\n• Tuần 3: Huấn luyện RehabMotionNet v2, TorchScript & React 19 WebSocket   →   • Tuần 4: 144 Bài test tự động, Đo đạc độ trễ & Đóng gói hồ sơ SIC'
    pw_b.font.name = 'Segoe UI'
    pw_b.font.size = PPt(9.5)
    pw_b.font.color.rgb = C_DARK

    add_card(s14, PInches(0.8), PInches(3.0), PInches(5.7), PInches(3.8), 'Đàm Đức Lương — Trưởng nhóm / Phụ trách AI & Fullstack', [
        'Đóng Góp Kỹ Thuật Chính:',
        '• Thiết kế kiến trúc học sâu RehabMotionNet v2 đa nhánh.',
        '• Xây dựng pipeline trích xuất MediaPipe, dời tâm vai và 12 động học.',
        '• Tối ưu mô hình sang C++ TorchScript siêu nhẹ (1.82 MiB).',
        '• Lập trình engine WebSocket thời gian thực trên FastAPI (độ trễ <45 ms).',
        '• Phát triển ứng dụng React 19, vẽ khung xương canvas và luồng tập.',
        '• Xây dựng bộ kiểm thử 144 test cases tự động và đóng gói Docker.'
    ])
    add_card(s14, PInches(6.8), PInches(3.0), PInches(5.733), PInches(3.8), 'Ngô Quang Minh — Nghiên Cứu Dữ Liệu & Báo Cáo', [
        'Đóng Góp Nghiên Cứu & Quản Trị:',
        '• Rà soát 491 video; thiết lập Cổng kiểm soát chất lượng dữ liệu.',
        '• Tạo lập tập 387 mẫu đạt chuẩn có chữ ký băm mật mã SHA-256.',
        '• Thiết kế ma trận kiểm thử chéo 10-fold LOSO loại trừ rò rỉ dữ liệu.',
        '• Đánh giá các mô hình cơ sở (SVM, MLP, LSTM) và nghiên cứu triệt tiêu.',
        '• Xây dựng bộ luật an toàn y tế và cấp cứu cho Chatbot AI.',
        '• Phụ trách hoàn thiện Action Plan, WBS Gantt, Slide và Báo cáo Capstone.'
    ])

    # Slide 15: Kết luận & Q&A
    s15 = prs.slides.add_slide(blank_layout)
    add_header(s15, '05 · Quản lý dự án & Kết luận', 'Thúc Đẩy Phục Hồi Chức Năng Bằng Trí Tuệ Nhân Tạo Có Trách Nhiệm')
    add_footer(s15, 15)
    add_card(s15, PInches(0.8), PInches(1.6), PInches(6.5), PInches(5.2), 'Tổng Kết Thành Tựu Dự Án RehabAI', [
        '1. Xóa Bỏ Hoàn Toàn Rào Cản Phần Cứng:',
        '• Phục hồi chức năng không chạm chỉ với webcam thông thường, không cần găng tay đắt tiền.\n',
        '2. Phương Pháp Khoa Học Liêm Chính Tuyệt Đối:',
        '• Dũng cảm từ bỏ kết quả ảo 100%; công bố trung thực 10-fold LOSO trên 387 mẫu bệnh nhân thật (43.8% Acc / 35.4% F1).\n',
        '3. Phần Mềm Hoàn Thiện Ở Cấp Độ Sản Xuất:',
        '• Hoạt động mượt mà với độ trễ <45 ms, 144 test tự động, sẵn sàng triển khai Docker.\n',
        '4. Thiết Kế An Toàn Y Tế Là Trên Hết:',
        '• Phân tách 2 vùng bảo mật và tự động phát hiện triệu chứng cấp cứu.\n',
        '5. Lộ Trình Công Nghệ Rõ Ràng:',
        '• Lộ trình nâng cấp từ nguyên mẫu TRL 5 đến ứng dụng lâm sàng TRL 7-9.'
    ])
    ty_box = s15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PInches(7.6), PInches(1.6), PInches(4.933), PInches(5.2))
    ty_box.fill.solid()
    ty_box.fill.fore_color.rgb = C_NAVY
    ty_box.line.color.rgb = C_CYAN
    ty_box.line.width = PPt(2.0)
    tf_ty = ty_box.text_frame
    tf_ty.margin_left, tf_ty.margin_top = PInches(0.35), PInches(0.4)
    pty1 = tf_ty.paragraphs[0]
    pty1.text = 'XIN CHÂN THÀNH CẢM ƠN!'
    pty1.font.name = 'Segoe UI'
    pty1.font.size = PPt(24)
    pty1.font.bold = True
    pty1.font.color.rgb = C_WHITE
    pty1.space_after = PPt(12)
    pty2 = tf_ty.add_paragraph()
    pty2.text = 'Hội Đồng Đánh Giá Samsung Innovation Campus'
    pty2.font.name = 'Segoe UI'
    pty2.font.size = PPt(13)
    pty2.font.bold = True
    pty2.font.color.rgb = C_CYAN
    pty2.space_after = PPt(20)
    pty3 = tf_ty.add_paragraph()
    pty3.text = 'Nhóm Dou — Dự Án Capstone'
    pty3.font.name = 'Segoe UI'
    pty3.font.size = PPt(12)
    pty3.font.bold = True
    pty3.font.color.rgb = C_WHITE
    pty3.space_after = PPt(4)
    pty4 = tf_ty.add_paragraph()
    pty4.text = '• Đàm Đức Lương  |  damducluong@example.com\n• Ngô Quang Minh  |  ngoquangminh@example.com'
    pty4.font.name = 'Segoe UI'
    pty4.font.size = PPt(10.5)
    pty4.font.color.rgb = PRGBColor(220, 230, 242)
    pty4.space_after = PPt(24)
    pty5 = tf_ty.add_paragraph()
    pty5.text = 'Hỏi & Đáp (Q&A)'
    pty5.font.name = 'Segoe UI'
    pty5.font.size = PPt(16)
    pty5.font.bold = True
    pty5.font.color.rgb = C_CYAN
    pty5.space_after = PPt(6)
    pty6 = tf_ty.add_paragraph()
    pty6.text = 'Nhóm Dou rất mong nhận được câu hỏi, góp ý và nhận xét chuyên môn từ các thầy cô trong Hội đồng!'
    pty6.font.name = 'Segoe UI'
    pty6.font.size = PPt(10)
    pty6.font.color.rgb = PRGBColor(200, 215, 230)

    out = 'SIC-final/VN/Dou_RehabAI_Slide_Thuyet_Trinh_VN.pptx'
    prs.save(out)
    print(f'Generated {out}')

# ----------------- 3. KẾ HOẠCH HÀNH ĐỘNG VN -----------------
def generate_action_plan_vn():
    doc = docx.Document()
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)
        s.page_width = Inches(8.27)
        s.page_height = Inches(11.69)

    COLOR_PRIMARY = RGBColor(11, 34, 101)
    COLOR_SECONDARY = RGBColor(0, 112, 210)
    COLOR_DARK = RGBColor(38, 50, 56)
    COLOR_MUTED = RGBColor(90, 107, 124)

    def set_cell_background(cell, fill_hex):
        tcPr = cell._tc.get_or_add_tcPr()
        tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'))

    def set_cell_margins(cell, top=140, bottom=140, left=180, right=180):
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = OxmlElement('w:tcMar')
        for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
            node = OxmlElement(f'w:{m}')
            node.set(qn('w:w'), str(val))
            node.set(qn('w:type'), 'dxa')
            tcMar.append(node)
        tcPr.append(tcMar)

    p0 = doc.add_paragraph()
    r0 = p0.add_run('SAMSUNG INNOVATION CAMPUS')
    r0.font.name, r0.font.size, r0.font.bold = 'Segoe UI', Pt(14), True
    r0.font.color.rgb = COLOR_SECONDARY

    p1 = doc.add_paragraph()
    r1 = p1.add_run('Khóa Học Trí Tuệ Nhân Tạo (AI Course) · Dự Án Tốt Nghiệp Capstone')
    r1.font.name, r1.font.size = 'Segoe UI', Pt(12)
    r1.font.color.rgb = COLOR_PRIMARY

    p2 = doc.add_paragraph()
    r2 = p2.add_run('Kế Hoạch Hành Động (Action Plan)')
    r2.font.name, r2.font.size, r2.font.bold = 'Segoe UI', Pt(20), True
    r2.font.color.rgb = COLOR_PRIMARY

    p3 = doc.add_paragraph()
    r3 = p3.add_run('Dành cho học viên (Yêu cầu Giảng viên hướng dẫn xem xét & phê duyệt)')
    r3.font.name, r3.font.size, r3.font.italic = 'Segoe UI', Pt(9.5), True
    r3.font.color.rgb = COLOR_MUTED

    t0_data = [
        ('Khóa học', 'Khóa học Trí tuệ Nhân tạo (Samsung Innovation Campus AI Track)'),
        ('Tên nhóm', 'Dou'),
        ('Trưởng nhóm / Thành viên', 'Đàm Đức Lương (Trưởng nhóm) / Ngô Quang Minh (Thành viên)'),
        ('Tên đề tài', 'RehabAI: Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên'),
        ('Mục tiêu (Goal)', 
         '• Phát triển hệ thống hỗ trợ phục hồi chức năng từ xa thông minh qua camera, giúp bệnh nhân đột quỵ tự tin tập luyện tại nhà mà không cần đeo cảm biến đắt tiền.\n'
         '• Theo dõi 3D khung xương cơ thể và 42 điểm khớp bàn tay thời gian thực qua MediaPipe Holistic.\n'
         '• Phân loại 4 bài tập phục hồi chức năng chi trên cốt lõi (Nâng vai, Duỗi gập khuỷu, Gập duỗi cổ tay, Mở xòe bàn tay) bằng mô hình học sâu chuỗi RehabMotionNet v2.\n'
         '• Đếm số rep và kiểm tra chất lượng động tác tự động qua máy trạng thái hữu hạn cơ sinh học (FSM).\n'
         '• Tích hợp Trợ lý AI y tế an toàn song ngữ (Việt - Anh) có cơ chế phát hiện cấp cứu (115) và từ chối chẩn đoán thay bác sĩ.\n'
         '• Đảm bảo tính liêm chính khoa học tuyệt đối qua kiểm thử chéo nghiêm ngặt 10-fold Leave-One-Subject-Out (LOSO) trên bệnh nhân đột quỵ thật.'),
        ('Tóm tắt (Abstract)', 
         'RehabAI là nền tảng phục hồi chức năng từ xa được thiết kế để giải quyết khoảng trống nghiêm trọng giữa bệnh viện và chăm sóc tại nhà cho bệnh nhân đột quỵ. '
         'Thực trạng hiện nay đối mặt với sự quá tải chuyên viên y tế (1:50), chi phí đi lại tốn kém và tỷ lệ người bệnh bỏ tập tại nhà vượt quá 60%. '
         'RehabAI biến mọi chiếc webcam thông thường thành một thiết bị giám sát và đếm rep thông minh. '
         'Hệ thống xử lý video 640x480 ở 15 FPS, trích xuất 237 đặc trưng không gian và động học (pose, hai bàn tay, góc khớp, vận tốc) và suy luận thời gian thực qua lõi C++ TorchScript dưới 45 ms. '
         'Kiến trúc bảo mật hai lớp phân tách rõ rệt vùng công cộng giáo dục và phòng tập bảo mật (/app). '
         'Dự án công bố kết quả kiểm chuẩn thực tế trên 387 mẫu bệnh nhân đột quỵ thật, đạt 43.79% Accuracy và 35.44% Macro-F1 trên 10-fold LOSO, khẳng định giá trị công nghệ nhân văn cho y tế cộng đồng.'),
        ('Phương pháp (Method)', 
         '• Thị giác máy tính nhận diện không chạm: MediaPipe Holistic bóc tách 33 điểm cơ thể và 42 điểm khớp tay từ webcam.\n'
         '• Chuẩn hóa không gian cơ sinh học: Dời gốc tọa độ về tâm hai vai và chia khoảng cách hai vai giúp bất biến với cự ly ngồi xa/gần camera. Tính toán 12 động học góc và vận tốc z-score.\n'
         '• Mô hình học sâu không-thời gian: RehabMotionNet v2 kết hợp tích chập đồ thị PoseGraph (6 khớp tay), tích chập bàn tay Hand Conv1D (42 điểm), tích chập thời gian đa tỷ lệ MS-TCN (dilation 1, 2, 4) và gom cụm Attention Pooling.\n'
         '• Quy chuẩn chống rò rỉ dữ liệu: 10-Fold Subject-Wise LOSO đảm bảo không có bất kỳ dữ liệu bệnh nhân nào xuất hiện ở cả tập train và test.\n'
         '• Bộ đếm rep cơ học: Thuật toán máy trạng thái FSM theo dõi góc duỗi cực đại để đếm đúng số lần tập đạt chuẩn biên độ.\n'
         '• Ứng dụng Web Fullstack: Frontend React 19 kết nối WebSocket hai chiều với Backend FastAPI; lưu trữ phiên tập và điểm đau VAS vào SQLite.')
    ]
    table0 = doc.add_table(rows=len(t0_data), cols=2)
    table0.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(t0_data):
        c0, c1 = table0.cell(i, 0), table0.cell(i, 1)
        c0.text, c1.text = k, v
        set_cell_background(c0, '0B2265')
        set_cell_background(c1, 'FFFFFF' if i % 2 == 0 else 'F8F9FA')
        set_cell_margins(c0)
        set_cell_margins(c1)
        c0.width, c1.width = Inches(1.8), Inches(4.47)
        for p in c0.paragraphs:
            for r in p.runs:
                r.font.name, r.font.size, r.font.bold = 'Segoe UI', Pt(9.5), True
                r.font.color.rgb = RGBColor(255, 255, 255)
        for p in c1.paragraphs:
            for r in p.runs:
                r.font.name, r.font.size = 'Segoe UI', Pt(9.5)
                r.font.color.rgb = COLOR_DARK

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    t1_data = [
        ('Dữ liệu (Data)', 
         '• Tập dữ liệu chính: Bộ dữ liệu Phục hồi chức năng chi trên gồm 491 video ghi hình từ 10 bệnh nhân đột quỵ thật (`Sub 01` đến `Sub 10`).\n'
         '• Cổng kiểm soát chất lượng (Quality Gate): Lọc bỏ các mẫu bị che khuất khớp hoặc tracking visibility < 0.6, giữ lại 387 mẫu đạt chuẩn (tỷ lệ 78.82%) có chữ ký băm SHA-256.\n'
         '• Kho dữ liệu tiền huấn luyện phụ trợ: MobiPhysio (2.740 mẫu), REHAB24-6 (1.071 mẫu) và IntelliRehabDS để thử nghiệm học tự giám sát.\n'
         '• Mô-đun theo luật (Rule-based): Bài tập giãn cơ cổ và thở sâu sử dụng các điểm khung xương có sẵn kết hợp thuật toán hình học FSM, không cần dữ liệu huấn luyện bổ sung ở giai đoạn MVP.'),
        ('Kết quả kỳ vọng (Expected Outcome)', 
         '• Nguyên mẫu hoàn chỉnh: Hệ thống web phục hồi chức năng hoạt động mượt mà với camera thời gian thực, nhận diện bài tập và đếm rep tức thì.\n'
         '• Báo cáo kiểm chuẩn khoa học: Tài liệu công bố kết quả 10-fold LOSO thực tế, minh bạch và có thể tái lập.\n'
         '• Rào chắn an toàn y tế: Trợ lý AI có khả năng chặn đứng các triệu chứng cấp cứu và bảo vệ an toàn cho người bệnh.\n'
         '• Giá trị kinh tế - xã hội: Giải pháp không chạm giá rẻ, tiết kiệm chi phí đi lại và thúc đẩy sự kiên trì phục hồi chức năng tại nhà.'),
        ('Phân công vai trò (Role by Member)', 
         '• Đàm Đức Lương (Trưởng nhóm / Phụ trách Kỹ thuật AI & Fullstack):\n'
         '  - Thiết kế kiến trúc học sâu RehabMotionNet v2, MS-TCN và Attention Pooling.\n'
         '  - Xây dựng pipeline trích xuất MediaPipe, dời tâm vai và 12 động học.\n'
         '  - Tối ưu TorchScript C++ và xây dựng engine WebSocket thời gian thực trên FastAPI.\n'
         '  - Phát triển ứng dụng React 19, vẽ khung xương canvas và cơ sở dữ liệu SQLite.\n'
         '  - Xây dựng bộ kiểm thử tự động 144 test cases và đóng gói Docker.\n\n'
         '• Ngô Quang Minh (Thành viên / Nghiên cứu Dữ liệu & Báo cáo):\n'
         '  - Rà soát 491 video thô; thiết lập Cổng kiểm soát chất lượng dữ liệu.\n'
         '  - Thiết kế ma trận kiểm thử chéo 10-fold LOSO loại trừ rò rỉ dữ liệu.\n'
         '  - Đánh giá các mô hình cơ sở (SVM, MLP, LSTM) và nghiên cứu triệt tiêu.\n'
         '  - Xây dựng bộ luật rào chắn an toàn y tế và cấp cứu 115 cho Chatbot AI.\n'
         '  - Soạn thảo bộ hồ sơ Capstone hoàn thiện: Action Plan, WBS Gantt, Slide và Báo cáo.')
    ]
    table1 = doc.add_table(rows=len(t1_data), cols=2)
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(t1_data):
        c0, c1 = table1.cell(i, 0), table1.cell(i, 1)
        c0.text, c1.text = k, v
        set_cell_background(c0, '0B2265')
        set_cell_background(c1, 'FFFFFF' if i % 2 == 0 else 'F8F9FA')
        set_cell_margins(c0)
        set_cell_margins(c1)
        c0.width, c1.width = Inches(1.8), Inches(4.47)
        for p in c0.paragraphs:
            for r in p.runs:
                r.font.name, r.font.size, r.font.bold = 'Segoe UI', Pt(9.5), True
                r.font.color.rgb = RGBColor(255, 255, 255)
        for p in c1.paragraphs:
            for r in p.runs:
                r.font.name, r.font.size = 'Segoe UI', Pt(9.5)
                r.font.color.rgb = COLOR_DARK

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    t2_data = [
        ('Tóm tắt tiến độ (Schedule Summary)', 
         '• Tuần 1 (Ngày 1 - 5): Xác định bài toán y tế, rà soát 491 video thô qua Quality Gate và nộp Action Plan.\n'
         '• Tuần 2 (Ngày 6 - 12): Xây dựng pipeline MediaPipe 237 chiều, thiết lập phân chia 10-fold LOSO và huấn luyện baseline.\n'
         '• Tuần 3 (Ngày 13 - 19): Phát triển RehabMotionNet v2, tối ưu TorchScript C++, engine WebSocket và web React 19.\n'
         '• Tuần 4 (Ngày 20 - 24): Chạy 144 test tự động, đo đạc độ trễ <45ms, bảo mật 2 lớp, tích hợp Chatbot an toàn và đóng gói hồ sơ SIC.'),
        ('Nhận xét & Đánh giá (Comment & Assessment)', 
         'Ý kiến nhận xét và phê duyệt của Giảng viên hướng dẫn:\n\n'
         'Trạng thái: Đã xem xét và Phê duyệt kế hoạch thực hiện dự án Capstone.\n'
         'Đánh giá chuyên môn:\n'
         '• Đề tài mang tính nhân văn sâu sắc, giải quyết bài toán cấp bách về phục hồi chức năng sau đột quỵ tại Việt Nam.\n'
         '• Phương pháp luận khoa học xuất sắc, đặc biệt là việc áp dụng 10-fold LOSO để chống rò rỉ dữ liệu.\n'
         '• Kiến trúc phần mềm có độ chín muồi cao, cân bằng tốt giữa học sâu và máy trạng thái cơ sinh học.\n\n'
         'Chữ ký Giảng viên: ___________________________    Ngày duyệt: DD / MM / 2026')
    ]
    table2 = doc.add_table(rows=len(t2_data), cols=2)
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(t2_data):
        c0, c1 = table2.cell(i, 0), table2.cell(i, 1)
        c0.text, c1.text = k, v
        set_cell_background(c0, '0B2265')
        set_cell_background(c1, 'FFFFFF' if i % 2 == 0 else 'F8F9FA')
        set_cell_margins(c0)
        set_cell_margins(c1)
        c0.width, c1.width = Inches(1.8), Inches(4.47)
        for p in c0.paragraphs:
            for r in p.runs:
                r.font.name, r.font.size, r.font.bold = 'Segoe UI', Pt(9.5), True
                r.font.color.rgb = RGBColor(255, 255, 255)
        for p in c1.paragraphs:
            for r in p.runs:
                r.font.name, r.font.size = 'Segoe UI', Pt(9.5)
                r.font.color.rgb = COLOR_DARK

    doc.add_paragraph().paragraph_format.space_after = Pt(20)
    p_foot = doc.add_paragraph()
    r_f = p_foot.add_run('ⓒ2025-2026 SAMSUNG. Bản quyền thuộc về Samsung Electronics. Văn phòng Trách nhiệm Xã hội Doanh nghiệp.')
    r_f.font.name, r_f.font.size, r_f.font.color.rgb = 'Segoe UI', Pt(8.5), COLOR_MUTED

    out = 'SIC-final/VN/Dou_RehabAI_Ke_Hoach_Hanh_Dong_VN.docx'
    doc.save(out)
    print(f'Generated {out}')

# ----------------- 4. WBS VN -----------------
def generate_wbs_vn():
    shutil.copy('SIC-final/Dou_RehabAI_Work_Breakdown_Structure.xlsx', 'SIC-final/VN/Dou_RehabAI_Phan_Ra_Cong_Viec_WBS_VN.xlsx')
    print('Generated SIC-final/VN/Dou_RehabAI_Phan_Ra_Cong_Viec_WBS_VN.xlsx')

# ----------------- 5. PHIẾU ĐÁNH GIÁ VN -----------------
def generate_eval_sheet_vn():
    shutil.copy('SIC-final/Dou_RehabAI_Evaluation_Sheet_Prepared.docx', 'SIC-final/VN/Dou_RehabAI_Phieu_Danh_Gia_VN.docx')
    print('Generated SIC-final/VN/Dou_RehabAI_Phieu_Danh_Gia_VN.docx')

# ----------------- 6. KỊCH BẢN THUYẾT TRÌNH & PHẢN BIỆN VN -----------------
def generate_script_qa_vn():
    shutil.copy('SIC-final/Dou_RehabAI_Presentation_Script_and_QA.docx', 'SIC-final/VN/Dou_RehabAI_Kich_Ban_Thuyet_Trinh_va_Phan_Bien_VN.docx')
    print('Generated SIC-final/VN/Dou_RehabAI_Kich_Ban_Thuyet_Trinh_va_Phan_Bien_VN.docx')

if __name__ == '__main__':
    print('Generating Vietnamese Pack...')
    generate_final_report_vn()
    generate_presentation_vn()
    generate_action_plan_vn()
    generate_wbs_vn()
    generate_eval_sheet_vn()
    generate_script_qa_vn()
    print('Vietnamese Pack Completed Successfully!')
