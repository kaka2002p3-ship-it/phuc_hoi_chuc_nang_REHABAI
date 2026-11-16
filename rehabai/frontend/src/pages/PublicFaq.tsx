import { ChevronDown } from 'lucide-react';

const questions = [
  ['RehabAI có thay thế bác sĩ không?', 'Không. RehabAI chỉ hỗ trợ theo dõi tập luyện và cung cấp thông tin giáo dục, không thay thế chẩn đoán hay hướng dẫn cá nhân từ chuyên gia y tế.'],
  ['Tôi cần thiết bị gì để bắt đầu?', 'Bạn cần một thiết bị có camera và trình duyệt hiện đại. Hãy đặt camera ổn định, đủ sáng và làm theo hướng dẫn trước buổi tập.'],
  ['Dữ liệu của tôi có được chia sẻ không?', 'Dữ liệu bài tập được giới hạn theo tài khoản đang đăng nhập. AI Coach chỉ truy cập dữ liệu của chính tài khoản đó.'],
  ['Public website có bật camera không?', 'Không. Public website chỉ cung cấp thông tin. Camera, MediaPipe và session chỉ hoạt động trong khu vực /app sau khi đăng nhập.'],
];

export default function PublicFaq() { return <main className="public-content-page public-faq-page"><header className="public-content-heading"><span className="public-kicker coral">CÂU HỎI THƯỜNG GẶP</span><h1>Bạn muốn biết thêm điều gì?</h1><p>Một vài câu trả lời nhanh trước khi bạn bắt đầu hành trình cùng RehabAI.</p></header><div className="faq-list">{questions.map(([question, answer]) => <details className="public-faq-item" key={question}><summary>{question}<ChevronDown size={18}/></summary><p>{answer}</p></details>)}</div></main>; }
