import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck } from 'lucide-react';

const posts = [
  ['lap-lai-phuc-hoi-chuc-nang', 'Tại sao luyện tập lặp lại quan trọng trong phục hồi chức năng?', 'Phục hồi chi trên'],
  ['mo-ban-tay', 'Mở bàn tay trong phục hồi chức năng', 'Chi trên'],
  ['camera-ai', 'Camera AI theo dõi chuyển động như thế nào?', 'Công nghệ'],
] as const;

export default function PublicKnowledge() { return <main className="public-content-page"><header className="public-content-heading"><span className="public-kicker coral">KIẾN THỨC PHỤC HỒI</span><h1>Knowledge Center</h1><p>Thông tin được tổ chức theo quy trình nguồn, evidence, citation và human review trước khi xuất bản.</p></header><div className="knowledge-preview-notice"><ShieldCheck size={16}/><span>Hiện chưa có bài viết PUBLISHED. Các mục dưới đây là bản xem trước giao diện, không phải khuyến nghị y khoa.</span></div><div className="public-info-grid">{posts.map(([slug, title, category]) => <article className="public-knowledge-row" key={slug}><span className="article-category">MOCK_ONLY · {category}</span><h2>{title}</h2><p>Bản xem trước nội dung. Nguồn và citation chỉ hiển thị sau khi được xác minh và duyệt.</p><Link to={`/knowledge/${slug}`} className="public-card-link">Xem trạng thái bài viết <ArrowRight size={14}/></Link></article>)}</div></main>; }

export function PublicKnowledgeDetail() { const slug = window.location.pathname.split('/').pop(); return <main className="public-content-page"><Link to="/knowledge" className="public-back-link">← Knowledge Center</Link><section className="public-article-detail"><span className="public-kicker coral">MOCK_ONLY · NEEDS_REVIEW</span><h1>{slug === 'mo-ban-tay' ? 'Mở bàn tay trong phục hồi chức năng' : 'Bài viết đang chờ kiểm duyệt'}</h1><p>Trang này là placeholder an toàn: chưa hiển thị claim, DOI, URL hay citation chưa được xác minh. Khi research pipeline hoàn tất human review và publish, nội dung approved mới được công khai và đưa vào RAG.</p><div className="research-note"><ShieldCheck size={24}/><strong>Chưa xuất bản</strong><span>Trạng thái hiện tại: NEEDS_REVIEW · Không dùng làm hướng dẫn điều trị.</span></div></section></main>; }
