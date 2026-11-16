import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import { BrainCircuit, Calendar, CheckCircle2, ChevronDown, Clock3, Droplets, HelpCircle, RefreshCw, Repeat2, ShieldCheck, XCircle } from 'lucide-react';
import { PageTitle } from './Reports';
import { useAuth } from '../auth';
import { authHeaders } from '../api';

type RepetitionResult = 'matched' | 'mismatched' | 'unassessed';
type Repetition = { id: string; repetition_number: number; result: RepetitionResult; label?: string; explanation?: string; recorded_at: string };
type FormQuality = { pace?: string; angle?: string; pace_label?: string; angle_label?: string; form_ok_reps?: number; reps_assessed?: number } | null;
type Detail = { id: string; exercise: string; start_time: string; duration_seconds: number; repetition: number; target_reps: number; pain_after: number | null; status: string; recommendation: string | null; repetitions: Repetition[]; matched_reps: number; mismatched_reps: number; unassessed_reps: number; form_quality?: FormQuality; speed_assessment?: string | null };

const PACE_COPY: Record<string, { label: string; tone: string }> = {
  ok: { label: 'Tốc độ phù hợp khuyến nghị', tone: 'badge-success' },
  too_fast: { label: 'Tập nhanh hơn khuyến nghị', tone: 'badge-warning' },
  too_slow: { label: 'Tập chậm hơn khuyến nghị', tone: 'badge-warning' },
  unknown: { label: 'Chưa đủ dữ liệu đo tốc độ', tone: 'badge-info' },
};
const ANGLE_COPY: Record<string, { label: string; tone: string }> = {
  ok: { label: 'Biên độ (góc) đạt yêu cầu', tone: 'badge-success' },
  short_range: { label: 'Biên độ góc chưa đủ — tập đầy hơn nếu không đau', tone: 'badge-warning' },
  unknown: { label: 'Chưa đủ dữ liệu đo góc', tone: 'badge-info' },
};

const resultCopy: Record<RepetitionResult, { label: string; explanation: string }> = {
  matched: { label: 'AI nhận diện đúng bài đã chọn', explanation: 'Dữ liệu camera đủ và bài AI nhận diện trùng với bài bạn đã chọn.' },
  mismatched: { label: 'AI nhận diện bài khác', explanation: 'Dữ liệu camera đủ nhưng bài AI nhận diện không trùng với bài bạn đã chọn.' },
  unassessed: { label: 'Chưa đủ dữ liệu để kết luận', explanation: 'Không có dự đoán hợp lệ khi lần tập được xác nhận. Đây không phải kết luận bạn tập sai.' },
};

