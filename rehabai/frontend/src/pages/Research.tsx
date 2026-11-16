import { useCallback, useEffect, useState } from 'react';
import { Activity, Download, FlaskConical, LockKeyhole, RefreshCw, Timer, Wifi } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import { authHeaders } from '../api';

type Session = { id:string; exercise:string; start_time:string; duration_seconds:number; repetition:number; target_reps:number; status:string };
type ModelInfo = { config?: { model_name?:string; version?:string; temporal_frames?:number; provenance?:{fold_id?:string} }; metrics?: { evaluation_protocol?:string; exercise?:{macro_f1_mean?:number} } };

export default function Research() {
  const { token } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [model, setModel] = useState<ModelInfo|null>(null);
  const [health, setHealth] = useState<{model_loaded?:boolean}|null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    Promise.all([
      fetch('/api/exercise/history', {headers:authHeaders(token)}).then(r=>r.ok?r.json():Promise.reject()),
      fetch('/api/model-info').then(r=>r.ok?r.json():Promise.reject()),
      fetch('/api/health').then(r=>r.ok?r.json():Promise.reject()),
    ]).then(([history, modelInfo, healthInfo]) => { setSessions(Array.isArray(history)?history:[]); setModel(modelInfo); setHealth(healthInfo); }).catch(()=>setError('Không thể tải metadata nghiên cứu từ máy chủ.')).finally(()=>setLoading(false));
  }, [token]);
  useEffect(() => { load(); }, [load]);
  const refresh = () => { setLoading(true); setError(''); load(); };
  const latest = sessions[0]; const config = model?.config; const metrics = model?.metrics; const completed = sessions.filter(s=>s.status==='COMPLETED').length;
  return <div className="research-page">
    <header className="page-title"><span className="eyebrow"><FlaskConical size={14}/> RESEARCH MODE · RESTRICTED</span><h1>Không gian nghiên cứu</h1><p>Thông tin kỹ thuật lấy từ backend và các phiên thuộc tài khoản đang đăng nhập, không phải số liệu minh họa.</p></header>
    <div className="research-banner"><LockKeyhole size={20}/><div><strong>Không gian chỉ đọc</strong><span>Session ID chỉ hiển thị rút gọn. Không gian này không xuất video, ảnh camera hoặc dữ liệu người dùng khác.</span></div></div>
    <div className="metric-grid research-metrics"><article className="surface metric-card"><span><Activity/></span><div><small>Phiên của tài khoản</small><strong>{loading?'Đang tải…':sessions.length}</strong></div></article><article className="surface metric-card"><span><Timer/></span><div><small>Phiên hoàn thành</small><strong>{loading?'—':`${completed}/${sessions.length}`}</strong></div></article><article className="surface metric-card"><span><Wifi/></span><div><small>Backend / model</small><strong>{health?.model_loaded?'Đã kết nối':loading?'Đang kiểm tra':'Chưa sẵn sàng'}</strong></div></article><article className="surface metric-card"><span><FlaskConical/></span><div><small>Model version</small><strong>{config?`${config.model_name||'Model'} v${config.version||'?'}`:'—'}</strong></div></article></div>
    {error&&<section className="surface research-empty" role="alert"><FlaskConical size={34}/><h2>Không tải được dữ liệu</h2><p>{error}</p><button className="btn btn-secondary" onClick={refresh}><RefreshCw size={17}/> Thử lại</button></section>}
    {!error&&<div className="research-data-grid"><section className="surface research-session-card"><div className="section-heading"><div><span className="eyebrow">PHIÊN GẦN NHẤT</span><h2>{latest?.exercise||'Chưa có phiên tập'}</h2></div>{latest&&<span className={`badge ${latest.status==='COMPLETED'?'badge-success':'badge-warning'}`}>{latest.status==='COMPLETED'?'Hoàn thành':'Chưa hoàn thành'}</span>}</div>{latest?<dl><div><dt>Session ID</dt><dd>{latest.id.slice(0,8)}…</dd></div><div><dt>Thời gian</dt><dd>{new Date(latest.start_time).toLocaleString('vi-VN')}</dd></div><div><dt>Số lần</dt><dd>{latest.repetition}/{latest.target_reps}</dd></div><div><dt>Thời lượng</dt><dd>{latest.duration_seconds}s</dd></div></dl>:<p className="research-muted">Hãy hoàn thành một buổi tập để tạo metadata phiên.</p>}{latest&&<Link className="btn btn-secondary" to={`/app/history/${latest.id}`}>Mở chi tiết phiên</Link>}</section><section className="surface research-session-card"><div className="section-heading"><div><span className="eyebrow">ARTIFACT ĐANG DÙNG</span><h2>{config?.model_name||'Chưa tải được model'}</h2></div></div><dl><div><dt>Version</dt><dd>{config?.version||'—'}</dd></div><div><dt>LOSO fold</dt><dd>{config?.provenance?.fold_id||'—'}</dd></div><div><dt>Temporal frames</dt><dd>{config?.temporal_frames||'—'}</dd></div><div><dt>Macro-F1</dt><dd>{metrics?.exercise?.macro_f1_mean==null?'—':`${(metrics.exercise.macro_f1_mean*100).toFixed(2)}%`}</dd></div></dl><p className="research-muted">{metrics?.evaluation_protocol||'Không có thông tin giao thức.'}</p></section></div>}
    <section className="surface research-disclosure"><strong>Phạm vi dữ liệu hiện có</strong><p>Backend hiện lưu metadata buổi tập, số lần, mức đau và nhận diện theo phiên. Latency inference, tracking quality từng frame và WebSocket event log chưa được lưu bền vững nên không hiển thị số giả.</p><button className="btn btn-secondary" onClick={()=>window.print()} disabled={!latest}><Download size={17}/> In báo cáo metadata</button></section>
  </div>;
}
