import { useEffect, useState } from 'react';
import { BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Calendar, CheckCircle, ChevronRight, RefreshCw, Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageTitle } from './Reports';
import { useAuth } from '../auth';
import { authHeaders } from '../api';

interface Session {
  id: string;
  exercise_id: number;
  exercise: string;
  status: string;
  start_time: string;
  completion_score?: number | null;
  repetition: number;
  target_reps: number;
}
interface DeepBreathingSession {
  session_id: string;
  exercise: 'DEEP_BREATHING';
  session_status: string;
  started_at: string;
  completed_cycles: number;
  target_cycles: number;
  interrupted_cycles: number;
}

export default function HistoryPage() {
  const { token } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [breathingSessions, setBreathingSessions] = useState<DeepBreathingSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [exerciseFilter, setExerciseFilter] = useState('all');
  const [visibleCount, setVisibleCount] = useState(10);
  const apiBase = import.meta.env.VITE_API_BASE || '';

  useEffect(() => {
    fetch(`${apiBase}/api/exercise/history`, { headers: authHeaders(token) })
      .then(res => res.json())
      .then(async data => {
        setSessions(Array.isArray(data) ? data : []);
        const breathing = await fetch(`${apiBase}/api/deep-breathing/sessions`, { headers: authHeaders(token) });
        setBreathingSessions(breathing.ok ? await breathing.json() : []);
        setError('');
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching sessions:', err);
        setError('Không thể tải lịch sử tập luyện.');
        setLoading(false);
      });
  }, [apiBase, token]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 'var(--space-2xl)' }}>
        <div className="spinner"></div>
      </div>
    );
  }

  if (error) return <div className="empty-state surface detail-state" role="alert"><strong>{error}</strong><button className="btn btn-primary" onClick={() => window.location.reload()}><RefreshCw size={17}/> Thử lại</button></div>;
  const combinedSessions: Session[] = [...sessions, ...breathingSessions.map(session => ({ id: session.session_id, exercise_id: 5, exercise: 'Hít thở sâu có hướng dẫn', status: session.session_status, start_time: session.started_at, repetition: session.completed_cycles, target_reps: session.target_cycles }))];
  const exercises = [...new Set(combinedSessions.map(session => session.exercise))];
  const normalizedQuery = query.trim().toLocaleLowerCase('vi-VN');
  const filteredSessions = combinedSessions.filter(session => {
    const matchesExercise = exerciseFilter === 'all' || session.exercise === exerciseFilter;
    const matchesQuery = !normalizedQuery || `${session.exercise} ${new Date(session.start_time).toLocaleString('vi-VN')}`.toLocaleLowerCase('vi-VN').includes(normalizedQuery);
    return matchesExercise && matchesQuery;
  });

  // Keep a real chronological seven-day window, including days with zero sessions.
  const today = new Date();
  const localDayKey = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  const chartDataMap: Record<string, number> = {};
  combinedSessions.forEach(session => {
    const date = new Date(session.start_time);
    const key = localDayKey(date);
    chartDataMap[key] = (chartDataMap[key] || 0) + 1;
  });
  const chartData = Array.from({ length: 7 }, (_, offset) => {
    const date = new Date(today);
    date.setHours(0, 0, 0, 0);
    date.setDate(today.getDate() - (6 - offset));
    const key = localDayKey(date);
    return {
      key,
      name: date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }),
      fullName: date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }),
      count: chartDataMap[key] || 0,
    };
  });
  const chartTotal = chartData.reduce((total, point) => total + point.count, 0);

  return (
    <div>
      <PageTitle title="Lịch sử các buổi tập" subtitle="Xem lại số lần, mức đau và trạng thái hoàn thành của từng buổi tập." />

      <section className="surface history-filters" aria-label="Bộ lọc lịch sử"><label><Search size={17}/><span className="sr-only">Tìm kiếm</span><input value={query} onChange={event => { setQuery(event.target.value); setVisibleCount(10); }} placeholder="Tìm theo bài tập hoặc ngày…" /></label><select value={exerciseFilter} onChange={event => { setExerciseFilter(event.target.value); setVisibleCount(10); }} aria-label="Lọc theo bài tập"><option value="all">Tất cả bài tập</option>{exercises.map(exercise => <option key={exercise} value={exercise}>{exercise}</option>)}</select></section>

      <div className="grid-cols-3 history-overview" style={{ marginBottom: 'var(--space-2xl)' }}>
        <section className="glass-card history-chart-card" aria-label="Số buổi tập trong bảy ngày qua">
          <div className="history-chart-heading"><div><span className="eyebrow">NHỊP TẬP LUYỆN</span><h3>Số buổi tập</h3><p>Trong 7 ngày gần nhất</p></div><span className="chart-total-pill"><strong>{chartTotal}</strong><small>buổi</small></span></div>
          <div className="history-chart" style={{ height: '300px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 16, right: 8, left: -18, bottom: 4 }} barCategoryGap="28%">
                <defs><linearGradient id="historyBarGradient" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#6d72f4"/><stop offset="100%" stopColor="#4b50d7"/></linearGradient></defs>
                <CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="4 6" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--muted)', fontSize: 12 }} dy={8} />
                <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: 'var(--muted)', fontSize: 12 }} width={32} />
                <Tooltip cursor={{ fill: 'rgba(91,95,239,.07)' }} content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const point = payload[0].payload as typeof chartData[number];
                  return <div className="history-chart-tooltip"><small>{point.fullName}</small><strong>{point.count} <span>{point.count === 1 ? 'buổi tập' : 'buổi tập'}</span></strong></div>;
                }} />
                <Bar dataKey="count" name="Buổi tập" fill="url(#historyBarGradient)" radius={[8, 8, 3, 3]} maxBarSize={58} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="history-chart-footnote"><span className="chart-legend-dot"/> Mỗi cột tương ứng với một ngày tập</div>
        </section>
        
        <section className="glass-card history-summary-card"><div className="history-summary-heading"><div><span className="eyebrow">TỔNG QUAN</span><h3>Tiến trình của bạn</h3></div><span className="history-summary-icon"><Calendar size={19}/></span></div><div className="history-summary-stat"><div className="history-stat-icon is-purple"><Calendar size={19}/></div><div><small>Tổng số buổi tập</small><strong>{combinedSessions.length}</strong></div></div><div className="history-summary-stat"><div className="history-stat-icon is-green"><CheckCircle size={19}/></div><div><small>Đã hoàn thành</small><strong>{combinedSessions.filter(s => s.status === 'COMPLETED').length}</strong></div></div><p className="history-summary-note">Tiếp tục duy trì đều đặn để theo dõi tiến bộ rõ hơn.</p></section>
      </div>

      <h3 style={{ marginBottom: 'var(--space-md)' }}>Các lượt tập gần đây</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
        {filteredSessions.slice(0, visibleCount).map(s => (
          <Link to={`/app/history/${s.id}`} key={s.id} className="glass-card history-row" style={{ padding: 'var(--space-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h4 style={{ margin: 0 }}>{s.exercise}</h4>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                {new Date(s.start_time).toLocaleString('vi-VN')}
              </span>
            </div>
            <div className="history-status"><div className={`badge ${s.status === 'COMPLETED' ? 'badge-success' : 'badge-warning'}`}>
              {s.status === 'COMPLETED' ? 'Đã hoàn thành' : s.status === 'INCOMPLETE' ? 'Chưa hoàn thành' : 'Đang tập / Bỏ dở'}
            </div><ChevronRight size={18}/></div>
          </Link>
        ))}
        {filteredSessions.length > visibleCount && <button className="btn btn-secondary history-more" onClick={() => setVisibleCount(value => value + 10)}>Xem thêm</button>}
        {combinedSessions.length > 0 && filteredSessions.length === 0 && (
          <p style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Không có buổi tập phù hợp bộ lọc.</p>
        )}
        {combinedSessions.length === 0 && (
          <p style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Chưa có lịch sử tập luyện.</p>
        )}
      </div>
    </div>
  );
}