export default function SessionDetail() {
  const { id } = useParams();
  const { token } = useAuth();
  const [item, setItem] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [expandedRep, setExpandedRep] = useState<string | null>(null);
  const [breathingDetail, setBreathingDetail] = useState<any>(null);
  const apiBase = import.meta.env.VITE_API_BASE || '';

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/api/exercise/history/${encodeURIComponent(id || '')}`, { headers: authHeaders(token), signal: controller.signal })
      .then(async response => { if (response.status === 404) throw new Error('Không tìm thấy buổi tập hoặc bạn không có quyền xem.'); if (!response.ok) throw new Error('Không thể tải chi tiết buổi tập.'); return response.json() as Promise<Detail>; })
      .then(setItem)
      .catch(async cause => {
        if (cause instanceof DOMException && cause.name === 'AbortError') return;
        const breathingResponse = await fetch(`${apiBase}/api/deep-breathing/sessions/${encodeURIComponent(id || '')}`, { headers: authHeaders(token), signal: controller.signal });
        if (breathingResponse.ok) { setBreathingDetail(await breathingResponse.json()); setError(''); return; }
        setItem(null); setError(cause instanceof Error ? cause.message : 'Không thể tải chi tiết buổi tập.');
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [apiBase, id, reloadKey, token]);

  if (loading) return <div className="surface detail-state" role="status"><div className="spinner"/><strong>Đang tải chi tiết buổi tập…</strong></div>;
  if (breathingDetail) return <DeepBreathingDetail item={breathingDetail} />;
  if (error || !item) return <div className="empty-state surface detail-state" role="alert"><strong>{error || 'Không tìm thấy chi tiết buổi tập.'}</strong><div><button className="btn btn-primary" onClick={() => { setLoading(true); setError(''); setReloadKey(value => value + 1); }}><RefreshCw size={17}/> Thử lại</button><Link className="btn btn-secondary" to="/app/history">Quay lại lịch sử</Link></div></div>;

  return <div>
    <PageTitle title="Chi tiết buổi tập" subtitle={item.exercise}/>
    <section className="surface detail-hero"><div><span className={`badge ${item.status === 'COMPLETED' ? 'badge-success' : 'badge-warning'}`}>{item.status === 'COMPLETED' ? 'Đã hoàn thành' : item.status === 'INCOMPLETE' ? 'Chưa hoàn thành' : 'Đang tập / Bỏ dở'}</span><h2>{item.exercise}</h2><p><Calendar size={16}/>{new Date(item.start_time).toLocaleString('vi-VN')}</p></div></section>
    <div className="metric-grid detail-metrics"><Mini icon={<Repeat2/>} label="Số lần" value={`${item.repetition}/${item.target_reps}`}/><Mini icon={<Clock3/>} label="Thời gian" value={`${Math.round(item.duration_seconds / 60)} phút`}/><Mini icon={<Droplets/>} label="Mức đau" value={`${item.pain_after ?? '—'}/10`}/></div>
    <section className="surface assessment-scope" aria-label="Phạm vi đánh giá của AI"><div className="scope-card is-available"><BrainCircuit/><div><strong>Nhận diện bài tập</strong><span>AI so sánh bài nhận diện với bài bạn đã chọn.</span></div><b>Đang hoạt động</b></div><div className={`scope-card ${item.form_quality ? 'is-available' : ''}`}><ShieldCheck/><div><strong>Đúng/sai & tốc độ</strong><span>{item.form_quality ? 'Đánh giá biên độ góc và tốc độ mỗi chu kỳ tập.' : 'Chưa chấm góc khớp, biên độ hoặc lỗi kỹ thuật của từng lần.'}</span></div><b>{item.form_quality ? 'Đang hoạt động' : 'Chưa đánh giá'}</b></div></section>
    {item.form_quality && (
      <section className="surface detail-metrics form-panel" aria-label="Đánh giá đúng/sai và tốc độ">
        <div className="section-heading"><div><h3>Đúng/Sai & tốc độ tập</h3><p>Đánh giá theo biên độ góc khớp và tốc độ mỗi chu kỳ — tham khảo, không thay thế ý kiến chuyên viên y tế.</p></div></div>
        <div className="metric-grid">
          <Mini icon={PACE_COPY[item.form_quality.pace || 'unknown'].tone === 'badge-success' ? <CheckCircle2/> : <Clock3/>} label="Tốc độ" value={PACE_COPY[item.form_quality.pace || 'unknown'].label}/>
          <Mini icon={ANGLE_COPY[item.form_quality.angle || 'unknown'].tone === 'badge-success' ? <ShieldCheck/> : <HelpCircle/>} label="Biên độ (góc)" value={ANGLE_COPY[item.form_quality.angle || 'unknown'].label}/>
          <Mini icon={<Repeat2/>} label="Đúng cả hai" value={`${item.form_quality.form_ok_reps ?? 0}/${item.form_quality.reps_assessed ?? 0} lần`}/>
        </div>
      </section>
    )}
    <section className="surface repetition-detail"><div className="repetition-heading"><div><h3>Chi tiết từng lần tập</h3><p>Mỗi kết quả chỉ phản ánh việc AI nhận diện đúng bài đã chọn, không phải kết luận đúng/sai kỹ thuật.</p></div><div className="repetition-summary"><span className="matched"><CheckCircle2/>Đúng bài: {item.matched_reps}</span><span className="mismatched"><XCircle/>Bài khác: {item.mismatched_reps}</span><span className="unassessed"><HelpCircle/>Thiếu dữ liệu: {item.unassessed_reps}</span></div></div>
      {item.repetitions.length ? <div className="repetition-list">{item.repetitions.map(rep => { const copy = resultCopy[rep.result]; const expanded = expandedRep === rep.id; return <article key={rep.id} className={`repetition-item ${rep.result}`}><button className="repetition-row" type="button" aria-expanded={expanded} onClick={() => setExpandedRep(expanded ? null : rep.id)}><span className="repetition-result-icon">{rep.result === 'matched' ? <CheckCircle2/> : rep.result === 'mismatched' ? <XCircle/> : <HelpCircle/>}</span><strong>Lần {rep.repetition_number}</strong><b>{rep.label || copy.label}</b><time>{new Date(rep.recorded_at).toLocaleTimeString('vi-VN')}</time><ChevronDown className="repetition-chevron"/></button>{expanded && <div className="repetition-expanded"><p>{rep.explanation || copy.explanation}</p><dl><div><dt>Phạm vi</dt><dd>Nhận diện loại bài tập</dd></div><div><dt>Kỹ thuật động tác</dt><dd>Chưa được đánh giá</dd></div><div><dt>Thời điểm ghi nhận</dt><dd>{new Date(rep.recorded_at).toLocaleString('vi-VN')}</dd></div></dl></div>}</article>; })}</div> : <p className="repetition-empty">Buổi tập cũ chưa có dữ liệu từng lần. Các buổi tập mới sẽ được ghi chi tiết tự động.</p>}
    </section>
    <p className="privacy-note"><ShieldCheck size={16}/> Chi tiết buổi tập này chỉ được truy xuất trong tài khoản đang đăng nhập.</p>
    {item.recommendation && <section className="surface recommendation-panel"><h3>Khuyến nghị an toàn</h3><p>{item.recommendation}</p><small>Thông tin hỗ trợ, không thay thế tư vấn của bác sĩ hoặc chuyên viên.</small></section>}
  </div>;
}
function DeepBreathingDetail({ item }: { item: any }) {
  return <div><PageTitle title="Chi tiết buổi hít thở" subtitle="DEEP_BREATHING · guided timer + quan sát chuyển động vai" /><section className="surface detail-hero"><div><span className="badge badge-success">{item.session_status}</span><h2>Hít thở sâu có hướng dẫn</h2><p><Calendar size={16}/>{new Date(item.started_at).toLocaleString('vi-VN')}</p></div></section><div className="metric-grid detail-metrics"><Mini icon={<Repeat2/>} label="Chu kỳ đã hướng dẫn" value={`${item.completed_cycles}/${item.target_cycles}`}/><Mini icon={<Clock3/>} label="Tracking" value={item.tracking_quality}/><Mini icon={<HelpCircle/>} label="Gián đoạn" value={item.interrupted_cycles}/></div><section className="surface repetition-detail"><div className="repetition-heading"><div><h3>Sự kiện buổi tập</h3><p>Kết quả mô tả số chu kỳ và chất lượng theo dõi; không phải kết luận đúng/sai hay chẩn đoán y khoa.</p></div><div className="repetition-summary"><span className="matched">Đã hướng dẫn: {item.completed_cycles}</span><span className="unassessed">Tracking: {item.tracking_quality}</span></div></div>{item.events?.length ? <div className="repetition-list">{item.events.map((event: any, index: number) => <article className="repetition-row" key={`${event.created_at}-${index}`}><span><CheckCircle2/></span><b>{event.event_type}</b><time>{event.phase || '—'} · {new Date(event.created_at).toLocaleTimeString('vi-VN')}</time></article>)}</div> : <p className="repetition-empty">Chưa có event chi tiết.</p>}</section><p className="privacy-note"><ShieldCheck size={16}/> Session chỉ thuộc tài khoản đang đăng nhập. Video gốc không được lưu.</p></div>;
}
function Mini({ icon, label, value }: { icon: ReactNode; label: string; value: string | number }) { return <div className="surface metric-card"><span>{icon}</span><div><small>{label}</small><strong>{value}</strong></div></div>; }
