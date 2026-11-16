import { Component, useState, type ReactNode } from 'react';
import { Activity, Menu, X } from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../auth';
import PublicChat from './PublicChat';

class PublicChatBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.error('RehabAI public chat widget crashed', error);
  }

  render() {
    if (this.state.hasError) {
      return <div className="public-chat-crash-fallback" role="alert">Chatbot tạm thời gặp lỗi. Bạn vẫn có thể xem các trang Bài tập, Kiến thức và FAQ. <button type="button" onClick={() => this.setState({ hasError: false })}>Thử lại</button></div>;
    }
    return this.props.children;
  }
}

export default function PublicChrome({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = () => setMenuOpen(false);

  return <div className="public-site-shell">
    <header className={`public-header${menuOpen ? ' is-menu-open' : ''}`}>
      <Link to="/" className="public-logo" onClick={closeMenu}>
        <span><Activity size={22}/></span><strong>Rehab<span>AI</span></strong>
      </Link>
      <button className="public-menu-toggle" type="button" aria-label={menuOpen ? 'Đóng menu' : 'Mở menu'} aria-expanded={menuOpen} onClick={() => setMenuOpen(value => !value)}>
        {menuOpen ? <X size={21}/> : <Menu size={21}/>}<span>{menuOpen ? 'Đóng' : 'Menu'}</span>
      </button>
      <nav className="public-nav" aria-label="Điều hướng trang giới thiệu">
        <NavLink onClick={closeMenu} to="/" end>Trang chủ</NavLink>
        <NavLink onClick={closeMenu} to="/about">Về dự án</NavLink>
        <NavLink onClick={closeMenu} to="/exercises">Bài tập</NavLink>
        <NavLink onClick={closeMenu} to="/knowledge">Kiến thức</NavLink>
        <NavLink onClick={closeMenu} to="/research">Nghiên cứu</NavLink>
        <NavLink onClick={closeMenu} to="/faq">FAQ</NavLink>
      </nav>
      <div className="public-auth">
        {user ? <Link onClick={closeMenu} to="/app" className="public-signup">Đi tới ứng dụng</Link> : <><Link onClick={closeMenu} to="/login" className="public-login">Đăng nhập</Link><Link onClick={closeMenu} to="/register" className="public-signup">Đăng ký</Link></>}
      </div>
    </header>
    {children}
    <PublicChatBoundary><PublicChat /></PublicChatBoundary>
    <footer className="public-footer">
      <Link to="/" className="public-logo"><span><Activity size={21}/></span><strong>Rehab<span>AI</span></strong></Link>
      <p>Hỗ trợ hành trình phục hồi chức năng tại nhà.</p>
      <div><Link to="/about">Về dự án</Link><Link to="/knowledge">Kiến thức</Link><Link to="/research">Nghiên cứu</Link><Link to="/login">Đăng nhập</Link></div>
      <small>Nội dung mang tính giáo dục, không thay thế tư vấn y tế.</small>
    </footer>
  </div>;
}
