import { useCallback, useEffect, useState } from 'react';
import { Activity, Bell, ClipboardList, FileClock, KeyRound, LayoutDashboard, LogOut, Shield, UserPlus, Users } from 'lucide-react';
import { useAuth } from '../auth';
import { authHeaders } from '../api';

type Account = { id: string; email: string; full_name: string; role: 'admin' | 'doctor' | 'patient'; is_active: boolean; created_at: string };
type AuditRow = { id: string; user_email: string | null; action: string; resource_type: string; created_at: string; payload?: Record<string, unknown> };
type Summary = { accounts: Record<string, number>; active_accounts: number; active_prescriptions: number; audit_events_today: number };

const ROLE_LABELS: Record<string, string> = { admin: 'Quản trị', doctor: 'Bác sĩ', patient: 'Bệnh nhân' };

// FastAPI 422 validation errors carry detail as an array of {loc, msg}; other
// errors carry a string. Flatten to a readable message so flashes don't render
// "[object Object]".
function errDetail(data: unknown, fallback: string): string {
  if (data && typeof data === 'object' && Array.isArray((data as { detail?: unknown }).detail)) {
    const lines = (data as { detail: { loc?: (string | number)[]; msg?: string }[] }).detail
      .map(item => `${(item?.loc ?? []).join('.')} — ${item?.msg ?? ''}`)
      .filter(Boolean);
    if (lines.length) return lines.join('; ');
  }
  const detail = (data as { detail?: unknown })?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  return fallback;
}

