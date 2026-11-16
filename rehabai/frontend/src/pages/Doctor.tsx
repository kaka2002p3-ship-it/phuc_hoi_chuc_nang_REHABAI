import { useCallback, useEffect, useState } from 'react';
import { Activity, CalendarClock, ClipboardList, LogOut, Search, Stethoscope, User } from 'lucide-react';
import { useAuth } from '../auth';
import { authHeaders } from '../api';

type Patient = { id: string; email: string; full_name: string; phone?: string | null; weekly_goal?: number | null };
type Prescription = { id: string; exercise_id: number; exercise: string; target_reps: number; sessions_per_day: number; note?: string | null; status: string; doctor_id: string; created_at: string };
type PatientDetail = Patient & {
  sessions: {
    id: string; exercise_id: number; exercise: string; start_time: string; status: string;
    repetition: number; target_reps: number | null; pain_before: number | null; pain_after: number | null;
    recommendation: string | null; matched_reps: number; mismatched_reps: number; unassessed_reps: number;
    form_quality?: { pace?: string; angle?: string; pace_label?: string; angle_label?: string; recent_reps?: Array<Record<string, unknown>> } | null;
    speed_assessment?: string | null;
  }[];
  active_prescriptions: Prescription[];
};
type ScheduleRow = { day_of_week: number; start_time: string; end_time: string; note?: string | null };

const DAY_NAMES = ['Chủ nhật', 'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7'];

const PACES: Record<string, { label: string; tone: 'ok' | 'warn' | 'bad' | 'muted' }> = {
  ok: { label: 'Tốc độ phù hợp', tone: 'ok' }, too_fast: { label: 'Tập nhanh', tone: 'warn' },
  too_slow: { label: 'Tập chậm', tone: 'warn' }, unknown: { label: 'Chưa đánh giá', tone: 'muted' },
};
const ANGLES: Record<string, { label: string; tone: 'ok' | 'warn' | 'bad' | 'muted' }> = {
  ok: { label: 'Biên độ đúng', tone: 'ok' }, short_range: { label: 'Biên độ chưa đủ', tone: 'warn' },
  unknown: { label: 'Chưa đánh giá', tone: 'muted' },
};
// Neck (id 6) is hidden from the UI pickers; the backend still supports it.
const EXERCISE_NAMES: Record<number, string> = { 1: 'Vai - Nâng vật', 2: 'Khuỷu tay - Gập/duỗi', 3: 'Cổ tay - Gập/duỗi', 4: 'Bàn tay - Mở bàn tay' };

