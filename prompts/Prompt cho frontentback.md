Bạn là một Senior Frontend Engineer + UI/UX Designer. Hãy xây dựng frontend web hoàn chỉnh cho ứng dụng **RehabAI**, một hệ thống hỗ trợ phục hồi chức năng tay/chi trên tại nhà.

### 1. Công nghệ

* React
* TypeScript
* Vite
* Tailwind CSS
* React Router
* Recharts cho biểu đồ
* Lucide React cho icon
* Axios cho giao tiếp Backend API
* Responsive Desktop/Tablet/Mobile

Không dùng giao diện quá "AI", không dùng gradient quá mạnh, không dùng neon, không dùng hiệu ứng futuristic.

### 2. Phong cách UI

Thiết kế giống một sản phẩm healthcare/rehabilitation thực tế:

* Background: White / very light gray
* Primary: Sage Green
* Accent: Soft Coral / Peach
* Text: Dark navy/gray
* Border: Light gray
* Border radius vừa phải
* Shadow nhẹ
* Typography rõ ràng
* Khoảng trắng hợp lý
* Ưu tiên khả năng đọc và thao tác
* Không trang trí thừa

Sidebar desktop:

* Logo RehabAI
* Tổng quan
* Bài tập
* Lịch sử
* Báo cáo
* Cài đặt

Mobile chuyển sidebar thành bottom navigation hoặc hamburger menu.

### 3. Các màn hình cần xây dựng

#### Screen 1 — Login/Register

Tạo:

* Email/Số điện thoại
* Password
* Remember me
* Login
* Register
* Forgot password
* Google login / Apple login có thể để placeholder

Sau khi đăng nhập → Dashboard.

#### Screen 2 — Dashboard

Hiển thị:

* Xin chào người dùng
* Số buổi tập
* Tỷ lệ hoàn thành
* Mức đau trung bình
* Tiến bộ gần đây
* Bài tập gần nhất
* Hoạt động gần đây

Không hiển thị các thông tin y khoa mà hệ thống chưa có dữ liệu.

#### Screen 3 — Pain Assessment Before Exercise

Trước khi bắt đầu bài tập:

Hiển thị câu hỏi:

"Hiện tại bạn cảm thấy mức độ đau như thế nào?"

Thang điểm 1–10.

Cho phép chọn:

1 2 3 4 5 6 7 8 9 10

Có mô tả:

* 1–3: Đau nhẹ
* 4–6: Đau vừa
* 7–10: Đau nhiều

Có ô ghi chú tùy chọn.

Button:

"Tiếp tục"

Nếu mức đau cao, hiển thị cảnh báo an toàn và khuyến nghị người dùng cân nhắc liên hệ nhân viên y tế thay vì tự tăng cường độ tập.

#### Screen 4 — Realtime Exercise

Đây là màn hình QUAN TRỌNG NHẤT.

Layout:

LEFT:

* Camera/video người dùng
* Skeleton/keypoints overlay
* Hiển thị frame realtime
* FPS
* Camera status

RIGHT:

* Tên bài tập
* Số repetition
* Tiến trình
* Trạng thái động tác

Ví dụ:

"Động tác đúng"
"Đang thực hiện"
"Cần điều chỉnh"

Hiển thị:

* Góc khớp hiện tại
* Góc mục tiêu
* Độ chính xác
* Repetition hiện tại
* Tổng repetition

Ví dụ:

Current angle: 82°
Target: 80–90°
Movement quality: 92%

Nếu phát hiện sai:

"Cánh tay đang thấp hơn phạm vi mục tiêu."

"Cố gắng nâng tay cao hơn một chút."

Có button:

* Tạm dừng
* Kết thúc

Không tự động đưa ra chẩn đoán y khoa.

#### Screen 5 — Pain Assessment After Exercise

Sau khi kết thúc:

"Bạn cảm thấy mức độ đau sau bài tập như thế nào?"

Thang 1–10.

Hiển thị:

Before: 3/10
After: 4/10

Cho phép ghi chú.

Nếu mức đau tăng đáng kể hoặc kéo dài:

hiển thị cảnh báo:

"Bạn nên cân nhắc liên hệ nhân viên y tế nếu cơn đau tiếp tục hoặc trở nên bất thường."

Không tự chẩn đoán.

#### Screen 6 — Safety Alert

Thiết kế alert card rõ ràng nhưng không gây hoảng sợ.

Ví dụ:

