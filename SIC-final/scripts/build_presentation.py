import os
import pptx
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette
    C_NAVY = RGBColor(11, 34, 101)      # Samsung Navy #0B2265
    C_CYAN = RGBColor(0, 169, 224)     # Cyan Accent #00A9E0
    C_BLUE = RGBColor(0, 112, 210)     # Blue Accent #0070D2
    C_DARK = RGBColor(38, 50, 56)      # Slate Dark #263238
    C_MUTED = RGBColor(90, 107, 124)   # Gray #5A6B7C
    C_BG_CARD = RGBColor(244, 246, 249)# Soft card background #F4F6F9
    C_BORDER = RGBColor(208, 215, 222) # Light border #D0D7DE
    C_WHITE = RGBColor(255, 255, 255)
    C_GREEN = RGBColor(46, 125, 50)

    def add_header(slide, unit_text, title_text):
        # Unit tracker
        tb_unit = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
        p_u = tb_unit.text_frame.paragraphs[0]
        p_u.text = unit_text.upper()
        p_u.font.name = 'Segoe UI'
        p_u.font.size = Pt(10)
        p_u.font.bold = True
        p_u.font.color.rgb = C_CYAN

        # Title
        tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.6))
        p_t = tb_title.text_frame.paragraphs[0]
        p_t.text = title_text
        p_t.font.name = 'Segoe UI'
        p_t.font.size = Pt(20)
        p_t.font.bold = True
        p_t.font.color.rgb = C_NAVY

        # Accent Line
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.35), Inches(11.733), Inches(0.03))
        line.fill.solid()
        line.fill.fore_color.rgb = C_CYAN
        line.line.fill.background()

    def add_footer(slide, current_slide, total_slides=15):
        tb_f = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.733), Inches(0.35))
        tf = tb_f.text_frame
        p = tf.paragraphs[0]
        p.text = f'Team Dou · RehabAI: Hệ Thống Hỗ Trợ Phục Hồi Chức Năng Chi Trên   |   Slide {current_slide} of {total_slides}   |   Samsung Innovation Campus'
        p.alignment = PP_ALIGN.CENTER
        p.font.name = 'Segoe UI'
        p.font.size = Pt(9)
        p.font.color.rgb = C_MUTED

    def add_card(slide, left, top, width, height, title, items, bg_color=C_BG_CARD, border_color=C_BORDER, title_color=C_NAVY):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.2)

        tf = shape.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.2)
        tf.margin_right = Inches(0.2)
        tf.margin_top = Inches(0.18)
        tf.margin_bottom = Inches(0.18)

        if title:
            p_t = tf.paragraphs[0]
            p_t.text = title
            p_t.font.name = 'Segoe UI'
            p_t.font.size = Pt(12)
            p_t.font.bold = True
            p_t.font.color.rgb = title_color
            p_t.space_after = Pt(6)

        first = True if not title else False
        for item in items:
            p = tf.add_paragraph() if not first else tf.paragraphs[0]
            first = False
            p.text = item
            p.font.name = 'Segoe UI'
            p.font.size = Pt(9.5)
            p.font.color.rgb = C_DARK
            p.space_after = Pt(4)
        return shape

    # ================= SLIDE 1: COVER =================
    s1 = prs.slides.add_slide(blank_layout)
    
    # Left banner rectangle
    bg_left = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.4), Inches(7.5))
    bg_left.fill.solid()
    bg_left.fill.fore_color.rgb = C_NAVY
    bg_left.line.fill.background()

    # Branding header
    tb_b = s1.shapes.add_textbox(Inches(0.9), Inches(0.8), Inches(7.5), Inches(0.5))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.text = 'SAMSUNG INNOVATION CAMPUS  ·  AI CAPSTONE PROJECT'
    p_b.font.name = 'Segoe UI'
    p_b.font.size = Pt(12)
    p_b.font.bold = True
    p_b.font.color.rgb = C_CYAN

    # Main Title
    tb_title = s1.shapes.add_textbox(Inches(0.9), Inches(1.3), Inches(7.5), Inches(2.0))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    p_t1 = tf_title.paragraphs[0]
    p_t1.text = 'RehabAI: Hệ Thống Hỗ Trợ Theo Dõi &\nĐánh Giá Bài Tập Phục Hồi Chức Năng Chi Trên'
    p_t1.font.name = 'Segoe UI'
    p_t1.font.size = Pt(26)
    p_t1.font.bold = True
    p_t1.font.color.rgb = C_NAVY

    # Subtitle
    tb_sub = s1.shapes.add_textbox(Inches(0.9), Inches(3.4), Inches(7.0), Inches(1.1))
    tf_sub = tb_sub.text_frame
    tf_sub.word_wrap = True
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = 'RehabAI: Upper-Limb Rehabilitation Exercise Monitoring and Evaluation Support System with Real-Time Landmark Tracking & Safe AI Coaching'
    p_sub.font.name = 'Segoe UI'
    p_sub.font.size = Pt(12)
    p_sub.font.color.rgb = C_DARK

    # Metadata card
    meta_box = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(4.7), Inches(6.6), Inches(1.8))
    meta_box.fill.solid()
    meta_box.fill.fore_color.rgb = C_BG_CARD
    meta_box.line.color.rgb = C_BORDER
    tf_m = meta_box.text_frame
    tf_m.margin_left = Inches(0.25)
    tf_m.margin_top = Inches(0.2)
    
    pm1 = tf_m.paragraphs[0]
    pm1.text = 'Team Dou  |  AI Course 2025-2026'
    pm1.font.name = 'Segoe UI'
    pm1.font.size = Pt(11)
    pm1.font.bold = True
    pm1.font.color.rgb = C_NAVY
    pm1.space_after = Pt(4)

    pm2 = tf_m.add_paragraph()
    pm2.text = '• Đàm Đức Lương — Lead AI & Fullstack Developer\n• Ngô Quang Minh — ML Researcher & Documentation Lead'
    pm2.font.name = 'Segoe UI'
    pm2.font.size = Pt(10)
    pm2.font.color.rgb = C_DARK
    pm2.space_after = Pt(4)

    pm3 = tf_m.add_paragraph()
    pm3.text = 'Date of Submission: 07/11/2026   |   Strict 10-Fold LOSO Verified'
    pm3.font.name = 'Segoe UI'
    pm3.font.size = Pt(9.5)
    pm3.font.color.rgb = C_MUTED

    # Hero image on right
    img_hero = 'SIC-final/assets/hero_companion.png'
    if os.path.exists(img_hero):
        s1.shapes.add_picture(img_hero, Inches(7.8), Inches(1.1), Inches(4.8), Inches(5.4))

    # ================= SLIDE 2: PROBLEM & MOTIVATION =================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, '01 · Introduction', 'Post-Stroke Rehabilitation: Clinical Reality & Systemic Bottlenecks')
    add_footer(s2, 2)

    # 4 Cards on left/center
    c_w = Inches(3.6)
    c_h = Inches(2.5)
    
    add_card(s2, Inches(0.8), Inches(1.6), c_w, c_h, '1. High Stroke Incidence & Disability', [
        '• Over 12 million new stroke incidents worldwide each year; leading cause of adult disability.',
        '• In Vietnam, ~200,000 cases annually; over 80% suffer persistent upper-limb motor deficits.',
        '• Effective motor recovery requires hundreds of repetitive movements daily to drive neuroplasticity.'
    ])

    add_card(s2, Inches(4.7), Inches(1.6), c_w, c_h, '2. Acute Therapist Shortages & Travel Cost', [
        '• Therapist-to-patient ratio exceeds 1:50 in public hospitals and provincial health centers.',
        '• Patients endure severe travel fatigue and travel expenses traveling to specialized therapy clinics.',
        '• Inability to receive daily one-on-one professional guidance once discharged.'
    ])

    add_card(s2, Inches(0.8), Inches(4.3), c_w, c_h, '3. Alarming Non-Compliance & Dropout', [
        '• Studies show >60% of stroke patients abandon prescribed home exercises within 6 months.',
        '• Root causes: lack of real-time correctness feedback, absence of tracking, and uncertainty.',
        '• Compensatory movement errors often go uncorrected, leading to suboptimal recovery.'
    ])

    add_card(s2, Inches(4.7), Inches(4.3), c_w, c_h, '4. Barrier of Specialized Sensor Systems', [
        '• Traditional tele-rehab hardware depends on wearable IMU sensors or cyber-gloves ($1,000s+).',
        '• Cumbersome to don independently for patients with hemiplegia / single-hand paralysis.',
        '• High hardware cost severely restricts home accessibility.'
    ])

    # Core Opportunity Box on right
    callout_box = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.6), Inches(1.6), Inches(3.9), Inches(5.2))
    callout_box.fill.solid()
    callout_box.fill.fore_color.rgb = RGBColor(235, 243, 250)
    callout_box.line.color.rgb = C_CYAN
    callout_box.line.width = Pt(1.5)
    tf_co = callout_box.text_frame
    tf_co.margin_left = Inches(0.25)
    tf_co.margin_right = Inches(0.25)
    tf_co.margin_top = Inches(0.3)
    
    p_co_t = tf_co.paragraphs[0]
    p_co_t.text = 'THE REHABAI SOLUTION'
    p_co_t.font.name = 'Segoe UI'
    p_co_t.font.size = Pt(13)
    p_co_t.font.bold = True
    p_co_t.font.color.rgb = C_NAVY
    p_co_t.space_after = Pt(8)

    co_bullets = [
        'Democratizing Care: Convert any standard RGB webcam or laptop camera into an intelligent rehabilitation coach.',
        'Zero Sensors Required: 100% contactless perception using MediaPipe Holistic skeletal & dual-hand tracking.',
        'Objective Telemetry: Automatic repetition counting via biomechanical finite state machines.',
        'Safe AI Companion: Bilingual conversational assistant with emergency symptom guardrails.',
        'Accessible Recovery: Empowering stroke survivors to practice evidence-based exercises in their living room.'
    ]
    for b in co_bullets:
        p = tf_co.add_paragraph()
        p.text = f'✓ {b}'
        p.font.name = 'Segoe UI'
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_DARK
        p.space_after = Pt(8)

    # ================= SLIDE 3: OBJECTIVES =================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, '01 · Introduction', 'RehabAI Core Objectives & Value Proposition')
    add_footer(s3, 3)

    obj_cards = [
        ('1. Contactless Skeletal Perception', [
            '• Extract 33 pose landmarks and 42 hand keypoints using MediaPipe Holistic.',
            '• Operate reliably on standard consumer webcams (640x480 @ 15-30 FPS).',
            '• Zero wearable sensors or specialized mocap hardware required.'
        ]),
        ('2. Spatiotemporal Movement Classification', [
            '• Recognize 4 clinically essential upper-limb rehabilitation movements.',
            '• Multi-Stream RehabMotionNet v2 combining graph, conv1D, and temporal layers.',
            '• Ingestion of full 96-frame spatiotemporal movement trajectories.'
        ]),
        ('3. Biomechanical Repetition Counting', [
            '• Track joint angles and angular velocities in real time.',
            '• Deterministic Finite State Machine (FSM) detecting complete extension peaks.',
            '• Filter out false triggers and provide immediate repetition feedback.'
        ]),
        ('4. Two-Layer Telehealth Platform', [
            '• Public informational website for stroke education, FAQ, and safety precautions.',
            '• Protected clinical exercise room (/app) accessible only with user authentication.',
            '• SQLite database storing session UUIDs, reps, and VAS pain ratings.'
        ]),
        ('5. Clinical AI Assistant with Guardrails', [
            '• Friendly bilingual conversational support in Vietnamese and English.',
            '• Deterministic interception of red-flag symptoms (chest pain, acute numbness).',
            '• Strict refusal of unsupported medical or diagnostic claims.'
        ]),
        ('6. Methodological Rigor & Anti-Leakage', [
            '• Eliminate artificial 100% legacy artifact claims.',
            '• Strict 10-fold Leave-One-Subject-Out (LOSO) cross-validation on real patients.',
            '• Fully transparent reporting of genuine generalization boundaries.'
        ])
    ]

    for idx, (title, items) in enumerate(obj_cards):
        col = idx % 3
        row = idx // 3
        left = Inches(0.8 + col * 3.95)
        top = Inches(1.6 + row * 2.65)
        add_card(s3, left, top, Inches(3.8), Inches(2.45), title, items)

    # ================= SLIDE 4: SYSTEM ARCHITECTURE =================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, '02 · Project Execution', 'Fullstack Multi-Tiered System Architecture')
    add_footer(s4, 4)

    img_arch = 'SIC-final/assets/fig1_system_architecture.png'
    if os.path.exists(img_arch):
        s4.shapes.add_picture(img_arch, Inches(0.8), Inches(1.5), Inches(7.5), Inches(5.3))

    arch_tiers = [
        ('Client Layer (React 19 + Vite)', [
            '• Captures 640x480 webcam video throttled at 15 FPS.',
            '• Canvas skeletal overlay rendering real-time pose.',
            '• Visual repetition progress bar & VAS pain slider.'
        ]),
        ('Feature Engine & Normalization', [
            '• MediaPipe Holistic extracting 33 pose + 42 hand joints.',
            '• Spatial origin translation to mid-shoulder midpoint.',
            '• Euclidean shoulder-width scaling for distance invariance.'
        ]),
        ('Inference Core (TorchScript)', [
            '• RehabMotionNet v2 (451k parameters, 1.82 MiB).',
            '• C++ compiled TorchScript executing in <45 ms.',
            '• Ingests (Batch, 96 frames, 237 dimensions) motion tensors.'
        ]),
        ('Safety & Persistence (FastAPI + SQLite)', [
            '• Real-time full-duplex WebSocket communication.',
            '• Kinematic FSM repetition counter & quality gating.',
            '• Guardrailed AI Assistant + SQLite session persistence.'
        ])
    ]

    for idx, (title, items) in enumerate(arch_tiers):
        top = Inches(1.5 + idx * 1.35)
        add_card(s4, Inches(8.55), top, Inches(3.98), Inches(1.25), title, items)

    # ================= SLIDE 5: DATASET & QUALITY GATE =================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, '02 · Project Execution', 'Dataset Curation & Quality Gate Verification')
    add_footer(s5, 5)

    img_data = 'SIC-final/assets/fig2_dataset_analysis.png'
    if os.path.exists(img_data):
        s5.shapes.add_picture(img_data, Inches(0.8), Inches(1.5), Inches(8.0), Inches(5.3))

    add_card(s5, Inches(9.0), Inches(1.5), Inches(3.53), Inches(5.3), 'Data Governance & Audit', [
        'Authentic Patient Cohort:',
        '• Recorded from 10 distinct post-stroke patients (Sub 01 through Sub 10).',
        '• Raw inventory: 491 video recordings under diverse domestic environments.\n',
        'Strict Quality Gate Audit:',
        '• Filtered out frames with landmark visibility < 0.6 on key arm joints.',
        '• Pruned 104 samples (21.2%) suffering severe tracking dropouts or occlusions.',
        '• Retained 387 verified samples (78.8% yield) for training and evaluation.\n',
        'Class Representation (387 total):',
        '• Ex 1: Shoulder Elevation — 123 (31.8%)',
        '• Ex 2: Elbow Extension — 65 (16.8%)',
        '• Ex 3: Wrist Flexion/Ext — 104 (26.9%)',
        '• Ex 4: Hand Opening — 95 (24.6%)\n',
        'Clinical Completion Reality:',
        '• Complete: 187 (48.3%) | Incomplete: 200 (51.7%), reflecting authentic impairment.'
    ])

    # ================= SLIDE 6: KINEMATICS PIPELINE =================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, '02 · Project Execution', 'Landmark Extraction, Normalization & Kinematics')
    add_footer(s6, 6)

    img_kin = 'SIC-final/assets/fig5_kinematics_pipeline.png'
    if os.path.exists(img_kin):
        s6.shapes.add_picture(img_kin, Inches(0.8), Inches(1.5), Inches(7.6), Inches(5.3))

    add_card(s6, Inches(8.65), Inches(1.5), Inches(3.88), Inches(5.3), 'Feature Contract: 237 Dimensions', [
        '1. Spatial Origin Normalization:',
        '• Anchored to 3D midpoint of left and right shoulders:',
        '  P_mid = (P_L_shoulder + P_R_shoulder) / 2',
        '  P_centered = P_raw - P_mid\n',
        '2. Scale & Distance Invariance:',
        '• Divided by Euclidean shoulder span distance:',
        '  P_norm = P_centered / ||P_L_sh - P_R_sh||_2',
        '• Guarantees identical feature scale whether user sits 1m or 2.5m away.\n',
        '3. 12 Biomechanical Kinematics:',
        '• Shoulder abduction/adduction angles (L/R)',
        '• Elbow flexion/extension angles (L/R)',
        '• Trunk inclination relative to vertical axis',
        '• Respective joint angular velocities (dθ/dt)',
        '• Bilateral wrist linear displacement velocities\n',
        '4. Motion Tensor Composition (96 x 237):',
        '• Pose (99) + Hand (126) + Kinematics (12) = 237 features across 96 temporal frames.'
    ])

    # ================= SLIDE 7: REHABMOTIONNET ARCHITECTURE =================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, '02 · Project Execution', 'RehabMotionNet v2: Multi-Stream Spatiotemporal Network')
    add_footer(s7, 7)

    arch_cards = [
        ('1. Upper-Limb PoseGraph Branch', [
            '• Input: 6 anatomical landmarks (bilateral shoulders, elbows, wrists).',
            '• Lightweight spatial graph convolutions preserving skeletal connectivity.',
            '• Focuses on macro upper-limb reaching and elevation geometry.'
        ]),
        ('2. Dual-Hand Conv1D Branch', [
            '• Input: 42 hand keypoints (126 spatial coordinates) across time.',
            '• 1D temporal convolutions extracting subtle finger flexion & extension.',
            '• Vital for distinguishing hand opening from broad arm movement.'
        ]),
        ('3. Multi-Scale TCN (MS-TCN)', [
            '• Dilated temporal convolutions with dilation factors d = 1, 2, 4.',
            '• Residual skip connections across hierarchical temporal receptive fields.',
            '• Captures micro-tremors, sub-movement phases, and macro-repetition rhythms.'
        ]),
        ('4. Attention Pooling & TorchScript', [
            '• Dynamic learned attention assigns high weights to peak extension frames.',
            '• Downweights resting and transition periods.',
            '• Compiled into TorchScript C++ artifact (1.82 MiB, 451k parameters) for <45ms execution.'
        ])
    ]

    for idx, (title, items) in enumerate(arch_cards):
        col = idx % 2
        row = idx // 2
        left = Inches(0.8 + col * 5.95)
        top = Inches(1.6 + row * 2.65)
        add_card(s7, left, top, Inches(5.8), Inches(2.45), title, items)

    # ================= SLIDE 8: 10-FOLD LOSO BENCHMARK =================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, '03 · Results & Evaluation', 'Strict 10-Fold LOSO Benchmark Across Evaluated Models')
    add_footer(s8, 8)

    img_bench = 'SIC-final/assets/fig3_model_benchmark.png'
    if os.path.exists(img_bench):
        s8.shapes.add_picture(img_bench, Inches(0.8), Inches(1.5), Inches(7.5), Inches(5.3))

    add_card(s8, Inches(8.55), Inches(1.5), Inches(3.98), Inches(5.3), 'Benchmarking on Real Patients', [
        'Strict 10-Fold LOSO Protocol:',
        '• Each fold holds out 1 subject strictly for testing, 1 for validation, 8 for training.',
        '• Zero subject overlap between train and test splits.',
        '• Normalization statistics fitted strictly on training partition.\n',
        'Model Comparison (Macro-F1 / Accuracy):',
        '• Majority Baseline: 5.47% F1 / 15.15% Acc',
        '• Multilayer Perceptron: 27.79% F1 / 34.51% Acc',
        '• Linear SVM: 28.80% F1 / 36.51% Acc',
        '• LSTM (Recurrent): 32.45% F1 / 39.96% Acc',
        '• RehabMotionNet v2: 35.44% F1 / 43.79% Acc (Production)',
        '• Optimized-v1: 39.45% F1 / 48.37% Acc (Research)\n',
        'Scientific Integrity:',
        '• Discarded artificial 100% legacy artifact claims.',
        '• Reports authentic generalization on unseen stroke patients with wide inter-subject variance (±23.35%).'
    ])

    # ================= SLIDE 9: CONFUSION MATRIX & ERROR ANALYSIS =================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, '03 · Results & Evaluation', '10-Fold Confusion Matrix & Movement Error Patterns')
    add_footer(s9, 9)

    img_cm = 'SIC-final/assets/fig4_confusion_matrix.png'
    if os.path.exists(img_cm):
        s9.shapes.add_picture(img_cm, Inches(0.8), Inches(1.5), Inches(7.5), Inches(5.3))

    add_card(s9, Inches(8.55), Inches(1.5), Inches(3.98), Inches(5.3), 'Clinical Error Analysis', [
        'Per-Class Normalized Recall Rates:',
        '• Exercise 3 (Wrist Flex/Ext): 66.35% (69/104)',
        '  Strong forearm rotation and wrist angle signatures.',
        '• Exercise 2 (Elbow Extension): 55.38% (36/65)',
        '  Good separation; confused with Ex 1 when shoulder rises.',
        '• Exercise 1 (Shoulder Elevation): 46.34% (57/123)',
        '  Compensatory movement leads to confusion with Ex 4.',
        '• Exercise 4 (Hand Opening): 37.89% (36/95)',
        '  Subtle finger displacements; confused with Ex 1 and Ex 3.\n',
        'Clinical Neurorehabilitation Insights:',
        '• Stroke Abnormal Synergies: Patients attempting shoulder elevation frequently experience involuntary finger splay, generating dual movement cues.',
        '• Resolution Strategy: Multi-task loss and separate finger-to-palm distance tracking resolve ambiguity.'
    ])

    # ================= SLIDE 10: ABLATION STUDY & ETHICAL AI =================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, '03 · Results & Evaluation', 'Ablation Insights & Ethical AI Decisions')
    add_footer(s10, 10)

    img_abl = 'SIC-final/assets/fig6_ablation_study.png'
    if os.path.exists(img_abl):
        s10.shapes.add_picture(img_abl, Inches(0.8), Inches(1.5), Inches(7.5), Inches(5.3))

    add_card(s10, Inches(8.55), Inches(1.5), Inches(3.98), Inches(5.3), 'Component Value & Safety Gating', [
        'Ablation Experiment Takeaways:',
        '• Hand Branch is Critical: Removing Hand Conv1D drops Macro-F1 from 35.44% to 28.11% (-7.33%) and Accuracy from 43.79% to 35.79% (-8.00%). Hand features are non-negotiable.',
        '• Kinematics Stream: Provides a +1.79% F1 stabilization to noisy raw coordinates.',
        '• MS-TCN vs Overfitting: SimCLR pretraining and complex attention showed slight overfitting on small cohorts, prompting the streamlined Optimized-v1 variant.\n',
        'Ethical Gating of Completion Head:',
        '• Auxiliary binary completion head achieved only 50.24% accuracy (random coin-flip level).',
        '• Decision: Responsibly excluded from production to avoid misleading vulnerable patients.',
        '• Solution: Repetition tracking is governed by verified kinematic FSM peak-detection logic.'
    ])

    # ================= SLIDE 11: TWO-LAYER SECURITY & SAFETY =================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, '03 · Results & Evaluation', 'Two-Layer Security Architecture & Clinical Boundaries')
    add_footer(s11, 11)

    img_sec = 'SIC-final/assets/fig8_two_layer_security.png'
    if os.path.exists(img_sec):
        s11.shapes.add_picture(img_sec, Inches(0.8), Inches(1.5), Inches(7.5), Inches(5.3))

    add_card(s11, Inches(8.55), Inches(1.5), Inches(3.98), Inches(5.3), 'Clinical Safety Guardrails', [
        'Public Informational Portal (/):',
        '• Static stroke recovery guides, FAQ, and tutorials.',
        '• Zero webcam access, zero AI inference.',
        '• Zero database write transactions.\n',
        'Protected Telehealth Suite (/app):',
        '• Requires explicit user authentication and consent.',
        '• Real-time WebSocket skeletal tracking and rep counter.',
        '• VAS pain logger (0-10) before and after exercises.\n',
        'Bilingual AI Coach Clinical Guardrails:',
        '• Red-Flag Interception: Detects emergency keywords ("đau ngực", "tê liệt đột ngột", "chest tightness") and triggers emergency medical protocols.',
        '• Refusal of Diagnosis: Explicitly refuses diagnostic claims; reinforces physician authority.',
        '• Local Rule-Based Fallback: Operates deterministically without cloud dependency.'
    ])

    # ================= SLIDE 12: INTERACTIVE WEB APPLICATION =================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, '03 · Results & Evaluation', 'Fullstack Interactive Application & User Experience')
    add_footer(s12, 12)

    img_ui = 'SIC-final/assets/ui_homepage.png'
    if os.path.exists(img_ui):
        s12.shapes.add_picture(img_ui, Inches(0.8), Inches(1.5), Inches(7.5), Inches(5.3))

    add_card(s12, Inches(8.55), Inches(1.5), Inches(3.98), Inches(5.3), 'Patient-Centric Telehealth UX', [
        'Real-Time Visual Feedback:',
        '• Live HTML5 canvas skeletal stick-figure overlaid directly onto the 640x480 webcam feed.',
        '• Instant visual indicators for landmark tracking quality (>60% threshold warning).\n',
        'Biomechanical Repetition Tracker:',
        '• Circular progress ring and repetition counter incremented upon verified full extension.',
        '• Form warnings when compensatory shoulder elevation is detected.\n',
        'Clinical Session Lifecycle:',
        '• Pre-exercise VAS pain level survey (0 to 10 scale).',
        '• Post-exercise session completion summary with pain delta analysis and rest recommendations.',
        '• Synchronized session history charts displaying daily adherence and functional progress.'
    ])

    # ================= SLIDE 13: TRL ROADMAP =================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, '04 · Projected Impact', 'Technology Readiness Level (TRL) & Future Horizons')
    add_footer(s13, 13)

    img_trl = 'SIC-final/assets/fig7_trl_roadmap.png'
    if os.path.exists(img_trl):
        s13.shapes.add_picture(img_trl, Inches(0.8), Inches(1.5), Inches(7.6), Inches(5.3))

    add_card(s13, Inches(8.65), Inches(1.5), Inches(3.88), Inches(5.3), 'Advancing from TRL 5 to TRL 7-9', [
        'Current State: TRL 5 (Integrated Prototype)',
        '• Complete end-to-end web system validated on 387 verified patient samples in simulated setting.\n',
        'Short-Term (Next 3 Months — TRL 6):',
        '• Integrate rule-based neck stretch and deep breathing modules.',
        '• Execute pilot trials with a cohort of 20 stroke outpatients in rehabilitation centers in Hanoi.\n',
        'Mid-Term (6 - 12 Months — TRL 7):',
        '• Multi-center clinical dataset expansion to 50+ patients across mild, moderate, and severe stroke.',
        '• Mobile app development (React Native / Flutter with on-device CoreML / TFLite).\n',
        'Long-Term (12 - 24 Months — TRL 8-9):',
        '• Formal randomized controlled trials (RCTs).',
        '• Correlation with clinical Fugl-Meyer assessment scores.',
        '• Medical device software certification and hospital EHR integration.'
    ])

    # ================= SLIDE 14: PROJECT MANAGEMENT =================
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, '05 · Management & Conclusion', 'Project Management, WBS Execution & Team Roles')
    add_footer(s14, 14)

    # 4-week WBS Banner across top
    wbs_banner = s14.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(11.733), Inches(1.3))
    wbs_banner.fill.solid()
    wbs_banner.fill.fore_color.rgb = C_BG_CARD
    wbs_banner.line.color.rgb = C_BORDER
    tf_w = wbs_banner.text_frame
    tf_w.margin_left = Inches(0.2)
    tf_w.margin_top = Inches(0.12)
    pw_t = tf_w.paragraphs[0]
    pw_t.text = 'FOUR-WEEK CAPSTONE EXECUTION TIMELINE (100% MILESTONES COMPLETED)'
    pw_t.font.name = 'Segoe UI'
    pw_t.font.size = Pt(11)
    pw_t.font.bold = True
    pw_t.font.color.rgb = C_NAVY
    pw_t.space_after = Pt(4)
    pw_b = tf_w.add_paragraph()
    pw_b.text = '• Week 1: Problem Scoping, 491-Video Dataset Audit & Quality Gate   →   • Week 2: MediaPipe Feature Contract & Strict 10-Fold LOSO Splits\n• Week 3: RehabMotionNet v2, TorchScript & React 19 WebSocket Engine   →   • Week 4: 144 Test Cases, Latency QA & Capstone Final Documentation'
    pw_b.font.name = 'Segoe UI'
    pw_b.font.size = Pt(9.5)
    pw_b.font.color.rgb = C_DARK

    # Member Role Cards below
    add_card(s14, Inches(0.8), Inches(3.0), Inches(5.7), Inches(3.8), 'Đàm Đức Lương — Lead AI & Fullstack Developer', [
        'Core Technical Contributions:',
        '• Designed Multi-Stream RehabMotionNet v2 neural architecture.',
        '• Implemented MediaPipe extraction, mid-shoulder normalization, and 12-kinematics stream.',
        '• Exported PyTorch weights to optimized C++ TorchScript artifact (1.82 MiB).',
        '• Built high-performance asynchronous WebSocket inference engine in FastAPI (<45 ms latency).',
        '• Developed React 19 interactive frontend, HTML5 canvas skeletal renderer, and session flow.',
        '• Constructed automated test suite (144 pytest unit and integration tests) and Docker bundles.'
    ])

    add_card(s14, Inches(6.8), Inches(3.0), Inches(5.733), Inches(3.8), 'Ngô Quang Minh — ML Researcher & Documentation Lead', [
        'Core Research & Governance Contributions:',
        '• Audited 491 raw video recordings; designed landmark confidence and continuity quality gates.',
        '• Curated the verified 387-sample evaluation dataset and established SHA-256 provenance manifests.',
        '• Designed the 10-fold Leave-One-Subject-Out (LOSO) split matrix to eliminate patient leakage.',
        '• Conducted classical baseline benchmarks (SVM, MLP, LSTM) and extensive ablation experiments.',
        '• Authored clinical safety guardrail heuristics and emergency triage rules for the AI Coach.',
        '• Led official Capstone deliverables: Action Plan, WBS Gantt workbook, Presentation, and Final Report.'
    ])

    # ================= SLIDE 15: CONCLUSION & QA =================
    s15 = prs.slides.add_slide(blank_layout)
    add_header(s15, '05 · Management & Conclusion', 'Empowering Neurorehabilitation Through Responsible AI')
    add_footer(s15, 15)

    add_card(s15, Inches(0.8), Inches(1.6), Inches(6.5), Inches(5.2), 'Summary of Project Achievements', [
        '1. Demolished the Hardware Barrier:',
        '• Contactless tele-rehabilitation utilizing standard RGB webcams, eliminating expensive wearable gloves.\n',
        '2. Uncompromised Scientific Methodology:',
        '• Refused artificial 100% claims; established strict 10-fold LOSO benchmark on 387 verified stroke samples (43.8% Acc / 35.4% F1).\n',
        '3. Production-Grade System Architecture:',
        '• Fullstack interactive platform with <45 ms latency, 144 automated tests, and Docker deployment.\n',
        '4. Clinical-Safety-First Design:',
        '• Two-layer zone isolation and deterministic emergency red-flag interception.\n',
        '5. Clear Path to Healthcare Impact:',
        '• Documented TRL roadmap advancing from TRL 5 prototype to certified clinical deployment.'
    ])

    # Thank you card on right
    ty_box = s15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.6), Inches(1.6), Inches(4.933), Inches(5.2))
    ty_box.fill.solid()
    ty_box.fill.fore_color.rgb = C_NAVY
    ty_box.line.color.rgb = C_CYAN
    ty_box.line.width = Pt(2.0)
    tf_ty = ty_box.text_frame
    tf_ty.margin_left = Inches(0.35)
    tf_ty.margin_top = Inches(0.4)

    pty1 = tf_ty.paragraphs[0]
    pty1.text = 'THANK YOU!'
    pty1.font.name = 'Segoe UI'
    pty1.font.size = Pt(28)
    pty1.font.bold = True
    pty1.font.color.rgb = C_WHITE
    pty1.space_after = Pt(12)

    pty2 = tf_ty.add_paragraph()
    pty2.text = 'Samsung Innovation Campus Evaluation Panel'
    pty2.font.name = 'Segoe UI'
    pty2.font.size = Pt(13)
    pty2.font.bold = True
    pty2.font.color.rgb = C_CYAN
    pty2.space_after = Pt(20)

    pty3 = tf_ty.add_paragraph()
    pty3.text = 'Team Dou — Capstone Project'
    pty3.font.name = 'Segoe UI'
    pty3.font.size = Pt(12)
    pty3.font.bold = True
    pty3.font.color.rgb = C_WHITE
    pty3.space_after = Pt(4)

    pty4 = tf_ty.add_paragraph()
    pty4.text = '• Đàm Đức Lương  |  damducluong@example.com\n• Ngô Quang Minh  |  ngoquangminh@example.com'
    pty4.font.name = 'Segoe UI'
    pty4.font.size = Pt(10.5)
    pty4.font.color.rgb = RGBColor(220, 230, 242)
    pty4.space_after = Pt(24)

    pty5 = tf_ty.add_paragraph()
    pty5.text = 'Questions & Discussion'
    pty5.font.name = 'Segoe UI'
    pty5.font.size = Pt(16)
    pty5.font.bold = True
    pty5.font.color.rgb = C_CYAN
    pty5.space_after = Pt(6)

    pty6 = tf_ty.add_paragraph()
    pty6.text = 'We warmly welcome questions, feedback, and technical critique from the instructors and evaluation committee.'
    pty6.font.name = 'Segoe UI'
    pty6.font.size = Pt(10)
    pty6.font.color.rgb = RGBColor(200, 215, 230)

    output_path = 'SIC-final/Dou_RehabAI_Presentation.pptx'
    prs.save(output_path)
    print(f'Successfully generated {output_path} with 15 rich slides!')

if __name__ == '__main__':
    create_presentation()

