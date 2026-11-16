from __future__ import annotations

from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "REHABAI_BAO_CAO_TOAN_BO_DU_AN.docx"


def run(text: str) -> str:
    return escape(text).replace("\n", "<w:br/>")


def p(text: str = "", style: str = "Normal", bold: bool = False) -> str:
    rpr = f"<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r>{rpr}<w:t xml:space="preserve">{run(text)}</w:t></w:r></w:p>'


def heading(text: str, level: int = 1) -> str:
    return p(text, f"Heading{level}")


def bullet(text: str) -> str:
    return f'<w:p><w:pPr><w:pStyle w:val="ListBullet"/></w:pPr><w:r><w:t xml:space="preserve">{run(text)}</w:t></w:r></w:p>'


def table(rows: list[list[str]], widths: list[int] | None = None) -> str:
    widths = widths or [2600] * len(rows[0])
    out = ['<w:tbl><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:color="B7C2D0"/><w:left w:val="single" w:sz="4" w:color="B7C2D0"/><w:bottom w:val="single" w:sz="4" w:color="B7C2D0"/><w:right w:val="single" w:sz="4" w:color="B7C2D0"/><w:insideH w:val="single" w:sz="4" w:color="D8DEE8"/><w:insideV w:val="single" w:sz="4" w:color="D8DEE8"/></w:tblBorders></w:tblPr>']
    for ri, row in enumerate(rows):
        out.append("<w:tr>")
        for ci, cell in enumerate(row):
            shade = '<w:shd w:fill="EAF0F8"/>' if ri == 0 else ""
            bold = "<w:b/>" if ri == 0 else ""
            out.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[ci]}" w:type="dxa"/>{shade}</w:tcPr><w:p><w:r><w:rPr>{bold}</w:rPr><w:t xml:space="preserve">{run(cell)}</w:t></w:r></w:p></w:tc>')
        out.append("</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def document_body() -> str:
    b: list[str] = []
    b.append(p("BÁO CÁO TOÀN BỘ DỰ ÁN REHABAI", "Title"))
    b.append(p("Hệ thống hỗ trợ phục hồi chức năng vận động bằng AI", "Subtitle"))
    b.append(p("Ngày lập: 02/10/2026 | Phạm vi: mã nguồn, artifact model, đánh giá, triển khai và kiểm thử", "Center"))
    b.append(p("", "Center"))
    b.append(p("Tóm tắt điều hành", "Heading1"))
    b.append(p("RehabAI là ứng dụng web hỗ trợ theo dõi bài tập phục hồi chức năng bằng camera. Hệ thống gồm giao diện React/Vite, backend FastAPI, xử lý landmark bằng MediaPipe, suy luận TorchScript, cơ sở dữ liệu PostgreSQL/SQLite, trợ lý hội thoại Ollama và module hít thở sâu dựa trên tín hiệu hình học. Phiên bản hiện tại phù hợp cho demo và nghiên cứu có kiểm soát; chưa phải thiết bị chẩn đoán và chưa có bằng chứng lâm sàng."))
    b.append(table([
        ["Hạng mục", "Trạng thái kiểm tra"],
        ["Python compile", "Đạt"],
        ["Backend/shared tests", "205 passed, 1 skipped"],
        ["Frontend build", "Đạt (TypeScript + Vite)"],
        ["Frontend lint", "Đạt (oxlint)"],
        ["Model artifact SHA-256", "Khớp toàn bộ manifest"],
        ["Docker runtime", "Backend healthy, PostgreSQL healthy, frontend/nginx đang chạy"],
        ["Migration production", "0006_deep_breathing (head)"],
    ], [3300, 6000]))
    b.append(p("Kết luận kỹ thuật: nền tảng phần mềm đã vận hành được và có kiểm thử hồi quy. Rủi ro chính nằm ở độ bao phủ subject/exercise và thiếu annotation chuyên gia để xác nhận đúng/sai kỹ thuật hoặc hiệu quả lâm sàng."))

    b.append(heading("1. Phạm vi và kiến trúc hệ thống"))
    b.append(p("Mã nguồn chính nằm trong thư mục rehabai/. Các thư mục data, experiments, artifacts và reports giữ dữ liệu, checkpoint, kết quả đánh giá và tài liệu nghiên cứu; chúng không phải các service chạy độc lập."))
    b.append(table([
        ["Lớp", "Thành phần", "Vai trò"],
        ["Frontend", "React 19, TypeScript, Vite, React Router, Recharts", "Trang công khai, đăng nhập, chọn bài, camera, lịch sử, báo cáo, AI Coach, hít thở sâu"],
        ["API", "FastAPI + Uvicorn + WebSocket", "Auth/JWT, session, pain, history, report, chat, inference realtime"],
        ["Vision", "MediaPipe Holistic/Pose, OpenCV, NumPy", "Trích xuất pose/hand landmarks, quality gate, tiền xử lý"],
        ["ML runtime", "TorchScript/PyTorch", "Nạp artifact, kiểm tra feature contract/hash, dự đoán exercise class"],
        ["Data", "SQLAlchemy, Alembic, PostgreSQL; SQLite dev", "User, session, pain, settings, chat, deep-breathing events"],
        ["Deploy", "Docker Compose, Nginx", "PostgreSQL, backend, frontend static server và reverse proxy"],
        ["Local AI", "Ollama", "Trợ lý hội thoại local, có timeout/concurrency/context limit"],
    ], [1700, 3000, 4600]))
    b.append(p("Luồng nhận diện bài tập: camera trình duyệt → WebSocket → MediaPipe landmarks → chuẩn hóa và kinematics → cửa sổ 96 frame × 237 feature → TorchScript model → exercise_id/confidence → frontend và session metadata. Video gốc không được lưu trong luồng session."))

    b.append(heading("2. Dữ liệu và feature contract"))
    b.append(p("Artifact production yêu cầu input shape (96, 237), kiểu float32. Feature schema gồm pose landmarks 33×4, pose world landmarks 33×4, hai bàn tay 21×3, timestamps/frame indices, các mask landmark và 12 đặc trưng động học."))
    b.append(table([
        ["Nhóm feature", "Kích thước / nội dung"],
        ["Pose", "33 landmark × (x, y, z, visibility); thêm pose world landmarks"],
        ["Hands", "Left/right hand: 21 landmark × (x, y, z), zero khi thiếu"],
        ["Masks", "pose_mask, left_hand_mask, right_hand_mask để phân biệt thiếu/interpolated"],
        ["Kinematics", "12 feature: shoulder/elbow angles, trunk inclination, angular velocity, wrist velocity"],
        ["Temporal window", "96 frame liên tiếp; normalization được đóng gói cùng artifact"],
    ], [2600, 6700]))
    b.append(p("Model loader xác minh architecture signature, input_dim, temporal_frames, class mapping, registry SHA-256 và bundle_sha256.json trước khi phục vụ. Điều này ngăn artifact sai schema hoặc bị thay đổi ngoài kiểm soát."))

    b.append(page_break())
    b.append(heading("3. Chi tiết các mô hình đã sử dụng"))
    b.append(p("Bảng dưới đây phân biệt model đang được backend nạp với các model/baseline chỉ dùng trong nghiên cứu. Việc có checkpoint hoặc metrics trong experiments không đồng nghĩa model đó đang phục vụ người dùng."))
    b.append(table([
        ["Model", "Vai trò", "Kiến trúc / input", "Kết quả / trạng thái"],
        ["RehabMotionNet v2", "Artifact backend hiện dùng", "TorchScript; 96×237; upper-limb; dùng hand, kinematics, contrastive, MS-TCN, attention; 4 lớp exercise", "LOSO 10 fold: accuracy 0.4379 ± 0.2335; macro-F1 0.3544 ± 0.2704. Research/demo; completion head không promote"],
        ["RehabMotionNet v1", "Baseline nghiên cứu", "RehabMotionNet, 96×237, 4 lớp; bản trước của upper-limb pipeline", "Exercise macro-F1 báo cáo khoảng 0.3491; completion F1 0.4846; không phải artifact production hiện tại"],
        ["UpperLimbCTRGCN v1", "So sánh nghiên cứu", "Graph convolution trên upper-limb skeleton; checkpoint theo fold LOSO", "Được dùng trong các thí nghiệm CTR-GCN và ensemble; không được chọn làm production artifact"],
        ["RehabCTR-TCN / 3-stream CTR-GCN + MS-TCN", "Nhận diện repetition research", "Các stream skeleton/hand/kinematic với temporal convolution; bài tập-specific", "Có các experiment datanew và strict multi-seed; nhãn auto_rule_v1 chỉ là heuristic, chưa là ground truth"],
        ["RehabMotionNet + CTR-GCN Ensemble v1", "Artifact nghiên cứu", "Kết hợp model_v2 và CTR-GCN fold_04 với trọng số cố định", "Macro-F1 LOSO nghiên cứu khoảng 0.3744; research-only, production vẫn dùng model_v2"],
        ["ExternalEncoderAdapter / SSL", "Thử nghiệm pretraining", "Adapter nối encoder ngoài với head RehabAI; các config trong experiments", "Dùng để so sánh generalization; không được promote vào runtime production"],
        ["MLP, LSTM, Linear SVM, Majority", "Baseline đánh giá", "Baseline cổ điển trên kinematics hoặc sequence", "Dùng làm mốc so sánh LOSO, không phục vụ API inference"],
        ["Deep Breathing analyzer", "Tính năng hít thở sâu", "Không dùng model ML đã huấn luyện; signal pipeline + state machine rule-based", "MediaPipe Pose, calibration, EMA, trend, hysteresis, timer; tracking_quality phân biệt camera và timer-only"],
    ], [1900, 1900, 3300, 3600]))
    b.append(heading("3.1 RehabMotionNet v2 đang được backend sử dụng", 2))
    b.append(p("Tên artifact: RehabMotionNet, version 1.1, architecture signature rehab_motionnet_upper_limb_v2. Class mapping artifact: output 0–3 tương ứng Exercise_1–Exercise_4. Model trả về exercise_id, confidence và completion_score; adapter production chỉ công bố nhận diện exercise và không biến completion_score thành đánh giá lâm sàng."))
    b.append(p("Metrics từ artifacts/model_v2/metrics.json: exercise accuracy mean 0.4379408, std 0.2334719; exercise macro-F1 mean 0.3543963, std 0.2704338; completion accuracy mean 0.5024326; completion macro-F1 0.4828134. Protocol là strict subject-wise LOSO 10 folds, 387 samples đạt quality gate."))
    b.append(p("Giới hạn: chỉ 10 subject; folds 07–10 có coverage exercise hạn chế; không có nhãn chuyên gia cho error type; model card xác định đây là research/demo inference model."))
    b.append(heading("3.2 Bộ đếm repetition và đánh giá chuyển động", 2))
    b.append(p("RuleBasedRepCounter là bộ đếm thực nghiệm dựa trên ngưỡng hình học cho vai, khuỷu, cổ tay và độ mở bàn tay. Nó dùng median smoothing, xác nhận nhiều frame, khóa bên hoạt động và cooldown để giảm đếm trùng. Bộ đếm này phù hợp hỗ trợ UI/session metadata; các nhãn auto_rule_v1 không được xem là nhãn đúng kỹ thuật."))
    b.append(heading("3.3 Deep Breathing không phải model classification", 2))
    b.append(p("Tính năng hít thở sâu dùng MediaPipe Pose và state machine gồm IDLE, READY, INHALE, HOLD, EXHALE, REST, UNKNOWN, TRACKING_INSUFFICIENT, PAUSED và COMPLETED. Pipeline xử lý visibility gate, calibration median, chuẩn hóa theo torso/shoulder, EMA, phát hiện xu hướng và kiểm tra duration/cooldown. Khi camera không dùng được, timer-only fallback ghi rõ tracking_quality=UNAVAILABLE."))

    b.append(heading("4. Backend, API và bảo mật"))
    b.append(p("Backend khai báo trong backend/main.py, gồm REST router, platform router, chat router, deep-breathing router và WebSocket inference. API auth dùng JWT; các truy vấn session/history/settings/chat được scope theo user hiện tại. CORS lấy từ CORS_ORIGINS; production yêu cầu cấu hình JWT_SECRET và CORS rõ ràng."))
    b.append(table([
        ["Nhóm API", "Endpoint tiêu biểu"],
        ["Auth", "POST /api/auth/register, POST /api/auth/login, GET /api/users/me"],
        ["Exercise", "POST /api/exercise/session/start, POST /api/exercise/session/end, GET /api/exercise/history"],
        ["Reports/settings", "GET /api/reports/summary, GET /api/reports/progress, GET/PUT /api/settings"],
        ["Chat", "POST /api/chat, GET /api/chat/status, conversations và public-chat"],
        ["Model", "GET /api/health, GET /api/model-info, GET /api/exercises"],
        ["Realtime", "WebSocket /ws/inference và /ws/deep-breathing/{session_id}"],
    ], [2600, 7100]))
    b.append(p("Các route /api/sessions* là alias tương thích tạm thời. Backend có request ID, access log dạng JSON và header rate-limit policy để tích hợp gateway."))

    b.append(heading("5. Frontend và trải nghiệm người dùng"))
    b.append(p("Frontend React/Vite có các nhóm trang public, login, home, exercise selection, practice camera, history/session detail, reports, research, settings, profile, AI Coach và deep breathing. Vite proxy chuyển /api tới 127.0.0.1:8000 và /ws tới WebSocket backend. CSS hỗ trợ light/dark theme, responsive layout và các trạng thái tracking/quality."))
    b.append(p("Các màn hình practice hiển thị bài tập đã chọn, bài tập nhận diện, confidence tương đối, landmark rate, tiến độ repetition, timeline và cảnh báo an toàn. Nội dung UI đã được thiết kế để không gọi mismatched là chẩn đoán động tác sai; đây chỉ là model nhận diện bài khác bài đã chọn."))

    b.append(page_break())
    b.append(heading("6. Dữ liệu, huấn luyện và đánh giá"))
    b.append(p("Pipeline nghiên cứu dùng manifest/split LOSO theo subject, fit normalization trên training partition và giữ provenance hash trong artifact. Dataset upper-limb ghi nhận 491 source videos, trong đó 387 samples vượt quality gate của artifact v2. Datanew có các manifest local và experiment repetition/temporal riêng; ontology ELBOW_FLEXION không được trộn với ELBOW_EXTENSION production."))
    b.append(table([
        ["Đánh giá", "Ý nghĩa"],
        ["Strict subject-wise LOSO", "Không để video/subject test lọt vào train hoặc normalization; đo khả năng tổng quát theo người"],
        ["Accuracy", "Tỷ lệ lớp exercise dự đoán đúng; cần đọc cùng macro-F1 vì class/subject coverage không cân bằng"],
        ["Macro-F1", "Trung bình F1 theo lớp; metric chính để phản ánh lớp yếu"],
        ["Completion head", "Đầu phụ nghiên cứu; không được dùng như điểm lâm sàng và không được promote"],
        ["Auto-rule labels", "Nhãn sinh bởi quy tắc biên độ/timing; dùng để review queue, không phải ground truth"],
    ], [2700, 7000]))
    b.append(p("Kết quả model phải được đọc kèm độ lệch giữa folds. v2 cải thiện nhẹ exercise so với v1 nhưng completion không tốt hơn baseline cân bằng; vì vậy artifact hiện tại chỉ phục vụ nhận diện exercise trong bối cảnh demo/nghiên cứu."))

    b.append(heading("7. Triển khai và vận hành"))
    b.append(p("Docker Compose triển khai PostgreSQL 16, backend, frontend static server và Nginx. Backend chạy Alembic trước Uvicorn, mount artifacts/model_v2 ở chế độ read-only, có healthcheck /api/health. Local development có thể dùng SQLite backend/data/rehabai_sessions.db và chạy Uvicorn/Vite trực tiếp."))
    b.append(table([
        ["Môi trường", "Cách chạy / địa chỉ"],
        ["Development backend", "PYTHONPATH=. ; uvicorn backend.main:app --reload --port 8000"],
        ["Development frontend", "cd frontend ; npm run dev ; mặc định http://localhost:5173"],
        ["Docker", "cd deployment ; tạo deployment/.env từ .env.example ; docker compose up --build -d"],
        ["Production entry", "Nginx :80; frontend :8080; backend debug :8000"],
    ], [2800, 6900]))
    b.append(p("Artifact integrity đã được xác minh bằng bundle_sha256.json. Khi thay model, cần cập nhật đồng bộ model_config, feature_schema, normalization, registry và hash manifest; model loader sẽ fail fast nếu contract không khớp."))

    b.append(heading("8. Kiểm thử và tình trạng hiện tại"))
    b.append(table([
        ["Kiểm tra", "Kết quả"],
        ["Python compileall", "PASS"],
        ["pytest tests shared/tests", "205 passed, 1 skipped; 2 warning không chặn"],
        ["npm run build", "PASS; TypeScript và Vite build thành công"],
        ["npm run lint", "PASS; oxlint không báo lỗi"],
        ["Model loader", "PASS; model v2 load được, CUDA/CPU fallback có sẵn"],
        ["Docker health", "PASS; backend và PostgreSQL healthy"],
        ["Migration", "Production PostgreSQL ở 0006_deep_breathing; SQLite local có thể cần upgrade head nếu đang ở 0005"],
    ], [3000, 6700]))
    b.append(p("Một số dòng INFO từ Alembic/Uvicorn/Docker được ghi vào stderr theo convention của công cụ; PowerShell có thể hiển thị chúng như lỗi dù process vẫn thành công. Request 401 trong log là phản hồi đúng khi gọi API protected không có JWT."))

    b.append(heading("9. Hạn chế và đề xuất tiếp theo"))
    for item in [
        "Bổ sung annotation chuyên gia cho đúng/sai kỹ thuật, error type, repetition boundary và đánh giá fresh-subject.",
        "Đo MAE, boundary F1 và temporal IoU cho repetition thay vì chỉ dùng heuristic labels.",
        "Mở rộng subject/exercise coverage, đặc biệt các fold có ít lớp; giữ strict LOSO và provenance.",
        "Chạy kiểm thử camera thực trên laptop/điện thoại: ánh sáng yếu, xoay màn hình, FPS, CPU/RAM, camera denial và reconnect WebSocket.",
        "Đồng bộ deployment/.env cho mỗi môi trường; không dùng giá trị JWT/mật khẩu mẫu trong production.",
        "Tách rõ metric demo, research và clinical validation trong giao diện và tài liệu phát hành.",
    ]:
        b.append(bullet(item))
    b.append(heading("10. Tài liệu và artifact tham chiếu"))
    for item in [
        "artifacts/model_v2/model_config.json, feature_schema.json, normalization.json, metrics.json, model_card.md",
        "backend/core/model_loader.py và backend/ml/inference/adapter.py",
        "backend/deep_breathing/ và frontend/src/pages/DeepBreathing.tsx",
        "reports/evaluation/UPPER_LIMB_V2_FINAL_REPORT.md",
        "reports/evaluation/REHABAI_FULL_STATUS_AUDIT_2026-09-20.md",
        "reports/evaluation/DEEP_BREATHING_IMPLEMENTATION_2026-09-29.md",
        "README.md, README_FRONTEND_BACKEND.md và deployment/compose.yaml",
    ]:
        b.append(bullet(item))
    b.append(p("Tuyên bố sử dụng: RehabAI là prototype nghiên cứu/demo hỗ trợ phục hồi chức năng. Kết quả model không thay thế chẩn đoán, đánh giá hoặc hướng dẫn của bác sĩ và chuyên viên y tế."))
    return "".join(b)


def make_docx() -> None:
    body = document_body()
    sect = '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1100" w:right="1100" w:bottom="1100" w:left="1100"/></w:sectPr>'
    document = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}{sect}</w:body></w:document>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="21"/><w:color w:val="17233C"/></w:rPr></w:rPrDefault></w:docDefaults><w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:spacing w:after="120" w:line="276"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:jc w:val="center"/><w:spacing w:after="240"/></w:pPr><w:rPr><w:b/><w:color w:val="4247C7"/><w:sz w:val="36"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:pPr><w:jc w:val="center"/><w:spacing w:after="180"/></w:pPr><w:rPr><w:color w:val="667085"/><w:sz w:val="25"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Center"><w:name w:val="Center"/><w:pPr><w:jc w:val="center"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="Heading 1"/><w:pPr><w:keepNext/><w:spacing w:before="260" w:after="120"/></w:pPr><w:rPr><w:b/><w:color w:val="4247C7"/><w:sz w:val="28"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="Heading 2"/><w:pPr><w:keepNext/><w:spacing w:before="180" w:after="90"/></w:pPr><w:rPr><w:b/><w:color w:val="176B59"/><w:sz w:val="24"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr><w:spacing w:after="80"/></w:pPr></w:style></w:styles>'''
    numbering = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/><w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/styles.xml"/></Relationships>'''
    doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Báo cáo toàn bộ dự án RehabAI</dc:title><dc:subject>Kiến trúc, mô hình, đánh giá và triển khai</dc:subject><dc:creator>Codex</dc:creator><cp:lastModifiedBy>Codex</cp:lastModifiedBy><dcterms:created xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="dcterms:W3CDTF">2026-10-02T00:00:00Z</dcterms:created></cp:coreProperties>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUT, "w", ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/numbering.xml", numbering)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("docProps/core.xml", core)
    print(OUT)


if __name__ == "__main__":
    make_docx()
