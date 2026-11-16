import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

def polish_wbs():
    wb = openpyxl.load_workbook('SIC-final/Dou_RehabAI_Work_Breakdown_Structure.xlsx')
    
    # 1. Polish Cover Page
    ws_cover = wb['Cover Page']
    # Check Project Title, Team Name, Date
    ws_cover['D14'] = 'RehabAI: Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên'
    ws_cover['D16'] = 'Team Dou: Đàm Đức Lương & Ngô Quang Minh'
    ws_cover['D17'] = 'Date: 07/11/2026'

    # 2. Polish WBS sheet
    ws = wb['WBS']
    ws['E7'] = '07/11/2026'
    ws['E8'] = 'Dou'
    ws['E9'] = 'RehabAI: Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên'

    # Task definitions: (row, task_col, task_name, start_d, end_d, resp, deliverable, d_start, d_end)
    # Day mapping: D1=11, D2=12, ..., D20=30
    tasks = [
        # 1. Project Planning (D1 - D2)
        (14, 2, '1. Project Planning & Requirement Analysis', 'W1-D1', 'W1-D2', 'All', 'Scope definition, clinical needs, target user persona', 1, 2),
        (15, 3, '1.1 Requirement analysis & clinical scope', 'W1-D1', 'W1-D1', 'Ngô Quang Minh', 'Requirement documentation & user stories', 1, 1),
        (16, 3, '1.2 Architecture, safety boundary & risk plan', 'W1-D2', 'W1-D2', 'Đàm Đức Lương', 'System architecture specification & risk analysis', 2, 2),
        
        # 2. Data and Preprocessing (D3 - D6)
        (17, 2, '2. Data Acquisition, Quality Gate & Preprocessing', 'W1-D3', 'W2-D6', 'Đàm Đức Lương', 'Landmark extraction & verified 387-sample dataset', 3, 6),
        (18, 3, '2.1 Dataset collection, inspection & quality gate', 'W1-D3', 'W1-D4', 'Ngô Quang Minh', 'Quality gate audit (491 videos -> 387 verified)', 3, 4),
        (19, 3, '2.2 MediaPipe Holistic & 12-kinematics extraction', 'W1-D5', 'W2-D6', 'Đàm Đức Lương', 'Mid-shoulder normalization & 237-D motion tensors', 5, 6),
        
        # 3. Modeling and Algorithm (D7 - D12)
        (20, 2, '3. Modeling, LOSO Evaluation & Algorithm Design', 'W2-D7', 'W3-D12', 'All', 'RehabMotionNet v2, 10-fold LOSO benchmark & FSM', 7, 12),
        (21, 3, '3.1 Baseline benchmarking & 10-fold LOSO evaluation', 'W2-D7', 'W2-D8', 'Ngô Quang Minh', 'Strict LOSO benchmark (Majority, SVM, MLP, LSTM)', 7, 8),
        (22, 3, '3.2 Multi-stream RehabMotionNet v2 & MS-TCN', 'W2-D9', 'W3-D10', 'Đàm Đức Lương', 'PoseGraph, Hand Conv1D, MS-TCN, TorchScript C++', 9, 10),
        (23, 3, '3.3 Biomechanical repetition counter & FSM logic', 'W3-D11', 'W3-D11', 'Đàm Đức Lương', 'Deterministic joint angle velocity peak-detection FSM', 11, 11),
        (24, 3, '3.4 Rule-based neck stretch & deep breathing design', 'W3-D12', 'W3-D12', 'Đàm Đức Lương', 'Geometry state machines for neck & breathing modules', 12, 12),
        
        # 4. System Implementation (D13 - D17)
        (25, 2, '4. Fullstack System Implementation & Telehealth App', 'W3-D13', 'W4-D17', 'Đàm Đức Lương', 'Interactive React 19 web app & FastAPI WebSocket core', 13, 17),
        (26, 3, '4.1 Two-layer web UI & security isolation', 'W3-D13', 'W3-D14', 'Đàm Đức Lương', 'Public educational portal vs protected /app zone', 13, 14),
        (27, 3, '4.2 Real-time WebSocket stream & skeletal canvas', 'W3-D15', 'W3-D15', 'Đàm Đức Lương', '15 FPS video pipeline, real-time skeleton overlay', 15, 15),
        (28, 3, '4.3 Session database, VAS pain logger & charts', 'W4-D16', 'W4-D16', 'Đàm Đức Lương', 'SQLAlchemy SQLite schema, session history & progress', 16, 16),
        (29, 3, '4.4 Guardrailed bilingual AI assistant integration', 'W4-D17', 'W4-D17', 'Ngô Quang Minh', 'Emergency red-flag heuristics & clinical boundaries', 17, 17),
        
        # 5. Testing and Documentation (D18 - D20)
        (30, 2, '5. Testing, Optimization & Capstone Deliverables', 'W4-D18', 'W4-D20', 'All', '144 automated tests, latency audit & final reports', 18, 20),
        (31, 3, '5.1 Automated test suite, latency QA & containerization', 'W4-D18', 'W4-D19', 'Đàm Đức Lương', '144 pytest suite, <45ms latency QA, Docker bundle', 18, 19),
        (32, 3, '5.2 Capstone Final Report, Action Plan, WBS & Slides', 'W4-D19', 'W4-D20', 'Ngô Quang Minh', 'Comprehensive report, deck, WBS & evaluation sheet', 19, 20)
    ]

    fill_main = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
    fill_gantt_main = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
    fill_gantt_sub = PatternFill(start_color='2E75B6', end_color='2E75B6', fill_type='solid')
    fill_done = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')

    font_main = Font(name='Segoe UI', size=10, bold=True, color='0B2265')
    font_sub = Font(name='Segoe UI', size=9.5, bold=False, color='263238')
    font_done = Font(name='Segoe UI', size=9, bold=True, color='375623')
    font_gantt = Font(name='Segoe UI', size=9, bold=True, color='FFFFFF')

    align_center = Alignment(horizontal='center', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')

    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    # Clear old task rows
    for r in range(14, 45):
        for c in range(2, 31):
            ws.cell(r, c).value = None
            ws.cell(r, c).fill = PatternFill(fill_type=None)

    for row_idx, task_col, task_name, start_d, end_d, resp, deliverable, d_start, d_end in tasks:
        is_main = (task_col == 2)
        
        # Set task text
        cell_task = ws.cell(row_idx, task_col)
        cell_task.value = task_name
        cell_task.font = font_main if is_main else font_sub
        cell_task.alignment = align_left
        
        # Start date
        cell_s = ws.cell(row_idx, 6)
        cell_s.value = start_d
        cell_s.font = font_main if is_main else font_sub
        cell_s.alignment = align_center

        # End date
        cell_e = ws.cell(row_idx, 7)
        cell_e.value = end_d
        cell_e.font = font_main if is_main else font_sub
        cell_e.alignment = align_center

        # Responsibility
        cell_r = ws.cell(row_idx, 8)
        cell_r.value = resp
        cell_r.font = font_main if is_main else font_sub
        cell_r.alignment = align_center

        # Deliverable
        cell_del = ws.cell(row_idx, 9)
        cell_del.value = deliverable
        cell_del.font = font_main if is_main else font_sub
        cell_del.alignment = align_left

        # Status
        cell_stat = ws.cell(row_idx, 10)
        cell_stat.value = 'Done'
        cell_stat.font = font_done
        cell_stat.fill = fill_done
        cell_stat.alignment = align_center

        # Apply borders and background for metadata cols
        for c in range(2, 11):
            ws.cell(row_idx, c).border = thin_border
            if is_main and c != 10:
                ws.cell(row_idx, c).fill = fill_main

        # Fill Gantt chart columns (Day 1 = Col 11 ... Day 20 = Col 30)
        for d in range(1, 21):
            col_target = 10 + d
            cell_g = ws.cell(row_idx, col_target)
            cell_g.border = thin_border
            if d_start <= d <= d_end:
                cell_g.value = '■'
                cell_g.fill = fill_gantt_main if is_main else fill_gantt_sub
                cell_g.font = font_gantt
                cell_g.alignment = align_center
            else:
                cell_g.value = ''

    wb.save('SIC-final/Dou_RehabAI_Work_Breakdown_Structure.xlsx')
    print('Successfully polished and saved SIC-final/Dou_RehabAI_Work_Breakdown_Structure.xlsx!')

if __name__ == '__main__':
    polish_wbs()

