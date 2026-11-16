import { Bot, MessageCircle, ShieldCheck, Sparkles } from 'lucide-react';
import coachRobot from '../assets/illustrations/coach-robot.svg';

export default function AICoach() {
  const openPrompt = (prompt: string) => {
    window.dispatchEvent(new CustomEvent('rehabai:open-chat', { detail: prompt }));
  };
  return <div className="coach-page">
    <header className="page-title"><span className="eyebrow"><Sparkles size={14}/> AI COACH · OLLAMA LOCAL</span><h1>AI Coach luôn ở bên bạn</h1><p>Trò chuyện, xem lại dữ liệu đã ghi nhận và nhận lời động viên an toàn — không chẩn đoán, không thay thế chuyên viên.</p></header>
    <section className="coach-layout">
      <article className="surface coach-intro"><div className="coach-avatar"><Bot size={30}/></div><h2>Một người bạn đồng hành nhẹ nhàng</h2><p>AI Coach sử dụng Ollama local và chỉ trả lời dựa trên ngữ cảnh được hệ thống xác minh. Bạn vẫn có thể tập luyện bình thường nếu Ollama tạm thời không khả dụng.</p><div className="coach-safety"><ShieldCheck size={18}/><span>Riêng tư · Local-first · Không tư vấn y khoa</span></div><div className="coach-prompts"><span>Gợi ý bắt đầu</span><button onClick={() => openPrompt('Tóm tắt buổi tập gần đây của tôi')}>Tóm tắt buổi tập gần đây</button><button onClick={() => openPrompt('Giải thích kết quả tập luyện gần đây của tôi')}>Giải thích kết quả của tôi</button><button onClick={() => openPrompt('Tôi muốn tâm sự một chút')}>Tôi muốn tâm sự</button></div></article>
      <article className="surface coach-chat-card"><div className="coach-chat-placeholder"><img className="coach-robot-art" src={coachRobot} alt="Robot AI Coach thân thiện"/><MessageCircle className="coach-message-icon" size={28}/><h3>Bắt đầu trò chuyện</h3><p>Trợ lý nổi ở góc phải màn hình để bạn luôn có thể gọi khi cần.</p><button className="btn btn-primary" onClick={()=>document.querySelector<HTMLButtonElement>('.chat-launcher')?.click()}>Mở AI Coach</button></div></article>
    </section>
  </div>;
}