export default function Admin() {
  const { user, token, logout } = useAuth();
  const [tab, setTab] = useState<'dashboard' | 'accounts' | 'audit'>('dashboard');
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [logs, setLogs] = useState<AuditRow[]>([]);
  const [newAccount, setNewAccount] = useState({ email: '', full_name: '', password: '', role: 'doctor' as Account['role'], phone: '' });
  const [message, setMessage] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const [broadcastForm, setBroadcastForm] = useState({ target_role: 'patient' as 'patient' | 'doctor', title: '', body: '' });
  const [loadError, setLoadError] = useState('');

  const load = useCallback(async () => {
    const [accRes, sumRes, logRes] = await Promise.all([
      fetch('/api/admin/users', { headers: authHeaders(token) }),
      fetch('/api/admin/health-summary', { headers: authHeaders(token) }),
      fetch('/api/admin/audit-logs?limit=200', { headers: authHeaders(token) }),
    ]);
    const [acc, sum, log] = await Promise.all([
      accRes.ok ? accRes.json().catch(() => []) : [],
      sumRes.ok ? sumRes.json().catch(() => null) : null,
      logRes.ok ? logRes.json().catch(() => []) : [],
    ]);
    setAccounts(Array.isArray(acc) ? acc : []); setSummary(sum && typeof sum === 'object' ? sum : null); setLogs(Array.isArray(log) ? log : []);
    if (!sumRes.ok) setLoadError(sumRes.status === 403 ? 'Tài khoản không có quyền quản trị để tải dữ liệu.' : 'Không thể tải dữ liệu tổng quan. Hãy kiểm tra backend rồi thử lại.');
    else setLoadError('');
  }, [token]);

  useEffect(() => { load().catch(() => {}); }, [load]);

  const flash = (kind: 'ok' | 'err', text: string) => { setMessage({ kind, text }); window.setTimeout(() => setMessage(null), 4000); };

  const createAccount = async () => {
    try {
      const res = await fetch('/api/admin/users', { method: 'POST', headers: authHeaders(token, true), body: JSON.stringify(newAccount) });
      const data = await res.json();
      if (!res.ok) throw new Error(errDetail(data, 'Không thể tạo tài khoản.'));
      flash('ok', `Đã tạo tài khoản ${data.email} (${ROLE_LABELS[data.role]}).`);
      setNewAccount({ email: '', full_name: '', password: '', role: 'doctor', phone: '' });
      load();
    } catch (e) { flash('err', e instanceof Error ? e.message : 'Lỗi không xác định.'); }
  };

  const setRole = async (account: Account, role: Account['role']) => {
    try {
      const res = await fetch(`/api/admin/users/${account.id}/role`, { method: 'PUT', headers: authHeaders(token, true), body: JSON.stringify({ role }) });
      const data = await res.json();
      if (!res.ok) throw new Error(errDetail(data, 'Không thể đổi quyền.'));
      flash('ok', `Đã đổi quyền của ${account.full_name} thành ${ROLE_LABELS[role]}.`);
      load();
    } catch (e) { flash('err', e instanceof Error ? e.message : 'Lỗi không xác định.'); }
  };

  const setActive = async (account: Account, is_active: boolean) => {
    try {
      const res = await fetch(`/api/admin/users/${account.id}/active`, { method: 'PUT', headers: authHeaders(token, true), body: JSON.stringify({ is_active }) });
      const data = await res.json();
      if (!res.ok) throw new Error(errDetail(data, 'Không thể thay đổi trạng thái.'));
      flash('ok', is_active ? 'Đã kích hoạt tài khoản.' : 'Đã khóa tài khoản.');
      load();
    } catch (e) { flash('err', e instanceof Error ? e.message : 'Lỗi không xác định.'); }
  };

  const sendBroadcast = async () => {
    const title = broadcastForm.title.trim();
    if (!title) { flash('err', 'Nhập tiêu đề thông báo.'); return; }
    try {
      const res = await fetch('/api/admin/broadcast', { method: 'POST', headers: authHeaders(token, true),
        body: JSON.stringify({ target_role: broadcastForm.target_role, title, body: broadcastForm.body.trim() || null }) });
      const data = await res.json();
      if (!res.ok) throw new Error(errDetail(data, 'Không thể gửi thông báo.'));
      flash('ok', `Đã gửi tới ${data.recipients} tài khoản (${broadcastForm.target_role}).`);
      setBroadcastForm({ target_role: broadcastForm.target_role, title: '', body: '' });
    } catch (e) { flash('err', e instanceof Error ? e.message : 'Lỗi không xác định.'); }
  };

  if (user?.role !== 'admin') {
    return <div className="page-title"><h1>Khu vực quản trị</h1><p>Bạn cần đăng nhập bằng tài khoản quản trị để xem trang này.</p>
      <button className="btn btn-danger" onClick={logout}>Đăng xuất</button></div>;
  }

  return <div className="page-container">
    <div className="page-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '.8rem' }}>
      <div><span className="eyebrow"><Shield size={13} /> KHU VỰC QUẢN TRỊ · REHABAI</span><h1>Trung tâm quản trị</h1><p>Quản lý tài khoản, nhật ký hệ thống và vận hành của phòng khám.</p></div>
      <button className="btn btn-danger" onClick={logout}><LogOut size={16}/> Đăng xuất</button>
    </div>
    <div style={{ display: 'flex', gap: '.5rem', marginBottom: '1.2rem', flexWrap: 'wrap' }}>
      {([['dashboard', LayoutDashboard, 'Tổng quan'], ['accounts', Users, 'Tài khoản'], ['audit', FileClock, 'Nhật ký hệ thống']] as const).map(([key, Icon, label]) => (
        <button key={key} className={tab === key ? 'btn btn-primary' : 'btn btn-secondary'} onClick={() => setTab(key)}><Icon size={16}/> {label}</button>
      ))}
    </div>
    {message && <div className={`form-error ${message.kind === 'ok' ? 'console-tag' : ''}`} role="alert" style={message.kind === 'ok' ? { background: 'rgba(34,197,94,.12)', color: '#15803d', border: '1px solid rgba(34,197,94,.3)', borderRadius: '1rem', padding: '.7rem 1rem', marginBottom: '1rem' } : undefined}>{message.text}</div>}
    {tab === 'dashboard' && <Dashboard summary={summary} logs={logs.slice(0, 8)} loadError={loadError} onRetry={() => { load().catch(() => {}); }}/>}
    {tab === 'accounts' && (
      <div className="console-grid">
        <div className="console-side">
          <section className="surface console-panel"><h3><UserPlus size={16} style={{ verticalAlign: 'middle', marginRight: '.4rem' }}/> Tạo tài khoản mới</h3>
            <div className="console-form" style={{ padding: 0 }}>
              <label>Họ và tên<input value={newAccount.full_name} onChange={e => setNewAccount(v => ({ ...v, full_name: e.target.value }))} minLength={2} required/></label>
              <label>Email<input type="email" value={newAccount.email} onChange={e => setNewAccount(v => ({ ...v, email: e.target.value }))} required/></label>
              <label>Mật khẩu (tối thiểu 8 ký tự)<input type="text" value={newAccount.password} onChange={e => setNewAccount(v => ({ ...v, password: e.target.value }))} minLength={8} required/></label>
              <label>Quyền<select value={newAccount.role} onChange={e => setNewAccount(v => ({ ...v, role: e.target.value as Account['role'] }))}><option value="doctor">Bác sĩ</option><option value="patient">Bệnh nhân</option><option value="admin">Quản trị</option></select></label>
              <label>Số điện thoại (tuỳ chọn)<input value={newAccount.phone} onChange={e => setNewAccount(v => ({ ...v, phone: e.target.value }))}/></label>
              <div className="form-actions"><button className="btn btn-primary" onClick={createAccount}>Tạo tài khoản</button></div>
            </div>
          </section>
          <section className="surface console-panel"><h3><Bell size={16} style={{ verticalAlign: 'middle', marginRight: '.4rem' }}/> Gửi thông báo tới nhóm</h3>
            <p style={{ color: 'var(--muted)', fontSize: '.85rem', margin: '0 0 .8rem' }}>Thông báo sẽ hiện trong hộp thư của bệnh nhân hoặc bác sĩ.</p>
            <div className="console-form" style={{ padding: 0 }}>
              <label>Nhóm nhận
                <select value={broadcastForm.target_role} onChange={e => setBroadcastForm(v => ({ ...v, target_role: e.target.value as 'patient' | 'doctor' }))}>
                  <option value="patient">Bệnh nhân</option><option value="doctor">Bác sĩ</option>
                </select>
              </label>
              <label>Tiêu đề<input value={broadcastForm.title} onChange={e => setBroadcastForm(v => ({ ...v, title: e.target.value }))} maxLength={200} placeholder="Ví dụ: Cập nhật lịch nghỉ lễ"/></label>
              <label>Nội dung (tuỳ chọn)<textarea value={broadcastForm.body} onChange={e => setBroadcastForm(v => ({ ...v, body: e.target.value }))} rows={2} maxLength={600}/></label>
              <div className="form-actions"><button className="btn btn-secondary" disabled={!broadcastForm.title.trim()} onClick={sendBroadcast}>Gửi thông báo</button></div>
            </div>
          </section>
        </div>
        <section className="surface console-panel">
          <h3 style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><span><Users size={16} style={{ verticalAlign: 'middle', marginRight: '.4rem' }}/> Danh sách tài khoản ({accounts.length})</span>
            <button className="btn btn-secondary" style={{ fontSize: '.78rem', padding: '.4rem .8rem' }} onClick={load}><Activity size={14}/> Làm mới</button></h3>
          <div style={{ overflow: 'auto' }}>
            <table className="console-table">
              <thead><tr><th>Người dùng</th><th>Email</th><th>Quyền</th><th>Trạng thái</th><th>Thao tác</th></tr></thead>
              <tbody>{accounts.map(account => (
                <tr key={account.id}>
                  <td><strong>{account.full_name}</strong>{account.id === user.id && <span className="console-tag ok" style={{ marginLeft: '.4rem' }}>bạn</span>}</td>
                  <td>{account.email}</td>
                  <td><select value={account.role} onChange={e => setRole(account, e.target.value as Account['role'])} style={{ border: '1px solid var(--line)', borderRadius: '.5rem', padding: '.3rem .5rem', background: 'var(--surface)', color: 'var(--ink)' }}>
                    <option value="admin">Quản trị</option><option value="doctor">Bác sĩ</option><option value="patient">Bệnh nhân</option></select></td>
                  <td><button className={`console-tag ${account.is_active ? 'ok' : 'bad'}`} style={{ border: 'none', cursor: 'pointer' }} onClick={() => setActive(account, !account.is_active)}>{account.is_active ? 'Đang hoạt động' : 'Đã khoá'}</button></td>
                  <td><small style={{ color: 'var(--muted)' }}>{new Date(account.created_at).toLocaleDateString('vi-VN')}</small></td>
                </tr>
              ))}{!accounts.length && <tr><td colSpan={5}><div className="empty-hint">Không có tài khoản nào.</div></td></tr>}</tbody>
            </table>
          </div>
        </section>
      </div>
    )}
    {tab === 'audit' && (
      <section className="surface console-panel">
        <h3><FileClock size={16} style={{ verticalAlign: 'middle', marginRight: '.4rem' }}/> Nhật ký hệ thống ({logs.length} sự kiện gần nhất)</h3>
        <p style={{ color: 'var(--muted)', fontSize: '.85rem', margin: '0 0 1rem' }}>Mọi thay đổi tài khoản, đơn tập, thông báo và cấu hình đều được ghi nhận tại đây.</p>
        <div style={{ overflow: 'auto' }}>
          <table className="console-table">
            <thead><tr><th>Thời gian</th><th>Người dùng</th><th>Hành động</th><th>Đối tượng</th><th>Chi tiết</th></tr></thead>
            <tbody>{logs.map(row => (
              <tr key={row.id}>
                <td style={{ whiteSpace: 'nowrap' }}>{new Date(row.created_at).toLocaleString('vi-VN')}</td>
                <td>{row.user_email || '—'}</td>
                <td><span className="console-tag muted">{row.action}</span></td>
                <td>{row.resource_type}{row.payload ? ` (${JSON.stringify(row.payload)})` : ''}</td>
                <td><small style={{ color: 'var(--muted)' }}>id: {row.id.slice(0, 8)}</small></td>
              </tr>
            ))}{!logs.length && <tr><td colSpan={5}><div className="empty-hint">Chưa có sự kiện nào.</div></td></tr>}</tbody>
          </table>
        </div>
      </section>
    )}
    {summary && <div style={{ marginTop: '1rem', fontSize: '.75rem', color: 'var(--muted)' }}><ClipboardList size={13} style={{ verticalAlign: 'middle', marginRight: '.3rem' }}/> <SummaryLine summary={summary}/></div>}
  </div>;
}