export default function Doctor() {
  const { user, token, logout } = useAuth();
  const [tab, setTab] = useState<'patients' | 'prescribe' | 'schedule'>('patients');
  const [patients, setPatients] = useState<Patient[]>([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<PatientDetail | null>(null);
  const [loadingPatient, setLoadingPatient] = useState(false);
  const [form, setForm] = useState({ exercise_id: 2, target_reps: 5, sessions_per_day: 1, note: '' });
  const [message, setMessage] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const [schedule, setSchedule] = useState<ScheduleRow[]>([]);
  const [loadError, setLoadError] = useState('');

  const loadPatients = useCallback(async () => {
    const res = await fetch(`/api/doctor/patients${search ? `?search=${encodeURIComponent(search)}` : ''}`, { headers: authHeaders(token) });
    if (res.ok) { setPatients(await res.json()); setLoadError(''); }
    else { setPatients([]); setLoadError(res.status === 403 ? 'Bạn không còn quyền truy cập khu vực bác sĩ.' : 'Không thể tải danh sách bệnh nhân. Hãy thử lại.'); }
  }, [token, search]);

  const openPatient = useCallback(async (patient: Patient) => {
    setLoadingPatient(true);
    try {
      const res = await fetch(`/api/doctor/patients/${patient.id}`, { headers: authHeaders(token) });
      if (res.ok) { setSelected(await res.json()); setTab('patients'); }
    } finally { setLoadingPatient(false); }
  }, [token]);

  useEffect(() => { loadPatients(); }, [loadPatients]);

  const flash = (kind: 'ok' | 'err', text: string) => { setMessage({ kind, text }); window.setTimeout(() => setMessage(null), 4000); };

  const prescribe = async () => {
    if (!selected) return;
    try {
      const res = await fetch('/api/doctor/prescriptions', { method: 'POST', headers: authHeaders(token, true),
        body: JSON.stringify({ patient_id: selected.id, exercise_id: form.exercise_id, target_reps: form.target_reps, sessions_per_day: form.sessions_per_day, note: form.note || null }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Không thể giao bài tập.');
      flash('ok', `Đã giao "${EXERCISE_NAMES[form.exercise_id] || form.exercise_id}" cho ${selected.full_name}. Bệnh nhân sẽ nhận thông báo.`);
      openPatient(selected);
    } catch (e) { flash('err', e instanceof Error ? e.message : 'Lỗi không xác định.'); }
  };

  const updateSchedule = async () => {
    try {
      const res = await fetch('/api/doctor/schedule', { method: 'PUT', headers: authHeaders(token, true), body: JSON.stringify(schedule) });
      if (!res.ok) throw new Error('Không thể lưu lịch.');
      flash('ok', 'Đã cập nhật lịch làm việc.');
    } catch { flash('err', 'Không thể lưu lịch.'); }
  };

  const loadSchedule = useCallback(async () => {
    const res = await fetch('/api/doctor/schedule', { headers: authHeaders(token) });
    if (res.ok) {
      const rows = await res.json();
      setSchedule(Array.isArray(rows) ? rows : []);
      setLoadError('');
    } else {
      setLoadError(res.status === 403 ? 'Bạn không còn quyền truy cập khu vực bác sĩ.' : 'Không thể tải lịch làm việc. Hãy thử lại.');
    }
  }, [token]);

  useEffect(() => { if (tab === 'schedule') loadSchedule(); }, [tab, loadSchedule]);

  if (user?.role !== 'doctor' && user?.role !== 'admin') {
    return <div className="page-title"><h1>Khu vực bác sĩ</h1><p>Bạn cần đăng nhập bằng tài khoản bác sĩ hoặc quản trị để xem trang này.</p>
      <button className="btn btn-danger" onClick={logout}>Đăng xuất</button></div>;
  }

  return <div className="page-container">
    <div className="page-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '.8rem' }}>
      <div><span className="eyebrow"><Stethoscope size={13} /> KHU VỰC BÁC SĨ · REHABAI</span><h1>Không gian bác sĩ</h1><p>Theo dõi bệnh nhân và giao bài tập phục hồi chức năng.</p></div>
      <button className="btn btn-danger" onClick={logout}><LogOut size={16}/> Đăng xuất</button>
    </div>
    <div style={{ display: 'flex', gap: '.5rem', marginBottom: '1.2rem', flexWrap: 'wrap' }}>
      {([['patients', User, 'Bệnh nhân'], ['prescribe', ClipboardList, 'Giao bài tập'], ['schedule', CalendarClock, 'Lịch làm việc']] as const).map(([key, Icon, label]) => (
        <button key={key} className={tab === key ? 'btn btn-primary' : 'btn btn-secondary'} onClick={() => setTab(key)}><Icon size={16}/> {label}</button>
      ))}
    </div>
    {message && <div role="alert" style={{ background: message.kind === 'ok' ? 'rgba(34,197,94,.12)' : 'rgba(239,68,68,.1)', color: message.kind === 'ok' ? '#15803d' : '#b91c1c', border: `1px solid ${message.kind === 'ok' ? 'rgba(34,197,94,.3)' : 'rgba(239,68,68,.3)'}`, borderRadius: '1rem', padding: '.7rem 1rem', marginBottom: '1rem' }}>{message.text}</div>}

    {tab === 'patients' && (
      <div className="console-grid">
        <div className="console-side">
          <section className="surface console-panel">
            <h3><User size={16} style={{ verticalAlign: 'middle', marginRight: '.4rem' }}/> Bệnh nhân ({patients.length})</h3>
            <label style={{ display: 'grid', gap: '.3rem', fontSize: '.78rem', color: 'var(--muted)', marginBottom: '.8rem' }}>Tìm kiếm
              <div className="input-shell" style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}><Search size={15}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Tên hoặc email…" style={{ border: 'none', background: 'transparent', color: 'var(--ink)', width: '100%' }}/></div></label>
            <div className="console-list">{loadError && <div className="empty-hint" role="alert" style={{ color: 'var(--danger, #b91c1c)' }}>{loadError}</div>}{patients.map(patient => (
              <button key={patient.id} className="console-item" onClick={() => openPatient(patient)} style={{ background: 'transparent', border: selected?.id === patient.id ? '1px solid var(--brand)' : '1px solid var(--line)', width: '100%' }}>
                <span className="avatar" style={{ flexShrink: 0 }}>{patient.full_name[0]?.toUpperCase()}</span>
                <span className="item-main"><strong>{patient.full_name}</strong><small>{patient.email}</small></span>
              </button>
            ))}{!patients.length && <div className="empty-hint">Chưa có bệnh nhân nào.</div>}</div>
          </section>
        </div>
        <section className="surface console-panel">
          <h3>{loadingPatient ? 'Đang tải…' : selected ? `Hồ sơ & lịch sử: ${selected.full_name}` : 'Chọn bệnh nhân để xem hồ sơ'}</h3>
          {selected && !loadingPatient && (
            <>
              <div style={{ display: 'grid', gap: '1rem' }}>
                <div><strong style={{ fontSize: '.9rem' }}>Thông tin</strong>
                  <table className="console-table" style={{ marginTop: '.5rem' }}><tbody>
                    <tr><td>Email</td><td>{selected.email}</td></tr>
                    {selected.phone != null && <tr><td>Số điện thoại</td><td>{selected.phone}</td></tr>}
                    {selected.weekly_goal != null && <tr><td>Mục tiêu tuần</td><td>{selected.weekly_goal} buổi</td></tr>}
                  </tbody></table>
                </div>
                <div><strong style={{ fontSize: '.9rem' }}>Đơn tập hiện tại</strong>
                  <div style={{ marginTop: '.5rem', display: 'grid', gap: '.4rem' }}>
                    {selected.active_prescriptions.map(rx => (
                      <div key={rx.id} style={{ display: 'flex', gap: '.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        <span className="console-tag ok">{rx.status === 'ACTIVE' ? 'Đang tập' : rx.status}</span>
                        <strong>{rx.exercise}</strong>
                        <span>· {rx.target_reps} lượt × {rx.sessions_per_day} lần/ngày</span>
                        {rx.note && <small style={{ color: 'var(--muted)' }}>Ghi chú: {rx.note}</small>}
                      </div>
                    ))}{!selected.active_prescriptions.length && <div className="empty-hint">Chưa có đơn tập nào.</div>}
                  </div>
                </div>
                <div>
                  <strong style={{ fontSize: '.9rem' }}>Lịch sử tập ({selected.sessions.length} buổi)</strong>
                  <div style={{ overflow: 'auto', marginTop: '.5rem' }}>
                    <table className="console-table">
                      <thead><tr><th>Bài tập</th><th>Ngày</th><th>Trạng thái</th><th>Lượt</th><th>Đúng/Sai</th><th>Tốc độ</th><th>Đau (trước→sau)</th></tr></thead>
                      <tbody>{selected.sessions.slice(0, 20).map(session => (
                        <tr key={session.id}>
                          <td><strong>{session.exercise}</strong></td>
                          <td style={{ whiteSpace: 'nowrap' }}>{new Date(session.start_time).toLocaleDateString('vi-VN')}</td>
                          <td><span className={`console-tag ${session.status === 'COMPLETED' ? 'ok' : 'muted'}`}>{session.status === 'COMPLETED' ? 'Hoàn thành' : session.status === 'IN_PROGRESS' ? 'Đang tập' : 'Chưa hoàn thành'}</span></td>
                          <td>{session.repetition}/{session.target_reps ?? '—'}</td>
                          <td>
                            <span className={`console-tag ${session.unassessed_reps ? 'muted' : session.mismatched_reps ? 'warn' : 'ok'}`} title={`${session.matched_reps} đúng · ${session.mismatched_reps} sai · ${session.unassessed_reps} chưa đủ dữ liệu`}>
                              {session.unassessed_reps ? `${session.unassessed_reps} chưa đánh giá` : session.mismatched_reps ? `${session.mismatched_reps} lượt sai` : `${session.matched_reps} lượt đúng`}
                            </span>
                          </td>
                          <td>{(session.form_quality?.pace && PACES[session.form_quality.pace]) ? <span className={`console-tag ${PACES[session.form_quality.pace!].tone}`}>{PACES[session.form_quality.pace!].label}</span> : <span className="console-tag muted">—</span>}
                            <br/>{session.form_quality?.angle && ANGLES[session.form_quality.angle] ? <span className={`console-tag ${ANGLES[session.form_quality.angle].tone}`} title={session.form_quality.angle_label}>{ANGLES[session.form_quality.angle].label}</span> : null}
                          </td>
                          <td>{session.pain_before ?? '—'} → {session.pain_after ?? '—'}</td>
                        </tr>
                      ))}{!selected.sessions.length && <tr><td colSpan={7}><div className="empty-hint">Bệnh nhân chưa có buổi tập nào.</div></td></tr>}</tbody>
                    </table>
                  </div>
                  {selected.sessions.some(s => s.recommendation) && <p style={{ fontSize: '.8rem', color: 'var(--muted)', marginTop: '.6rem' }}><Activity size={13} style={{ verticalAlign: 'middle' }}/> Gợi ý gần nhất: {selected.sessions.find(s => s.recommendation)?.recommendation}</p>}
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    )}

    {tab === 'prescribe' && (
      <div className="console-grid">
        <div className="console-side">
          <section className="surface console-panel">
            <h3><ClipboardList size={16} style={{ verticalAlign: 'middle', marginRight: '.4rem' }}/> Giao bài tập</h3>
            <p style={{ color: 'var(--muted)', fontSize: '.85rem' }}>Bệnh nhân được chọn: <strong>{selected ? selected.full_name : 'chưa chọn'}</strong></p>
            <div className="console-form" style={{ padding: 0 }}>
              <label>Chọn bệnh nhân
                <select value={selected?.id || ''} onChange={e => { const found = patients.find(p => p.id === e.target.value); if (found) openPatient(found); }}>
                  <option value="">— Chọn —</option>
                  {/* Keep the currently selected patient visible even if the search filter hid them,
                      otherwise the button would submit for an invisible patient. */}
                  {selected && !patients.some(p => p.id === selected.id)
                    && <option value={selected.id}>{selected.full_name} · {selected.email} (đang chọn)</option>}
                  {patients.map(patient => <option key={patient.id} value={patient.id}>{patient.full_name} · {patient.email}</option>)}
                </select>
              </label>
              <label>Bài tập
                <select value={form.exercise_id} onChange={e => setForm(v => ({ ...v, exercise_id: Number(e.target.value) }))}>
                  {Object.entries(EXERCISE_NAMES).map(([id, name]) => <option key={id} value={id}>{name}</option>)}
                </select>
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '.7rem' }}>
                <label>Số lượt mỗi lần (reps)
                  <input type="number" min={1} max={30} value={form.target_reps} onChange={e => setForm(v => ({ ...v, target_reps: Math.max(1, Math.min(30, Number(e.target.value) || 1)) }))}/>
                </label>
                <label>Lần tập mỗi ngày
                  <input type="number" min={1} max={14} value={form.sessions_per_day} onChange={e => setForm(v => ({ ...v, sessions_per_day: Math.max(1, Math.min(14, Number(e.target.value) || 1)) }))}/>
                </label>
              </div>
              <label>Ghi chú cho bệnh nhân (tuỳ chọn)
                <textarea value={form.note} onChange={e => setForm(v => ({ ...v, note: e.target.value }))} rows={3} maxLength={500} placeholder="Ví dụ: tập chậm, dừng ngay nếu đau tăng trên 4/10."/>
              </label>
              <div className="form-actions">
                <button className="btn btn-primary" disabled={!selected} onClick={prescribe}>{selected ? 'Giao bài tập & gửi thông báo' : 'Chọn bệnh nhân trước'}</button>
              </div>
            </div>
          </section>
          {selected && <section className="surface console-panel"><h3>Đơn tập hiện tại của {selected.full_name}</h3>
            <div style={{ display: 'grid', gap: '.4rem' }}>{selected.active_prescriptions.map(rx => (
              <div key={rx.id} style={{ display: 'flex', gap: '.6rem', flexWrap: 'wrap', fontSize: '.85rem' }}><span className="console-tag ok">{rx.status}</span><strong>{rx.exercise}</strong><span>{rx.target_reps} × {rx.sessions_per_day} lần/ngày</span></div>
            ))}{!selected.active_prescriptions.length && <div className="empty-hint">Chưa có đơn tập.</div>}</div>
          </section>}
        </div>
      </div>
    )}

    {tab === 'schedule' && (
      <section className="surface console-panel" style={{ maxWidth: '760px' }}>
        <h3><CalendarClock size={16} style={{ verticalAlign: 'middle', marginRight: '.4rem' }}/> Lịch làm việc của bạn</h3>
        <p style={{ color: 'var(--muted)', fontSize: '.85rem' }}>Lịch này hiển thị cho bệnh nhân trong mục “Phòng khám” và được dùng khi đặt lịch tư vấn.</p>
        <div style={{ display: 'grid', gap: '.6rem', marginTop: '1rem' }}>
          {schedule.map((row, index) => (
            <div key={index} style={{ display: 'grid', gridTemplateColumns: '110px 90px 90px 1fr', gap: '.6rem', alignItems: 'center', fontSize: '.85rem' }}>
              <label style={{ color: 'var(--muted)', fontSize: '.78rem' }}>{DAY_NAMES[row.day_of_week]}
                <select value={row.day_of_week} onChange={e => setSchedule(s => s.map((r, i) => i === index ? { ...r, day_of_week: Number(e.target.value) } : r))} style={{ width: '100%', margin: '0' }}>
                  {DAY_NAMES.map((name, day) => <option key={day} value={day}>{name}</option>)}
                </select>
              </label>
              <label style={{ color: 'var(--muted)', fontSize: '.78rem' }}>Bắt đầu
                <input type="time" value={row.start_time} onChange={e => setSchedule(s => s.map((r, i) => i === index ? { ...r, start_time: e.target.value } : r))}/>
              </label>
              <label style={{ color: 'var(--muted)', fontSize: '.78rem' }}>Kết thúc
                <input type="time" value={row.end_time} onChange={e => setSchedule(s => s.map((r, i) => i === index ? { ...r, end_time: e.target.value } : r))}/>
              </label>
              <input value={row.note || ''} placeholder="Ghi chú (tuỳ chọn)" onChange={e => setSchedule(s => s.map((r, i) => i === index ? { ...r, note: e.target.value } : r))}/>
            </div>
          ))}
          {!schedule.length && <div className="empty-hint">Chưa có lịch nào. Thêm ca đầu tiên bên dưới.</div>}
        </div>
        <div style={{ display: 'flex', gap: '.6rem', marginTop: '1rem', flexWrap: 'wrap' }}>
          <button className="btn btn-secondary" onClick={() => setSchedule(s => [...s, { day_of_week: 1, start_time: '08:00', end_time: '17:00', note: null }])}>+ Thêm ca</button>
          <button className="btn btn-primary" onClick={updateSchedule}>Lưu lịch</button>
        </div>
      </section>
    )}
  </div>;
}
