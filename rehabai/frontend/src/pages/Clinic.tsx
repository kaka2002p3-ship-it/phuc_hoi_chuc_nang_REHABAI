import { useEffect, useState } from 'react';
import { Building2, CalendarClock, ClipboardList, MapPin, Phone } from 'lucide-react';
import { useAuth } from '../auth';
import { authHeaders } from '../api';

type Clinic = { name: string; address: string | null; phone: string | null; notes?: Record<string, unknown> | null };
type Prescription = { id: string; exercise_id: number; exercise: string; target_reps: number; sessions_per_day: number; note?: string | null; status: string; created_at: string };
type ScheduleRow = { day_of_week: number; start_time: string; end_time: string; note?: string | null };

const DAY_NAMES = ['Chủ nhật', 'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7'];

export default function Clinic() {
  const { token, user } = useAuth();
  const [clinic, setClinic] = useState<Clinic | null>(null);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [schedule, setSchedule] = useState<ScheduleRow[]>([]);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const isStaff = user?.role === 'admin' || user?.role === 'doctor';
    Promise.all([
      fetch('/api/clinic', { headers: isStaff ? authHeaders(token) : undefined }).then(r => r.ok ? r.json() : null),
      fetch('/api/clinic/my-prescriptions', { headers: authHeaders(token) }).then(r => r.ok ? r.json() : []),
      fetch('/api/clinic/doctor-schedules', { headers: authHeaders(token) }).then(r => r.ok ? r.json() : []),
    ]).then(([data, rx, schedules]) => {
      setClinic(data ?? null);
      setPrescriptions(Array.isArray(rx) ? rx : []);
      setSchedule(Array.isArray(schedules) ? schedules : []);
      if (!data) setOffline(true);
    });
  }, [token, user]);

  const active = prescriptions.filter(item => item.status === 'ACTIVE');
  const finished = prescriptions.filter(item => item.status !== 'ACTIVE');

  return <div className="page-container">
    <div className="page-title"><span className="eyebrow"><Building2 size={13} /> PHÒNG KHÁM PHỤC HỒI CHỨC NĂNG</span>
      <h1>{clinic?.name || 'RehabAI'}</h1>
      <p>Thông tin liên hệ và kế hoạch tập luyện của bạn.</p></div>
    {offline && <p className="form-error" role="alert">Không thể tải thông tin phòng khám. Hãy kiểm tra kết nối.</p>}

    <div className="grid-cols-3 feature-grid" style={{ marginBottom: '1.5rem' }}>
      <section className="surface feature-card"><span><MapPin/></span><h3>Địa chỉ</h3><p>{clinic?.address || 'cc Tecco Phù Liên, Phan Đình Phùng, Thái Nguyên'}</p></section>
      <section className="surface feature-card"><span><Phone/></span><h3>Liên hệ</h3><p>{clinic?.phone || '0978469616'}</p></section>
      <section className="surface feature-card"><span><CalendarClock/></span><h3>Lịch bác sĩ</h3>
        {schedule.length ? <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '.3rem' }}>{schedule.map((row, index) => (
          <li key={index} style={{ fontSize: '.85rem' }}>{DAY_NAMES[row.day_of_week]}: {row.start_time}–{row.end_time}{row.note ? ` · ${row.note}` : ''}</li>
        ))}</ul> : <p>Chưa có lịch nào được công bố. Hãy gọi cho phòng khám để đặt lịch.</p>}
      </section>
    </div>

    {user?.role === 'patient' && (
      <section className="surface" style={{ padding: '1.4rem 1.5rem' }}>
        <div className="section-heading"><div><h3><ClipboardList size={18}/> Bài tập bác sĩ giao cho bạn</h3>
          <p>Thực hiện đúng số lượt và số lần mỗi ngày theo đơn tập. Nhấn vào bài để bắt đầu tập.</p></div></div>
        {active.length ? <div style={{ display: 'grid', gap: '.8rem' }}>{active.map(item => <PrescriptionCard key={item.id} item={item}/>)}</div> : <p className="empty-hint">Hiện chưa có đơn tập nào. Bác sĩ sẽ giao bài tập cho bạn.</p>}
        {finished.length > 0 && <details style={{ marginTop: '1rem' }}><summary style={{ cursor: 'pointer', fontSize: '.85rem', color: 'var(--muted)' }}>Đơn tập trước đây ({finished.length})</summary>
          <div style={{ display: 'grid', gap: '.5rem', marginTop: '.8rem', fontSize: '.85rem' }}>{finished.map(item => (
            <div key={item.id}>{item.exercise} · {item.target_reps} lượt × {item.sessions_per_day} lần/ngày · <span className={`console-tag ${item.status === 'COMPLETED' ? 'ok' : 'bad'}`}>{item.status === 'COMPLETED' ? 'Hoàn thành' : 'Đã huỷ'}</span></div>
          ))}</div></details>}
      </section>
    )}
  </div>;
}

function PrescriptionCard({ item }: { item: Prescription }) {
  // Link to the real exercise id. Practice supports 2/4/6 live and shows an
  // "in development" notice for the others (1, 3) instead of silently
  // substituting a different exercise.
  const exerciseSlug = item.exercise_id;
  return <article className="exercise-quick" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
    <div className="exercise-quick-copy"><h4>{item.exercise}</h4>
      <p style={{ display: 'flex', gap: '.5rem', flexWrap: 'wrap' }}>
        <span className="console-tag ok">{item.target_reps} lượt/lần</span>
        <span className="console-tag muted">{item.sessions_per_day} lần/ngày</span>
      </p>
      {item.note && <p style={{ color: 'var(--muted)', fontSize: '.8rem' }}>Ghi chú: {item.note}</p>}
    </div>
    <a className="btn btn-primary" href={`/app/practice/${exerciseSlug}`}>Bắt đầu tập</a>
  </article>;
}