function Dashboard({ summary, logs, loadError, onRetry }: { summary: Summary | null; logs: AuditRow[]; loadError?: string; onRetry?: () => void }) {
  if (loadError) return <div className="surface console-panel" role="alert">
    <div className="empty-hint" style={{ color: 'var(--danger, #b91c1c)' }}>{loadError}</div>
    <button className="btn btn-secondary" style={{ marginTop: '.8rem' }} onClick={onRetry}>Thử lại</button>
  </div>;
  if (!summary) return <div className="surface console-panel"><div className="empty-hint">Đang tải dữ liệu tổng quan…</div></div>;
  return <div>
    <div className="grid-cols-4 metric-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-lg)', marginBottom: '1.2rem' }}>
      <StatCard icon={<Users/>} label="Tài khoản" value={`${(summary.accounts?.admin || 0) + (summary.accounts?.doctor || 0) + (summary.accounts?.patient || 0)}`} detail={`Quản trị ${summary.accounts?.admin || 0} · Bác sĩ ${summary.accounts?.doctor || 0} · Bệnh nhân ${summary.accounts?.patient || 0}`}/>
      <StatCard icon={<KeyRound/>} label="Đang hoạt động" value={`${summary.active_accounts}`} detail="Tài khoản chưa bị khoá"/>
      <StatCard icon={<ClipboardList/>} label="Đơn tập active" value={`${summary.active_prescriptions}`} detail="Bài tập bác sĩ đã giao"/>
      <StatCard icon={<Activity/>} label="Sự kiện hôm nay" value={`${summary.audit_events_today}`} detail="Nhật ký hệ thống"/>
    </div>
    <section className="surface console-panel"><h3>Hoạt động gần nhất</h3>
      <div style={{ display: 'grid', gap: '.4rem' }}>{logs.map(row => (
        <div key={row.id} style={{ display: 'flex', gap: '.7rem', fontSize: '.85rem', alignItems: 'center' }}>
          <span className={`console-tag ${row.action.includes('create') ? 'ok' : row.action.includes('cancel') || row.action.includes('deactivate') ? 'bad' : 'muted'}`}>{row.action}</span>
          <span style={{ flex: 1 }}>{row.user_email || 'hệ thống'} · {row.resource_type}</span>
          <small style={{ color: 'var(--muted)' }}>{new Date(row.created_at).toLocaleString('vi-VN')}</small>
        </div>
      ))}{!logs.length && <div className="empty-hint">Chưa có sự kiện nào.</div>}</div>
    </section>
  </div>;
}

function StatCard({ icon, label, value, detail }: { icon: React.ReactNode; label: string; value: string | number; detail: string }) {
  return <article className="surface metric-card" style={{ display: 'flex', gap: '.9rem', alignItems: 'center' }}><span>{icon}</span><div><small>{label}</small><strong>{value}</strong><br/><small style={{ color: 'var(--muted)' }}>{detail}</small></div></article>;
}

function SummaryLine({ summary }: { summary: Summary }) {
  return <span>Tổng tài khoản: {summary.active_accounts} hoạt động · {summary.active_prescriptions} đơn tập · {summary.audit_events_today} sự kiện hôm nay</span>;
}
