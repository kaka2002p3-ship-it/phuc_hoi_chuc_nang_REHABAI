import { useState } from 'react';
import type { FormEvent } from 'react';
import { Activity, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../auth';
import heroCompanion from '../assets/illustrations/hero-companion-3d.png';

export default function Login() {
  const { user, save } = useAuth(); const navigate = useNavigate(); const location = useLocation(); const [searchParams] = useSearchParams();
  const redirectParam = searchParams.get('redirect') || '';
  const safeRedirect = redirectParam.startsWith('/app') && !redirectParam.startsWith('//') ? redirectParam : '/app';
  const [register, setRegister] = useState(location.pathname === '/register'); const [email, setEmail] = useState('');
  const [name, setName] = useState(''); const [password, setPassword] = useState('');
  const [error, setError] = useState(''); const [loading, setLoading] = useState(false);
  if (user) return <Navigate to={safeRedirect} replace />;
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setLoading(true);
    try {
      const response = await fetch(`/api/auth/${register ? 'register' : 'login'}`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(register ? { email, full_name: name, password } : { email, password }) });
      const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Không thể đăng nhập.');
      save(data.access_token, data.user);
      const role = data.user?.role;
      navigate(role === 'admin' ? '/admin' : role === 'doctor' ? '/doctor' : safeRedirect, { replace: true });
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Có lỗi xảy ra.'); } finally { setLoading(false); }
  };
  return <main className="auth-page">
    <section className="auth-brand"><div className="brand-mark"><Activity /></div><h1>RehabAI</h1><p>Hành trình phục hồi của bạn<br />được hỗ trợ bởi AI</p><div className="auth-illustration" aria-hidden="true"><span className="auth-orbit auth-orbit-one"/><span className="auth-orbit auth-orbit-two"/><span className="auth-sparkles">✦　✧　•　✦</span><img src={heroCompanion} alt=""/></div><div className="auth-tagline">Mỗi chuyển động nhỏ<br/><strong>đều có ý nghĩa.</strong></div></section>
    <section className="auth-card"><div className="auth-form"><span className="eyebrow">CHÀO MỪNG BẠN</span><h2>{register ? 'Tạo tài khoản' : 'Đăng nhập'}</h2><p>Tiếp tục hành trình tập luyện an toàn tại nhà.</p>
      <form onSubmit={submit}>
        {register && <label><span>Họ và tên</span><div className="input-shell"><UserRound size={18}/><input value={name} onChange={e=>setName(e.target.value)} minLength={2} required /></div></label>}
        <label><span>Email</span><div className="input-shell"><Mail size={18}/><input type="email" value={email} onChange={e=>setEmail(e.target.value)} required /></div></label>
        <label><span>Mật khẩu</span><div className="input-shell"><LockKeyhole size={18}/><input type="password" value={password} onChange={e=>setPassword(e.target.value)} minLength={register ? 8 : 1} required /></div></label>
        {error && <div className="form-error">{error}</div>}<button className="btn btn-primary" disabled={loading}>{loading ? 'Đang xử lý…' : register ? 'Đăng ký' : 'Đăng nhập'}</button>
      </form><button className="text-button" onClick={()=>{setRegister(v=>!v);setError('')}}>{register ? 'Đã có tài khoản? Đăng nhập' : 'Chưa có tài khoản? Đăng ký'}</button><Link className="auth-home-link" to="/">← Về trang giới thiệu</Link>
      <small className="medical-note">RehabAI hỗ trợ theo dõi tập luyện, không thay thế chẩn đoán hoặc điều trị y tế.</small>
    </div></section>
  </main>;
}
