import { Activity, ArrowRight, Brain, Camera, CheckCircle2, HeartPulse, Lightbulb, ShieldCheck, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import heroCompanion from '../assets/illustrations/hero-companion-3d.png';
import handOpening from '../assets/illustrations/hand-opening.svg';
import elbowExtension from '../assets/illustrations/elbow-extension.svg';

const exercises = [
  { title: 'Mở bàn tay', description: 'Cải thiện vận động tinh và khả năng kiểm soát bàn tay.', image: handOpening, slug: 'hand-opening' },
  { title: 'Duỗi khuỷu tay', description: 'Tăng biên độ vận động khuỷu tay và sức mạnh cơ.', image: elbowExtension, slug: 'elbow-extension' },
];

export default function PublicHome() {
  const { user } = useAuth();
  return <main className="public-home public-home-compact">
    <section className="public-hero">
      <div className="public-hero-copy"><span className="public-kicker"><Sparkles size={15}/> PHỤC HỒI CHỨC NĂNG THÔNG MINH</span><h1>Phục hồi chức năng<br/><em>thông minh ngay tại nhà</em></h1><p>Ứng dụng trí tuệ nhân tạo và camera để theo dõi chuyển động, hỗ trợ bạn tập luyện phục hồi chức năng an toàn, hiệu quả và khoa học.</p><div className="public-hero-actions"><Link to={user ? '/app' : '/login'} className="public-button primary">{user ? 'Đi tới ứng dụng' : 'Đăng nhập để sử dụng RehabAI'} <ArrowRight size={17}/></Link>{!user && <Link to="/register" className="public-button outline">Đăng ký</Link>}<Link to="/about" className="public-button outline">Tìm hiểu thêm</Link></div></div>
      <div className="public-hero-visual"><div className="hero-orb"/><img src={heroCompanion} alt="Trợ lý RehabAI hướng dẫn mở bàn tay"/><div className="hero-stat"><span>Repetitions</span><strong>8</strong><span>Độ chính xác</span><strong>92%</strong></div></div>
      <div className="public-benefits"><Benefit icon={<Camera/>} title="Tập tại nhà" text="Mọi lúc, mọi nơi"/><Benefit icon={<Brain/>} title="Theo dõi bằng camera AI" text="Thời gian thực"/><Benefit icon={<Lightbulb/>} title="Hướng dẫn dễ hiểu" text="Phù hợp nhiều đối tượng"/><Benefit icon={<ShieldCheck/>} title="Riêng tư và an toàn" text="Dữ liệu theo tài khoản"/></div>
    </section>
    <section className="public-section public-home-exercises"><div className="public-section-heading"><div><span className="public-kicker coral">BÀI TẬP NỔI BẬT</span><h2>Khám phá RehabAI</h2><p>Xem thông tin bài tập trước; camera chỉ hoạt động trong ứng dụng sau khi đăng nhập.</p></div><Link to="/exercises">Xem tất cả <ArrowRight size={14}/></Link></div><div className="public-home-exercise-grid">{exercises.map(item=><article className="public-home-exercise" key={item.slug}><div><img src={item.image} alt=""/></div><section><h3>{item.title}</h3><p>{item.description}</p><Link to={`/exercises/${item.slug}`} className="public-card-link">Xem thông tin <ArrowRight size={14}/></Link></section></article>)}</div></section>
    <section className="public-home-steps"><span className="public-kicker">BẮT ĐẦU ĐƠN GIẢN</span><h2>Learn about RehabAI trước khi Use RehabAI</h2><div><Step icon={<HeartPulse/>} text="Tìm hiểu dự án và bài tập"/><Step icon={<CheckCircle2/>} text="Đăng nhập hoặc tạo tài khoản"/><Step icon={<Activity/>} text="Vào ứng dụng để tập luyện"/></div></section>
  </main>;
}

function Benefit({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) { return <div className="public-benefit"><span>{icon}</span><div><strong>{title}</strong><small>{text}</small></div></div>; }
function Step({ icon, text }: { icon: React.ReactNode; text: string }) { return <article><span>{icon}</span><strong>{text}</strong></article>; }
