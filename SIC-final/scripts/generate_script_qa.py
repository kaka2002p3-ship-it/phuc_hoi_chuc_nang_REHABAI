import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def create_script_qa():
    doc = docx.Document()

    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)
        s.page_width = Inches(8.27)
        s.page_height = Inches(11.69)

    C_NAVY = RGBColor(11, 34, 101)      # #0B2265
    C_BLUE = RGBColor(0, 112, 210)     # #0070D2
    C_DARK = RGBColor(38, 50, 56)      # #263238
    C_MUTED = RGBColor(90, 107, 124)

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
                            run.font.color.rgb = C_DARK

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Segoe UI'
        run.font.size = Pt(15)
        run.font.bold = True
        run.font.color.rgb = C_NAVY
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Segoe UI'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = C_BLUE
        return p

    def add_body(text, bold_prefix=None, space_after=5):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.name = 'Segoe UI'
            r_pre.font.size = Pt(9.5)
            r_pre.font.bold = True
            r_pre.font.color.rgb = C_DARK
        run = p.add_run(text)
        run.font.name = 'Segoe UI'
        run.font.size = Pt(9.5)
        run.font.color.rgb = C_DARK
        return p

    # Header
    p0 = doc.add_paragraph()
    p0.paragraph_format.space_before = Pt(10)
    p0.paragraph_format.space_after = Pt(2)
    r0 = p0.add_run('SAMSUNG INNOVATION CAMPUS · AI CAPSTONE PROJECT')
    r0.font.name = 'Segoe UI'
    r0.font.size = Pt(11)
    r0.font.bold = True
    r0.font.color.rgb = C_BLUE

    p1 = doc.add_paragraph()
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after = Pt(4)
    r1 = p1.add_run('Kịch Bản Thuyết Trình Chi Tiết & Bộ Câu Hỏi Phản Biện (Q&A)')
    r1.font.name = 'Segoe UI'
    r1.font.size = Pt(18)
    r1.font.bold = True
    r1.font.color.rgb = C_NAVY

    p2 = doc.add_paragraph()
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.space_after = Pt(16)
    r2 = p2.add_run('Dự án: RehabAI: Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên  |  Nhóm Dou: Đàm Đức Lương & Ngô Quang Minh')
    r2.font.name = 'Segoe UI'
    r2.font.size = Pt(10)
    r2.font.italic = True
    r2.font.color.rgb = C_MUTED

    # Section 1: Presentation Script
    add_h1('Phần 1: Kịch Bản Thuyết Trình Từng Slide (Thời Lượng Chuẩn: 12 - 15 Phút)')

    slides_script = [
        ('Slide 1: Tiêu đề dự án (Cover)', '0:00 - 0:45',
         'Kính thưa Ban giám khảo và các thầy cô Hội đồng Samsung Innovation Campus. Chúng em là nhóm Dou, gồm hai thành viên: Đàm Đức Lương - phụ trách phát triển hệ sinh thái AI và nền tảng Fullstack, và Ngô Quang Minh - phụ trách nghiên cứu dữ liệu, đánh giá mô hình và an toàn y tế. Hôm nay, chúng em xin đại diện nhóm bảo vệ dự án Capstone: "RehabAI: Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên", ứng dụng thị giác máy tính và học sâu thời gian thực.'),
        
        ('Slide 2: Thực trạng & Động lực lâm sàng', '0:45 - 2:00',
         'Đột quỵ là nguyên nhân hàng đầu gây tàn tật vận động ở người trưởng thành, với hơn 200.000 ca mắc mới mỗi năm tại Việt Nam và trên 80% để lại di chứng liệt nửa người, đặc biệt là chi trên. Để phục hồi chức năng, bệnh nhân bắt buộc phải thực hiện hàng trăm cử động lặp đi lặp lại mỗi ngày để tái tạo liên kết thần kinh. Tuy nhiên, tỷ lệ chuyên viên phục hồi chức năng tại các cơ sở y tế công lập chỉ đạt 1 trên 50 bệnh nhân, chi phí đi lại tốn kém khiến hơn 60% bệnh nhân bỏ cuộc sau 6 tháng. Các giải pháp găng tay cảm biến ngoại vi hiện nay có giá thành hàng nghìn USD và người bệnh liệt một tay không thể tự đeo. Đây chính là động lực để chúng em phát triển RehabAI - giải pháp hoàn toàn không chạm (contactless), chỉ sử dụng webcam máy tính thông thường.'),
        
        ('Slide 3: Mục tiêu cốt lõi của dự án', '2:00 - 3:15',
         'RehabAI đặt ra 6 mục tiêu kỹ thuật rõ ràng: Thứ nhất, nhận diện không chạm 33 điểm khung xương và 42 điểm bàn tay qua MediaPipe Holistic. Thứ hai, phân loại 4 bài tập vận động cốt lõi cho chi trên qua mô hình học sâu chuỗi RehabMotionNet v2. Thứ ba, đếm số lần tập (rep) chính xác bằng máy trạng thái hữu hạn động học. Thứ tư, xây dựng nền tảng web bảo mật 2 lớp phân tách rõ rệt. Thứ năm, trợ lý AI song ngữ có rào chắn an toàn ngăn chặn phát ngôn sai lệch và phát hiện cấp cứu. Thứ sáu, duy trì tính liêm chính khoa học tuyệt đối qua kiểm thử chéo 10-fold LOSO trên bệnh nhân thật.'),
        
        ('Slide 4: Kiến trúc hệ thống tổng thể', '3:15 - 4:30',
         'Kiến trúc RehabAI gồm 4 tầng chính: Tầng Client sử dụng React 19 tối ưu, bắt hình ảnh 640x480 ở 15 FPS và vẽ khung xương trực tiếp trên HTML5 canvas; Tầng Feature Engine xử lý chuẩn hóa tọa độ tâm vai và trích xuất 12 động học; Tầng Inference Core vận hành mô hình TorchScript C++ với kích thước cực nhẹ 1.82 MiB; Tầng Backend FastAPI kết nối WebSocket hai chiều cho độ trễ dưới 45 ms, đồng thời lưu trữ phiên tập và mức độ đau VAS vào cơ sở dữ liệu SQLite.'),
        
        ('Slide 5: Quản trị dữ liệu & Cổng kiểm soát chất lượng (Quality Gate)', '4:30 - 5:45',
         'Dữ liệu của dự án được thu thập từ 10 bệnh nhân đột quỵ thật với 491 video gốc. Thay vì sử dụng bừa bãi dữ liệu nhiễu, chúng em thiết lập Cổng kiểm soát chất lượng nghiêm ngặt: loại bỏ các mẫu bị che khuất khớp chính hoặc độ tin cậy tracking dưới 60%. Kết quả giữ lại 387 mẫu bệnh nhân đạt chuẩn chất lượng cao (tỷ lệ 78.82%). Phân bố bài tập phản ánh đúng thực tế phục hồi chức năng: Nâng vai chiếm 31.8%, Duỗi khuỷu 16.8%, Gập duỗi cổ tay 26.9%, và Mở xòe bàn tay chiếm 24.6%.'),
        
        ('Slide 6: Đường ống trích xuất đặc trưng & Chuẩn hóa động học', '5:45 - 7:00',
         'Thách thức lớn nhất của camera gia đình là khoảng cách bệnh nhân thay đổi liên tục. Chúng em giải quyết triệt để bằng thuật toán chuẩn hóa không gian: Dời gốc tọa độ (0,0,0) về trung điểm nối hai khớp vai, sau đó chia toàn bộ tọa độ cho độ rộng hai vai. Nhờ đó, dù bệnh nhân ngồi cách xa 1 mét hay 2.5 mét, tensor đặc trưng vẫn đồng nhất. Chúng em kết hợp thêm 12 đặc trưng động học z-score (góc vai, góc khuỷu, độ nghiêng thân mình, vận tốc góc và vận tốc dịch chuyển cổ tay) để tạo thành tensor chuyển động kích thước 96 frame x 237 chiều.'),
        
        ('Slide 7: Mạng nơ-ron không-thời gian RehabMotionNet v2', '7:00 - 8:15',
         'Mô hình trung tâm của dự án là RehabMotionNet v2 (451.561 tham số), được thiết kế đa nhánh: Nhánh PoseGraph xử lý liên kết hình học 6 khớp tay chính; Nhánh Hand Conv1D xử lý chi tiết 42 điểm ngón tay; Nhánh Kinematic bổ trợ thông số vật lý. Ba luồng dữ liệu được hợp nhất qua mạng tích chập thời gian đa tỷ lệ (Multi-Scale TCN) với dilation 1, 2, 4 nhằm nắm bắt cả vi rung động và nhịp điệu bài tập. Lớp Attention Pooling giúp mô hình tự học cách tập trung vào thời điểm duỗi cực đại thay vì bị nhiễu bởi các khoảng nghỉ.'),
        
        ('Slide 8: Kết quả thực nghiệm kiểm chuẩn 10-Fold LOSO', '8:15 - 9:30',
         'Điểm tự hào nhất của nhóm Dou là tính liêm chính khoa học: Chúng em dũng cảm loại bỏ những con số ảo 100% của các mô hình cũ (do rò rỉ dữ liệu cùng bệnh nhân ở train và test). Thay vào đó, chúng em thực hiện giao thức nghiêm ngặt nhất trong y tế: 10-Fold Leave-One-Subject-Out (LOSO) trên 387 mẫu bệnh nhân thật. Mô hình RehabMotionNet v2 sản xuất đạt Accuracy 43.79% và Macro-F1 35.44%, vượt trội hoàn toàn so với Majority baseline (15.2%), Linear SVM (36.5%), MLP (34.5%) và LSTM (40.0%). Biến thể nghiên cứu Optimized-v1 của nhóm thậm chí đã chạm mốc 48.37% Accuracy và 39.45% Macro-F1.'),
        
        ('Slide 9: Phân tích ma trận nhầm lẫn & Cơ chế bù trừ lâm sàng', '9:30 - 10:45',
         'Ma trận nhầm lẫn 10-fold cho thấy: Bài gập duỗi cổ tay đạt độ nhạy cao nhất 66.35%, duỗi khuỷu đạt 55.38%, nâng vai đạt 46.34% và mở bàn tay đạt 37.89%. Nguyên nhân nhầm lẫn chính giữa bài 1 và bài 4 xuất phát từ hiện tượng đồng vận bất thường (Abnormal Synergies) - người bệnh đột quỵ khi cố gắng nâng vai thường vô thức xòe các ngón tay. Việc mô hình ghi nhận sự nhầm lẫn này chính là bằng chứng xác thực cho thấy AI đang học đúng chuyển động của bệnh nhân thật.'),
        
        ('Slide 10: Nghiên cứu triệt tiêu (Ablation) & Quyết định đạo đức AI', '10:45 - 11:45',
         'Nghiên cứu triệt tiêu chứng minh nhánh bàn tay (Hand Conv1D) có vai trò sống còn: nếu bỏ nhánh này, F1 giảm tới 7.33% và Accuracy giảm 8.00%. Đồng thời, chúng em đưa ra một quyết định đạo đức quan trọng: Nhánh dự đoán hoàn thành bài tập (Completion Head) chỉ đạt 50.24% accuracy (ngang ngửa tung đồng xu ngẫu nhiên). Chúng em đã kiên quyết vô hiệu hoá nhánh này, không đưa vào giao diện web để tránh đánh lừa người bệnh. Toàn bộ logic đếm số rep được chuyển giao cho máy trạng thái động học đáng tin cậy.'),
        
        ('Slide 11: Kiến trúc bảo mật 2 lớp & Rào chắn an toàn y tế', '11:45 - 12:45',
         'Để bảo vệ bệnh nhân, hệ thống phân tách 2 lớp: Vùng công cộng giới thiệu kiến thức và không bao giờ kích hoạt camera; Vùng phòng tập `/app` yêu cầu đăng nhập và có sự đồng ý của người dùng. Trợ lý AI song ngữ tích hợp bộ lọc an toàn cục bộ: nếu phát hiện các từ khóa cấp cứu như "đau thắt ngực", "tê liệt đột ngột", hệ thống sẽ lập tức cảnh báo bệnh nhân gọi cấp cứu 115, đồng thời kiên quyết từ chối đưa ra chẩn đoán thay thế bác sĩ.'),
        
        ('Slide 12: Trải nghiệm ứng dụng thực tế trên Web', '12:45 - 13:30',
         'Ứng dụng React 19 cung cấp phản hồi thị giác tức thì: Khung xương khớp vẽ đè lên webcam, vòng tròn đếm số rep tăng dần theo biên độ duỗi thật, cảnh báo khi phát hiện tư thế bù trừ vai, thanh trượt ghi nhận mức độ đau VAS trước và sau tập, cùng biểu đồ lịch sử theo dõi tiến độ phục hồi qua từng ngày.'),
        
        ('Slide 13: Lộ trình sẵn sàng công nghệ (TRL Roadmap)', '13:30 - 14:15',
         'RehabAI hiện tại đã đạt mức TRL 5: Nguyên mẫu tích hợp hoàn chỉnh được kiểm chứng trong môi trường mô phỏng. Kế hoạch ngắn hạn 3 tháng tới là tiến lên TRL 6 thông qua thử nghiệm thực địa với 20 bệnh nhân ngoại trú tại các trung tâm phục hồi chức năng ở Hà Nội. Kế hoạch trung hạn 6-12 tháng là mở rộng dữ liệu 50+ bệnh nhân và phát triển phiên bản mobile trên Android/iOS.'),
        
        ('Slide 14: Quản lý dự án & Đóng góp của các thành viên', '14:15 - 14:45',
         'Nhóm Dou đã hoàn thành 100% các mốc WBS trong 4 tuần: Từ lập kế hoạch, lọc dữ liệu, huấn luyện mô hình LOSO, tối ưu TorchScript đến xây dựng web app và 144 bài kiểm thử tự động. Sự phối hợp ăn ý giữa Đức Lương và Quang Minh đã giúp dự án vượt qua thách thức lớn nhất về rò rỉ dữ liệu để hoàn thiện đúng tiến độ.'),
        
        ('Slide 15: Kết luận & Lời cảm ơn', '14:45 - 15:00',
         'RehabAI đã chứng minh khả năng đưa AI có trách nhiệm vào phục hồi chức năng, giúp người bệnh lấy lại sự tự chủ vận động với chi phí bằng 0 cho thiết bị cảm biến. Chúng em xin chân thành cảm ơn các thầy cô Samsung Innovation Campus đã tận tình hướng dẫn. Nhóm Dou rất mong nhận được câu hỏi và nhận xét từ Hội đồng!')
    ]

    for title, timing, script in slides_script:
        add_h2(f'{title}  [{timing}]')
        add_body(script)

    doc.add_page_break()

    # Section 2: Q&A Defense Guide
    add_h1('Phần 2: Bộ Câu Hỏi Phản Biện Trọng Tâm Của Hội Đồng & Đáp Án Chuẩn')

    qa_list = [
        ('Câu hỏi 1: Tại sao Accuracy nhận diện bài tập chỉ đạt 43.79% và Macro-F1 là 35.44%? Liệu con số này có quá thấp để triển khai ứng dụng thực tế?',
         'Đáp án đắt giá:\n'
         'Thưa thầy cô, đây là một điểm mấu chốt thể hiện tính liêm chính khoa học của nhóm Dou:\n'
         '1. Thứ nhất, 43.79% là kết quả thu được trên giao thức kiểm thử khắt khe nhất trong y tế: 10-Fold Leave-One-Subject-Out (LOSO) trên bệnh nhân đột quỵ thật. Bệnh nhân ở tập kiểm thử hoàn toàn xa lạ với tập huấn luyện.\n'
         '2. Thứ hai, các nghiên cứu trước đây thường báo cáo độ chính xác 95-100% là do chia train/test ngẫu nhiên trên cùng một video hoặc cùng một bệnh nhân (Data Leakage), khiến mô hình học vẹt đặc điểm bệnh nhân thay vì bài tập.\n'
         '3. Thứ ba, 43.79% vượt trội gấp 3 lần so với Majority Baseline (15.15%) và vượt xa các mô hình SVM (36.5%) hay MLP (34.5%).\n'
         '4. Thứ tư, trong ứng dụng thực tế, người bệnh luôn chọn bài tập trước khi vào phòng tập. AI đóng vai trò giám sát và xác nhận người dùng có tập đúng bài đã chọn hay không (Verification flag), kết hợp cùng bộ đếm động học FSM để đếm rep. Do đó, hệ thống hoàn toàn đảm bảo tính hữu ích và an toàn cho người dùng.'),
        
        ('Câu hỏi 2: Làm thế nào các bạn đảm bảo 100% không bị Data Leakage giữa các bệnh nhân?',
         'Đáp án đắt giá:\n'
         'Nhóm kiểm soát chống rò rỉ dữ liệu ở 4 cấp độ:\n'
         '1. Cấp độ phân chia: Sử dụng strictly Subject-Wise split: Với mỗi fold k, toàn bộ video của Bệnh nhân k chỉ nằm ở Test set; 1 bệnh nhân làm Validation set; 8 bệnh nhân còn lại làm Train set.\n'
         '2. Cấp độ tiền xử lý: Toàn bộ thống kê Mean và Std của phép chuẩn hóa z-score cho 12 đặc trưng động học chỉ được fit trên tập Train, sau đó mới transform cho Validation và Test.\n'
         '3. Cấp độ thời gian: Phép tăng cường dữ liệu (Data Augmentation) chỉ áp dụng trong epoch train, không áp dụng trước khi chia fold.\n'
         '4. Cấp độ xác minh: Mã nguồn kiểm thử `test_leakage_audit.py` kiểm tra giao của tập ID bệnh nhân giữa Train và Test bằng rỗng trước khi cho phép bắt đầu huấn luyện.'),
        
        ('Câu hỏi 3: Tại sao các bạn lại vô hiệu hoá (gate) nhánh Completion Head (dự đoán động tác hoàn thành)?',
         'Đáp án đắt giá:\n'
         'Đây là quyết định xuất phát từ đạo đức AI y tế (Responsible AI):\n'
         'Mô hình ban đầu có một nhánh phụ binary classification để đoán bài tập Complete hay Incomplete. Tuy nhiên, khi đánh giá LOSO, nhánh này chỉ đạt Accuracy 50.24% và F1 48.28%—hoàn toàn tương đương với việc tung đồng xu may rủi. Nếu đưa tính năng này lên web, nó có thể báo sai khiến bệnh nhân tưởng mình đã tập đủ biên độ hoặc ngược lại làm người bệnh nản lòng. Nhóm kiên quyết tắt nhánh này trên giao diện và chuyển sang dùng máy trạng thái động học (FSM) đo góc khớp vật lý thực tế, chỉ tăng số rep khi góc duỗi vượt qua ngưỡng lâm sàng quy định.'),
        
        ('Câu hỏi 4: Hệ thống xử lý thế nào khi người bệnh tập trong phòng tối hoặc một phần cơ thể bị che khuất?',
         'Đáp án đắt giá:\n'
         'RehabAI tích hợp cơ chế Cổng chất lượng thời gian thực (Quality Gate):\n'
         'MediaPipe Holistic trả về chỉ số visibility (độ nhìn rõ) cho từng khớp. Hệ thống liên tục kiểm tra 6 khớp trọng yếu (vai, khuỷu, cổ tay hai bên). Nếu tỷ lệ khớp nhìn thấy dưới 60% liên tiếp 5 frame, hệ thống sẽ tạm dừng đếm rep và hiển thị thông báo trực quan trên màn hình yêu cầu bệnh nhân điều chỉnh lại ánh sáng hoặc lùi ra xa camera. Khi chất lượng phục hồi trên 60%, quá trình tập mới tiếp tục, ngăn ngừa tuyệt đối việc nhận diện sai do mất dấu khung xương.'),
        
        ('Câu hỏi 5: Kiến trúc mô hình RehabMotionNet v2 có gì đột phá so với các kiến trúc ST-GCN truyền thống?',
         'Đáp án đắt giá:\n'
         'Các kiến trúc ST-GCN truyền thống thường chỉ xử lý toàn thân và bỏ qua chi tiết ngón tay do số điểm quá lớn gây nặng nề. RehabMotionNet v2 đột phá ở thiết kế đa nhánh chuyên biệt cho phục hồi chức năng:\n'
         '1. Nhánh bàn tay Hand Conv1D riêng biệt: Nghiên cứu triệt tiêu của nhóm chứng minh nếu không có nhánh này, F1 giảm ngay 7.33% vì cử động mở bàn tay phụ thuộc vào khoảng cách các đốt ngón tay chứ không phải khung xương tay.\n'
         '2. Kết hợp 12 đặc trưng động học vật lý: Thay vì để mạng tự đoán góc, nhóm nạp trực tiếp vận tốc góc và góc khớp giúp mô hình học nhanh hơn trên dữ liệu nhỏ.\n'
         '3. Tối ưu hóa TorchScript: Kích thước mô hình chỉ 1.82 MiB, chạy suy luận chỉ mất 11 ms trên CPU thông thường, không đòi hỏi card đồ họa rời đắt tiền.')
    ]

    for q, a in qa_list:
        add_h2(q)
        add_body(a)

    output_path = 'SIC-final/Dou_RehabAI_Presentation_Script_and_QA.docx'
    doc.save(output_path)
    print(f'Successfully generated {output_path}!')

if __name__ == '__main__':
    create_script_qa()

