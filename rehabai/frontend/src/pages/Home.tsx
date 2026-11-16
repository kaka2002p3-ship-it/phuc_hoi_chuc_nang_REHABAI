import { Link } from 'react-router-dom';
import { ArrowRight, Activity, Shield, Brain, CalendarDays, CheckCircle2, MessageCircle, Sparkles, Trophy } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { authHeaders } from '../api';
import { ClinicalDisclaimer } from '../components/ClinicalDisclaimer';
import { useUiHideSettings } from '../ui-hide-settings';
import heroCompanion from '../assets/illustrations/hero-companion-3d.png';
import handOpening from '../assets/illustrations/hand-opening.svg';
import elbowExtension from '../assets/illustrations/elbow-extension.svg';

type Summary={total_sessions:number;completed_sessions:number;completion_rate:number};

export default function Home() {
  const { user, token, logout } = useAuth();
  const uiHide = useUiHideSettings();
  const [summary, setSummary] = useState<Summary>({ total_sessions: 0, completed_sessions: 0, completion_rate: 0 });
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  useEffect(() => {
    fetch('/api/reports/summary', { headers: authHeaders(token) })
      .then(r => {
        if (r.status === 401) {
          logout();
          return Promise.reject(new Error('EXPIRED'));
        }
        return r.ok ? r.json() : Promise.reject(new Error('NETWORK_ERROR'));
      })
      .then(setSummary)
      .catch(err => {
        if (err?.message !== 'EXPIRED') setOffline(true);
      })
      .finally(() => setLoading(false));
  }, [token, logout]);
  return <div className="home-container">
    <section className="home-hero surface"><div className="home-hero-copy"><span className="eyebrow"><Sparkles size={14}/> MỖI CHUYỂN ĐỘNG NHỎ ĐỀU CÓ Ý NGHĨA</span><h1>Chào {user?.full_name?.split(' ').at(-1) || 'bạn'},<br/>hôm nay mình <em>cùng cố gắng nhé.</em></h1><p>RehabAI đồng hành cùng bạn qua từng lần mở bàn tay và gập/duỗi khuỷu tay — riêng tư, nhẹ nhàng và dễ sử dụng.</p><div className="hero-actions"><Link to="/app/exercises" className="btn btn-primary">Bắt đầu tập luyện <ArrowRight size={18}/></Link><Link to="/app/reports" className="btn btn-secondary">Xem tiến trình</Link></div></div><div className="hero-illustration" aria-hidden="true"><img src={heroCompanion} alt=""/><span className="hero-ai-badge">AI</span></div></section>
    {!uiHide.hide_clinical_warning && <ClinicalDisclaimer className="mb-6" />}
    {offline&&<p className="form-error" role="alert">Không thể kết nối máy chủ. Hãy thử lại; giao diện tập luyện không hiển thị dữ liệu giả.</p>}
    <div className="metric-grid home-metrics"><Metric icon={<CalendarDays/>} label="Tổng buổi tập" value={loading?'—':summary.total_sessions}/><Metric icon={<CheckCircle2/>} label="Đã hoàn thành" value={loading?'—':summary.completed_sessions}/><Metric icon={<Activity/>} label="Tỷ lệ hoàn thành" value={loading?'—':`${Math.round(summary.completion_rate*100)}%`}/><Metric icon={<MessageCircle/>} label="Trợ lý local" value="Ollama"/></div>
    <div className="dashboard-main-grid"><section className="surface dashboard-exercises"><div className="section-heading"><div><h3>Bài tập hôm nay</h3><p>Hai bài tập hiện được hệ thống hỗ trợ.</p></div><Link to="/app/exercises">Xem tất cả</Link></div><div className="exercise-quick-grid"><Exercise image={handOpening} title="Mở bàn tay" text="Theo dõi bàn tay và đếm lần lặp đã xác nhận." to="/app/practice/4" tone="violet"/><Exercise image={elbowExtension} title="Gập/duỗi khuỷu tay" text="Theo dõi một chu kỳ chuyển động khuỷu tay trong vùng camera." to="/app/practice/2" tone="coral"/></div></section><section className="surface progress-story"><div className="story-icon"><Trophy/></div><span className="eyebrow">CÂU CHUYỆN TIẾN TRÌNH</span><h3>{summary.total_sessions ? 'Bạn đang xây dựng một thói quen tốt.' : 'Hành trình của bạn bắt đầu từ đây.'}</h3><p>{summary.total_sessions ? `Hệ thống đã ghi nhận ${summary.total_sessions} buổi tập và ${summary.completed_sessions} buổi hoàn thành.` : 'Chưa có đủ dữ liệu để tạo tổng kết tuần. Hãy hoàn thành buổi tập đầu tiên để bắt đầu theo dõi.'}</p><div className="story-sparkles" aria-hidden="true"><span>✦</span><span>★</span><span>✦</span></div></section></div>
    <div className="grid-cols-3 feature-grid"><Feature icon={<Activity/>} title="Theo dõi realtime">Camera và skeleton overlay hỗ trợ quan sát chuyển động.</Feature><Feature icon={<Brain/>} title="AI hỗ trợ, không áp đặt">Mô hình ghi nhận tín hiệu; AI Coach không tự chẩn đoán.</Feature><Feature icon={<Shield/>} title="Local-first">Video được xử lý theo phiên, Ollama chạy qua backend local.</Feature></div>
  </div>;
}

function Metric({icon,label,value}:{icon:React.ReactNode;label:string;value:string|number}){return <article className="surface metric-card"><span>{icon}</span><div><small>{label}</small><strong>{value}</strong></div></article>}
function Exercise({image,title,text,to,tone}:{image:string;title:string;text:string;to:string;tone:string}){return <article className={`exercise-quick ${tone}`}><div className="exercise-quick-art"><img src={image} alt="" aria-hidden="true"/></div><div className="exercise-quick-copy"><h4>{title}</h4><p>{text}</p></div><Link to={to} className="btn btn-primary">Bắt đầu</Link></article>}
function Feature({icon,title,children}:{icon:React.ReactNode;title:string;children:React.ReactNode}){return <article className="surface feature-card"><span>{icon}</span><h3>{title}</h3><p>{children}</p></article>}