"Bạn vẫn còn cảm thấy đau sau khi tập."

Nội dung:

"Để đảm bảo an toàn, hãy ngừng hoặc hạn chế tiếp tục tập nếu cơn đau kéo dài và cân nhắc liên hệ bác sĩ/chuyên viên phục hồi chức năng."

Button:

* Xem lịch sử
* Liên hệ / đặt lịch khám (placeholder)

Có disclaimer:

"RehabAI là công cụ hỗ trợ theo dõi và luyện tập tại nhà, không thay thế chẩn đoán hoặc hướng dẫn của bác sĩ."

#### Screen 7 — Exercise History

Table/list:

* Ngày
* Bài tập
* Repetition
* Điểm chất lượng
* Mức đau trước
* Mức đau sau
* Trạng thái

Filter:

* Tất cả
* Hoàn thành
* Chưa hoàn thành

Click vào một record → Session Detail.

#### Screen 8 — Progress Report

Dùng Recharts.

Biểu đồ:

* Exercise completion
* Movement quality
* Pain level
* Number of sessions

Cho phép chọn:

7 ngày
30 ngày
90 ngày

Hiển thị summary cards:

* Completion rate
* Average movement quality
* Average pain
* Sessions

Không tạo ra nhận định y khoa từ biểu đồ.

#### Screen 9 — Session Detail

Hiển thị:

* Date/time
* Exercise
* Duration
* Repetition
* Movement quality
* Pain before
* Pain after

Bảng từng repetition:

Rep | Status | Accuracy | Feedback

Ví dụ:

1 | Correct | 94% | Good
2 | Correct | 91% | Good
3 | Incorrect | 76% | Raise arm slightly

Có thumbnail/video replay nếu Backend cung cấp video.

#### Screen 10 — Settings

Sections:

Language:

* Vietnamese
* English

Account:

* Personal information
* Change password

Device:

* Camera
* Resolution

Notifications:

* Exercise reminder
* Pain warning
* System notification

Appearance:

* Light
* Dark

### 4. State management

Tạo các state/service riêng:

authService
exerciseService
painService
sessionService
reportService
settingsService

Không hard-code dữ liệu vào component.

Có mock API data để frontend chạy ngay khi Backend chưa hoàn thiện.

### 5. API chuẩn bị sẵn

Tạo Axios API client.

Các endpoint dự kiến:

POST /api/auth/login
POST /api/auth/register
GET /api/users/me

POST /api/pain/before
POST /api/pain/after

POST /api/exercise/session/start
POST /api/exercise/session/end

POST /api/exercise/predict
GET /api/exercise/history

GET /api/reports/summary
GET /api/reports/progress
GET /api/sessions/{id}

GET /api/settings
PUT /api/settings

### 6. Realtime architecture

Chuẩn bị abstraction để sau này Backend có thể gửi prediction realtime bằng WebSocket:

Web Camera
→ frame
→ MediaPipe/keypoints
→ Backend/ML
→ prediction
→ Frontend

Frontend không tự giả lập AI prediction trong production.

Khi Backend chưa kết nối, tạo mock WebSocket/service để demo.

### 7. Project structure

src/
├── components/
├── pages/
├── layouts/
├── services/
├── hooks/
├── types/
├── utils/
├── charts/
├── api/
├── assets/
└── routes/

Tách component rõ ràng.

Không tạo một file React quá lớn.

### 8. Yêu cầu cuối

* Code sạch
* TypeScript strict
* Responsive
* Accessible
* Loading state
* Empty state
* Error state
* API error handling
* Camera permission handling
* WebSocket disconnect handling
* Có README
* Có .env.example
* Có mock data
* Có hướng dẫn chạy project

Quan trọng nhất:

**Giao diện phải giống một ứng dụng phục hồi chức năng thực tế, đơn giản, sạch sẽ và đáng tin cậy; không được tạo cảm giác đây là một dashboard AI khoa học viễn tưởng.**

Bạn là Senior Backend Engineer + Machine Learning Engineer. Hãy xây dựng Backend hoàn chỉnh cho ứng dụng **RehabAI**.

### 1. Công nghệ

* Python 3.11+
* FastAPI
* PostgreSQL
* SQLAlchemy
* Pydantic
* Alembic
* PyTorch
* MediaPipe
* OpenCV
* Docker
* Nginx

Kiến trúc phải modular, dễ thay thế model AI sau này.

### 2. Kiến trúc

