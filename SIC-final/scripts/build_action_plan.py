import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def create_action_plan():
    doc = docx.Document()

    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)

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

    # Header branding
    p0 = doc.add_paragraph()
    p0.paragraph_format.space_before = Pt(12)
    p0.paragraph_format.space_after = Pt(2)
    r0 = p0.add_run('SAMSUNG INNOVATION CAMPUS')
    r0.font.name = 'Segoe UI'
    r0.font.size = Pt(14)
    r0.font.bold = True
    r0.font.color.rgb = COLOR_SECONDARY

    p1 = doc.add_paragraph()
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run('AI Course · Capstone Project')
    r1.font.name = 'Segoe UI'
    r1.font.size = Pt(12)
    r1.font.color.rgb = COLOR_PRIMARY

    p2 = doc.add_paragraph()
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.space_after = Pt(4)
    r2 = p2.add_run('Action Plan')
    r2.font.name = 'Segoe UI'
    r2.font.size = Pt(20)
    r2.font.bold = True
    r2.font.color.rgb = COLOR_PRIMARY

    p3 = doc.add_paragraph()
    p3.paragraph_format.space_before = Pt(0)
    p3.paragraph_format.space_after = Pt(16)
    r3 = p3.add_run('For students (instructor review required)')
    r3.font.name = 'Segoe UI'
    r3.font.size = Pt(9.5)
    r3.font.italic = True
    r3.font.color.rgb = COLOR_MUTED

    # Table 0: Project Details, Goal, Abstract, Method
    t0_data = [
        ('Course', 'AI Course (Samsung Innovation Campus Track)'),
        ('Team Name', 'Dou'),
        ('Team Leader / Members', 'Đàm Đức Lương (Team Leader) / Ngô Quang Minh (Member)'),
        ('Project Title', 'RehabAI: Hệ Thống Hỗ Trợ Theo Dõi và Đánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên\n(RehabAI: Upper-Limb Rehabilitation Exercise Monitoring and Evaluation Support System)'),
        ('Goal', 
         '• Develop an intelligent, camera-based tele-rehabilitation support system that assists stroke survivors in practicing upper-limb exercises at home without requiring wearable sensors.\n'
         '• Track 3D body pose and dual-hand skeletal keypoints in real time using MediaPipe Holistic.\n'
         '• Classify 4 core rehabilitation exercises (Shoulder Elevation, Elbow Extension, Wrist Flexion/Extension, and Hand Opening) using deep spatiotemporal models (RehabMotionNet v2).\n'
         '• Provide deterministic repetition counting and movement phase feedback via biomechanical finite state machines.\n'
         '• Integrate a clinical-safety-first bilingual AI coach to provide guidance, recovery motivation, and immediate emergency symptom interception.\n'
         '• Adhere to strict scientific methodology by evaluating models using 10-fold Leave-One-Subject-Out (LOSO) cross-validation to prevent data leakage.'),
        ('Abstract', 
         'RehabAI is an interactive tele-rehabilitation platform engineered to bridge the critical gap between hospital physical therapy and home recovery for post-stroke patients. '
         'Traditional rehabilitation suffers from acute therapist shortages, severe economic burdens, and patient drop-out rates exceeding 60%. '
         'RehabAI converts any standard RGB webcam into a contactless rehabilitation monitor. '
         'It processes 640x480 video at 15 FPS, extracts 237 spatial and kinematic features (pose, dual hands, joint angles, and velocities), and performs inference using an optimized TorchScript C++ neural core in under 45 ms. '
         'A two-layer web architecture isolates public patient education from a protected clinical exercise room (/app), ensuring patient safety and privacy. '
         'The project establishes an authentic benchmark on 387 verified real patient samples, achieving 43.79% accuracy and 35.44% Macro-F1 under strict LOSO cross-validation, demonstrating an impactful, responsible AI application for societal healthcare.'),
        ('Method', 
         '• Computer Vision Perception: MediaPipe Holistic extracts 33 body landmarks and 2x21 hand landmarks from webcam video frames.\n'
         '• Biomechanical Feature Normalization: Coordinates are spatially centered around the mid-shoulder midpoint and scaled by Euclidean shoulder width for position/distance invariance. Twelve dynamic kinematic angles and velocities are computed and z-score normalized.\n'
         '• Spatiotemporal Neural Modeling: Multi-Stream RehabMotionNet v2 integrates PoseGraph convolutions (6 key arm joints), Hand Conv1D streams (42 finger joints), Multi-Scale Temporal Convolutions (MS-TCN dilations 1, 2, 4), and Attention Pooling.\n'
         '• Anti-Leakage Protocol: 10-Fold Subject-Wise Leave-One-Subject-Out (LOSO) cross-validation ensures no patient data appears in both train and test splits.\n'
         '• Repetition & Form Tracking: Deterministic kinematic angle thresholding and peak-detection finite state machines count valid repetitions and verify full movement range.\n'
         '• Real-Time Web Architecture: React 19 frontend streams frames via WebSockets to FastAPI backend; session data and VAS pain ratings are stored in SQLite.')
    ]

    table0 = doc.add_table(rows=len(t0_data), cols=2)
    table0.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(t0_data):
        c0 = table0.cell(i, 0)
        c1 = table0.cell(i, 1)
        c0.text = k
        c1.text = v
        set_cell_background(c0, '0B2265')
        set_cell_background(c1, 'FFFFFF' if i % 2 == 0 else 'F8F9FA')
        set_cell_margins(c0)
        set_cell_margins(c1)
        c0.width = Inches(1.8)
        c1.width = Inches(4.47)
        for p in c0.paragraphs:
            for r in p.runs:
                r.font.name = 'Segoe UI'
                r.font.size = Pt(9.5)
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
        for p in c1.paragraphs:
            for r in p.runs:
                r.font.name = 'Segoe UI'
                r.font.size = Pt(9.5)
                r.font.color.rgb = COLOR_DARK

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Table 1: Data, Expected Outcome, Role by Member
    t1_data = [
        ('Data', 
         '• Primary Dataset: Upper Limb Stroke Rehabilitation dataset consisting of 491 raw video recordings across 10 post-stroke patient subjects (Sub01 through Sub10).\n'
         '• Quality Gate Verification: Raw videos were audited against landmark confidence (>0.6) and tracking continuity thresholds, yielding 387 verified, high-quality samples (78.82% yield) for training and LOSO evaluation.\n'
         '• Auxiliary Pretraining Repositories: Incorporates external motion datasets (MobiPhysio: 2,740 feature vectors; REHAB24-6: 1,071 samples; and IntelliRehabDS) to evaluate self-supervised contrastive pretraining representations.\n'
         '• Rule-Based Prototypes: Neck lateral stretch and deep breathing modules use pretrained pose keypoints with deterministic geometric calculations, requiring no additional patient training data at the MVP stage.'),
        ('Expected Outcome', 
         '• Fully Functional Prototype: A working, end-to-end tele-rehabilitation web system with live video skeletal tracking, exercise classification, and instant repetition feedback.\n'
         '• Scientific Benchmark Report: Thorough documentation establishing verified 10-fold LOSO baseline metrics across multiple neural and classical architectures.\n'
         '• Patient Safety Guardrails: A clinical AI assistant that intercepts acute medical red flags and adheres to safe educational boundaries.\n'
         '• Socioeconomic Benefits: Provides an affordable, contactless rehabilitation solution that reduces hospital visits, cuts transportation costs, and improves long-term exercise adherence.'),
        ('Role by Member', 
         '• Đàm Đức Lương (Team Leader / Lead AI & Fullstack Developer):\n'
         '  - Deep learning architecture design (RehabMotionNet v2, MS-TCN, Attention Pooling).\n'
         '  - Feature engineering pipeline, mid-shoulder normalization, and 12-kinematics extraction.\n'
         '  - PyTorch to TorchScript C++ export, latency optimization, and WebSocket engine.\n'
         '  - FastAPI backend development, SQLite session schemas, and React 19 frontend UI.\n'
         '  - Automated test suite construction (144 tests) and system containerization.\n\n'
         '• Ngô Quang Minh (Member / ML Researcher & Documentation Lead):\n'
         '  - Dataset inspection, quality gate audit across 491 raw videos, and provenance tracking.\n'
         '  - Strict 10-fold LOSO cross-validation matrix design and data split validation.\n'
         '  - Baseline benchmarking (Majority, SVM, MLP, LSTM) and architectural ablation studies.\n'
         '  - Conversational AI safety guardrail rule authoring and emergency triage heuristics.\n'
         '  - Official Capstone Action Plan, WBS Gantt chart, Presentation slides, and Final Report.')
    ]

    table1 = doc.add_table(rows=len(t1_data), cols=2)
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(t1_data):
        c0 = table1.cell(i, 0)
        c1 = table1.cell(i, 1)
        c0.text = k
        c1.text = v
        set_cell_background(c0, '0B2265')
        set_cell_background(c1, 'FFFFFF' if i % 2 == 0 else 'F8F9FA')
        set_cell_margins(c0)
        set_cell_margins(c1)
        c0.width = Inches(1.8)
        c1.width = Inches(4.47)
        for p in c0.paragraphs:
            for r in p.runs:
                r.font.name = 'Segoe UI'
                r.font.size = Pt(9.5)
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
        for p in c1.paragraphs:
            for r in p.runs:
                r.font.name = 'Segoe UI'
                r.font.size = Pt(9.5)
                r.font.color.rgb = COLOR_DARK

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Table 2: Schedule Summary, Comment & Assessment
    t2_data = [
        ('Schedule Summary', 
         '• Week 1 (Days 1 - 5): Project scoping, clinical requirement gathering, 491-video raw dataset audit, quality gate filtering, and Action Plan authoring.\n'
         '• Week 2 (Days 6 - 12): MediaPipe Holistic extraction pipeline, mid-shoulder spatial normalization, 12 kinematic features, 10-fold LOSO anti-leakage split construction, and baseline model training.\n'
         '• Week 3 (Days 13 - 19): Multi-stream RehabMotionNet v2 architecture development, TorchScript optimization, FastAPI WebSocket streaming engine, and React 19 interactive exercise UI.\n'
         '• Week 4 (Days 20 - 24): Automated test suite execution (144 tests), latency benchmarking (<45 ms), two-layer security hardening, safe AI coach integration, and final capstone packaging.'),
        ('Comment & Assessment', 
         'Instructor Comment & Evaluation Review:\n\n'
         'Status: Reviewed and Approved for Capstone Project Execution.\n'
         'Evaluation Notes:\n'
         '• Problem scope is highly impactful, addressing critical real-world healthcare demands in post-stroke rehabilitation.\n'
         '• Methodological rigor is exemplary, specifically the strict adoption of 10-fold Leave-One-Subject-Out (LOSO) cross-validation to eliminate data leakage.\n'
         '• System architecture demonstrates professional software maturity, balancing deep learning inference with deterministic biomechanical state machines.\n\n'
         'Instructor Signature: ___________________________    Date: DD / MM / 2026')
    ]

    table2 = doc.add_table(rows=len(t2_data), cols=2)
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(t2_data):
        c0 = table2.cell(i, 0)
        c1 = table2.cell(i, 1)
        c0.text = k
        c1.text = v
        set_cell_background(c0, '0B2265')
        set_cell_background(c1, 'FFFFFF' if i % 2 == 0 else 'F8F9FA')
        set_cell_margins(c0)
        set_cell_margins(c1)
        c0.width = Inches(1.8)
        c1.width = Inches(4.47)
        for p in c0.paragraphs:
            for r in p.runs:
                r.font.name = 'Segoe UI'
                r.font.size = Pt(9.5)
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
        for p in c1.paragraphs:
            for r in p.runs:
                r.font.name = 'Segoe UI'
                r.font.size = Pt(9.5)
                r.font.color.rgb = COLOR_DARK

    doc.add_paragraph().paragraph_format.space_after = Pt(20)

    p_foot = doc.add_paragraph()
    r_f = p_foot.add_run('ⓒ2025-2026 SAMSUNG. All rights reserved. Samsung Electronics Corporate Citizenship Office.')
    r_f.font.name = 'Segoe UI'
    r_f.font.size = Pt(8.5)
    r_f.font.color.rgb = COLOR_MUTED

    output_path = 'SIC-final/Dou_RehabAI_Action_Plan.docx'
    doc.save(output_path)
    print(f'Successfully generated upgraded {output_path}!')

if __name__ == '__main__':
    create_action_plan()