Frontend React
↓
HTTP/HTTPS
↓
Nginx
↓
FastAPI
↓
Service Layer
┌──────┼────────┐
↓      ↓        ↓
Auth   Exercise  Report
↓
ML Service
↓
MediaPipe
↓
Keypoints
↓
RehabMotionNet
↓
Complete/Incomplete
↓
PostgreSQL

### 3. Database

Tạo các bảng:

users
exercise_types
exercise_sessions
pain_assessments
movement_predictions
movement_feedback
session_repetitions
reports
system_settings

Có:

created_at
updated_at

ID sử dụng UUID.

### 4. Authentication

Implement:

POST /api/auth/register
POST /api/auth/login
GET /api/users/me

Sử dụng JWT.

Password phải hash an toàn.

Không lưu password plaintext.

### 5. Pain Assessment

POST /api/pain/before

Lưu:

session_id
pain_score
note
timestamp

POST /api/pain/after

Lưu tương tự.

Backend có logic phát hiện:

* pain increase
* high pain
* persistent warning

Nhưng KHÔNG chẩn đoán bệnh.

Response có:

pain_score
warning
message

### 6. Exercise Session

POST /api/exercise/session/start

POST /api/exercise/session/end

GET /api/exercise/history

GET /api/sessions/{session_id}

Lưu:

exercise
start_time
end_time
duration
repetition
movement_quality
pain_before
pain_after

### 7. ML Service

Tạo module:

ml/
├── preprocessing/
├── keypoints/
├── models/
├── inference/
└── schemas/

Pipeline:

Video/Camera
↓
MediaPipe
↓
Pose + Hand landmarks
↓
Normalization
↓
Sequence buffer
↓
RehabMotionNet
↓
Prediction

Input dự kiến:

33 pose landmarks
+
21 left hand landmarks
+
21 right hand landmarks

Không được sử dụng synthetic/random features trong production.

### 8. Model

Thiết kế interface:

BaseRehabModel

Có thể thay đổi:

LSTM
BiLSTM
GRU
Transformer

mà không phải sửa API.

Output:

prediction
confidence
movement_quality
feedback
timestamp

Ví dụ:

{
"prediction": "complete",
"confidence": 0.91,
"movement_quality": 0.89,
"feedback": "Động tác đang được thực hiện đúng."
}

### 9. Realtime

Tạo WebSocket:

/ws/exercise/{session_id}

Frontend gửi frame/keypoints.

Backend trả:

prediction
confidence
feedback
joint_angles
repetition
movement_quality

Có cơ chế:

* reconnect
* timeout
* invalid frame handling
* session termination

### 10. REST API

Implement đầy đủ:

POST /api/auth/register
POST /api/auth/login
GET /api/users/me

POST /api/pain/before
POST /api/pain/after

POST /api/exercise/session/start
POST /api/exercise/session/end

GET /api/exercise/history

GET /api/sessions/{id}

GET /api/reports/summary
GET /api/reports/progress

GET /api/settings
PUT /api/settings

GET /api/health

### 11. Docker

Tạo:

Dockerfile
docker-compose.yml
.env.example

Services:

frontend
backend
postgres
nginx

ML model được mount/version riêng.

### 12. Security

Implement:

* JWT
* password hashing
* CORS
* request validation
* file validation
* rate limiting placeholder
* environment variables
* không commit secrets
* structured logging

### 13. Testing

Tạo:

tests/
├── test_auth.py
├── test_pain.py
├── test_sessions.py
├── test_prediction.py
└── test_reports.py

Có mock model để test API mà không cần GPU.

### 14. README

README phải giải thích:

Architecture
Installation
Environment variables
Database migration
Run development
Run Docker
API documentation
ML model integration
WebSocket protocol
Testing

### 15. Nguyên tắc quan trọng

RehabAI là **hệ thống hỗ trợ phục hồi chức năng tại nhà**, không phải hệ thống chẩn đoán.

Backend không được:

* tự chẩn đoán bệnh
* tự thay đổi phác đồ điều trị
* tự đưa ra kết luận y khoa
* tự tăng cường độ tập dựa trên AI

AI chỉ phân tích chất lượng chuyển động và trả feedback theo model đã được huấn luyện.

Nếu phát hiện tín hiệu đau đáng lo ngại, hệ thống chỉ đưa ra cảnh báo và khuyến nghị người dùng liên hệ bác sĩ/chuyên viên y tế.
