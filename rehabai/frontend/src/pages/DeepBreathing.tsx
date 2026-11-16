import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Camera, CircleStop, Pause, Play, RotateCcw, ShieldCheck, Wind } from 'lucide-react';
import { useAuth } from '../auth';
import { authHeaders } from '../api';

type Config = { inhale_seconds: number; hold_seconds: number; exhale_seconds: number; rest_seconds: number; target_cycles: number; cycle_seconds?: number };
type Update = { type: string; phase: string; cycle_index: number; completed_cycles: number; interrupted_cycles: number; tracking_quality: string; signal_quality: string; phase_confidence: string; elapsed_seconds: number; event?: string | null };

const labels: Record<string, string> = { IDLE: 'Sẵn sàng', READY: 'Chuẩn bị', INHALE: 'Hít vào', HOLD: 'Giữ nhẹ', EXHALE: 'Thở ra', REST: 'Nghỉ', UNKNOWN: 'Chưa xác định', TRACKING_INSUFFICIENT: 'Chưa thấy rõ vai', PAUSED: 'Đã tạm dừng', COMPLETED: 'Hoàn tất hướng dẫn' };
const trackingLabels: Record<string, string> = { GOOD: 'Theo dõi tốt', MEDIUM: 'Theo dõi trung bình', POOR: 'Cần điều chỉnh vị trí', UNAVAILABLE: 'Không có dữ liệu camera' };

function phaseLabel(phase: string) { return labels[phase] || phase; }

export default function DeepBreathing() {
  const { token } = useAuth();
  const apiBase = import.meta.env.VITE_API_BASE || '';
  const wsBase = (import.meta.env.VITE_WS_BASE || `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`).replace(/\/$/, '');
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const captureTimerRef = useRef<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const sessionRef = useRef<string | null>(null);
  const startedAtRef = useRef<number | null>(null);
  const pauseStartedAtRef = useRef<number | null>(null);
  const pausedDurationRef = useRef(0);
  const finishedRequestedRef = useRef(false);
  const pausedRef = useRef(false);
  const timerOnlyRef = useRef(false);
  const [config, setConfig] = useState<Config>({ inhale_seconds: 4, hold_seconds: 0, exhale_seconds: 6, rest_seconds: 0, target_cycles: 6 });
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const [cameraAvailable, setCameraAvailable] = useState<boolean | null>(null);
  // getUserMedia resolves asynchronously after the video element is mounted.
  // Track readiness so the stream is attached even when it resolves later.
  const [streamReady, setStreamReady] = useState(false);
  const [timerOnly, setTimerOnly] = useState(false);
  const [update, setUpdate] = useState<Update>({ type: 'BREATH_PHASE', phase: 'IDLE', cycle_index: 0, completed_cycles: 0, interrupted_cycles: 0, tracking_quality: 'UNAVAILABLE', signal_quality: 'UNKNOWN', phase_confidence: 'UNKNOWN', elapsed_seconds: 0 });
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState('');
  const [finished, setFinished] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => { pausedRef.current = paused; }, [paused]);
  useEffect(() => { timerOnlyRef.current = timerOnly; }, [timerOnly]);

  // The video element is rendered only after `running` becomes true. Attach
  // the stream in an effect after that render; attaching it in `start()` was
  // a race where videoRef.current was still null and no frames were sent.
  useEffect(() => {
    if (!running || !streamReady || !streamRef.current || !videoRef.current) return;
    const video = videoRef.current;
    if (video.srcObject !== streamRef.current) video.srcObject = streamRef.current;
    void video.play().catch(() => setError('Camera đã được cấp quyền nhưng trình duyệt chưa phát được hình. Hãy tải lại trang hoặc đóng ứng dụng khác đang dùng camera.'));
  }, [running, streamReady]);

  const cleanup = useCallback(() => {
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = null;
    if (captureTimerRef.current) window.clearInterval(captureTimerRef.current);
    captureTimerRef.current = null;
    streamRef.current?.getTracks().forEach(track => track.stop());
    streamRef.current = null;
    setStreamReady(false);
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  useEffect(() => () => cleanup(), [cleanup]);

  useEffect(() => {
    fetch(`${apiBase}/api/deep-breathing/config`, { headers: authHeaders(token) })
      .then(res => res.ok ? res.json() : null)
      .then(value => { if (value) setConfig(value); })
      .catch(() => { /* defaults remain usable */ });
  }, [apiBase, token]);

  const createSession = useCallback(async () => {
    const response = await fetch(`${apiBase}/api/deep-breathing/sessions`, { method: 'POST', headers: authHeaders(token, true), body: JSON.stringify({}) });
    if (!response.ok) throw new Error('Không thể tạo buổi tập.');
    const value = await response.json();
    sessionRef.current = value.session_id;
    setSessionId(value.session_id);
    return value.session_id as string;
  }, [apiBase, token]);

  const finish = useCallback(async (status: string = 'COMPLETED', mode = timerOnlyRef.current) => {
    if (!sessionRef.current || saving) return;
    setSaving(true);
    try {
      const response = await fetch(`${apiBase}/api/deep-breathing/sessions/${sessionRef.current}/finish`, { method: 'POST', headers: authHeaders(token, true), body: JSON.stringify({ session_status: status, tracking_mode: mode ? 'GUIDED_TIMER_ONLY' : 'POSE_SHOULDER', guided_cycles_completed: update.completed_cycles }) });
      if (!response.ok) throw new Error('Không thể lưu kết quả buổi tập.');
      setFinished(true);
      cleanup();
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Không thể lưu kết quả.'); }
    finally { setSaving(false); }
  }, [apiBase, cleanup, saving, token, update.completed_cycles]);

  const sendFrames = useCallback((id: string) => {
    const ws = new WebSocket(`${wsBase}/ws/deep-breathing/${encodeURIComponent(id)}?token=${encodeURIComponent(token || '')}`);
    wsRef.current = ws;
    ws.onmessage = event => {
      try { const value = JSON.parse(event.data) as Update & { type: string; code?: string; message?: string }; if (value.type === 'ERROR') { setError(value.message || 'Camera tạm thời không phân tích được.'); if (value.code === 'CAMERA_UNAVAILABLE') { timerOnlyRef.current = true; setTimerOnly(true); setCameraAvailable(false); setUpdate(current => ({ ...current, tracking_quality: 'UNAVAILABLE', signal_quality: 'UNKNOWN' })); ws.close(); } return; } setUpdate(value); setElapsed(value.elapsed_seconds); } catch { setError('Phản hồi camera không hợp lệ.'); }
    };
    ws.onerror = () => { timerOnlyRef.current = true; setTimerOnly(true); setCameraAvailable(false); setError('Kết nối theo dõi camera bị gián đoạn. Đã chuyển sang timer-only; tracking unavailable.'); };
    ws.onclose = () => { if (running && !finished && !timerOnlyRef.current) setError('Theo dõi camera đã ngắt kết nối trước khi nhận được khung hình. Hãy kiểm tra quyền camera và kết nối.'); };
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    const capture = () => {
      if (!context || !canvas || !videoRef.current || ws.readyState !== WebSocket.OPEN || pausedRef.current) return;
      context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
      const logicalTimestamp = Date.now() - pausedDurationRef.current;
      ws.send(JSON.stringify({ session_id: id, timestamp: logicalTimestamp, frame: canvas.toDataURL('image/jpeg', 0.62).split(',')[1] }));
    };
    const captureTimer = window.setInterval(capture, 1000 / 12);
    captureTimerRef.current = captureTimer;
    return () => { window.clearInterval(captureTimer); ws.close(); };
  }, [finished, running, token, wsBase]);

  const start = useCallback(async () => {
    const requestedTimerOnly = timerOnlyRef.current;
    setError(''); setFinished(false); setPaused(false); pausedRef.current = false; pauseStartedAtRef.current = null; pausedDurationRef.current = 0; finishedRequestedRef.current = false; setUpdate(value => ({ ...value, phase: 'READY', completed_cycles: 0, interrupted_cycles: 0, elapsed_seconds: 0 }));
    try {
      const id = await createSession();
      // Mount the video before requesting/attaching the stream.
      setRunning(true);
      let stream: MediaStream | null = null;
      if (!requestedTimerOnly) {
        try {
          if (!window.isSecureContext && !['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname)) {
            throw Object.assign(new Error('Camera cần HTTPS hoặc localhost.'), { name: 'InsecureContextError' });
          }
          if (!navigator.mediaDevices?.getUserMedia) {
            throw Object.assign(new Error('Trình duyệt không cung cấp getUserMedia.'), { name: 'UnsupportedError' });
          }
          stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }, audio: false });
        } catch (cause) {
          const name = cause instanceof DOMException || cause instanceof Error ? cause.name : 'UnknownError';
          const message = name === 'NotAllowedError' || name === 'SecurityError'
            ? 'Camera bị từ chối hoặc trang chưa được cấp quyền. Hãy bấm biểu tượng khóa trên thanh địa chỉ → Camera → Cho phép, sau đó tải lại trang.'
            : name === 'NotFoundError'
              ? 'Không tìm thấy camera trên thiết bị.'
              : name === 'NotReadableError' || name === 'AbortError'
                ? 'Camera đang được ứng dụng khác sử dụng. Hãy đóng ứng dụng đó rồi thử lại.'
                : name === 'InsecureContextError'
                  ? 'Camera chỉ hoạt động trên HTTPS hoặc localhost. Không mở bằng địa chỉ HTTP của máy khác.'
                  : name === 'UnsupportedError'
                    ? 'Trình duyệt hiện tại không hỗ trợ camera API.'
                    : 'Không thể mở camera. Đã chuyển sang guided timer-only; tracking unavailable.';
          setCameraAvailable(false); setTimerOnly(true); timerOnlyRef.current = true; setError(`${message} (mã: ${name})`);
        }
      } else { setCameraAvailable(false); setTimerOnly(true); }
      if (stream) {
        setCameraAvailable(true); streamRef.current = stream; setStreamReady(true);
      }
      startedAtRef.current = performance.now();
      timerRef.current = window.setInterval(() => {
        if (pausedRef.current || !startedAtRef.current) return;
        const seconds = (performance.now() - startedAtRef.current - pausedDurationRef.current) / 1000;
        if (timerOnlyRef.current) {
          setElapsed(seconds);
          const cycleSeconds = config.inhale_seconds + config.hold_seconds + config.exhale_seconds + config.rest_seconds;
          const completed = Math.min(Math.floor(seconds / cycleSeconds), config.target_cycles);
          const within = seconds % cycleSeconds;
          const phase = within < config.inhale_seconds ? 'INHALE' : within < config.inhale_seconds + config.hold_seconds ? 'HOLD' : within < config.inhale_seconds + config.hold_seconds + config.exhale_seconds ? 'EXHALE' : 'REST';
          setUpdate(value => ({ ...value, phase: completed >= config.target_cycles ? 'COMPLETED' : phase, cycle_index: Math.min(completed + 1, config.target_cycles), completed_cycles: completed, tracking_quality: 'UNAVAILABLE', signal_quality: 'UNKNOWN', elapsed_seconds: seconds }));
        }
      }, 200);
      if (stream) sendFrames(id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Không thể bắt đầu bài tập.'); cleanup(); }
  }, [cleanup, config, createSession, sendFrames]);

  const togglePause = () => {
    const now = performance.now();
    setPaused(value => {
      const next = !value;
      pausedRef.current = next;
      if (next) pauseStartedAtRef.current = now;
      else if (pauseStartedAtRef.current !== null) { pausedDurationRef.current += now - pauseStartedAtRef.current; pauseStartedAtRef.current = null; }
      return next;
    });
  };
  const stop = () => { void finish('INTERRUPTED'); };
  const reset = () => { cleanup(); sessionRef.current = null; finishedRequestedRef.current = false; timerOnlyRef.current = false; setTimerOnly(false); setStreamReady(false); setSessionId(null); setRunning(false); setFinished(false); setElapsed(0); setUpdate(value => ({ ...value, phase: 'IDLE', completed_cycles: 0, interrupted_cycles: 0, elapsed_seconds: 0 })); };
  const phaseSeconds = update.phase === 'INHALE' ? config.inhale_seconds : update.phase === 'HOLD' ? config.hold_seconds : update.phase === 'EXHALE' ? config.exhale_seconds : config.rest_seconds;
  const cycleDuration = config.inhale_seconds + config.hold_seconds + config.exhale_seconds + config.rest_seconds;
  const cycleElapsed = elapsed % Math.max(cycleDuration, 1);
  const phaseElapsed = update.phase === 'INHALE' ? cycleElapsed
    : update.phase === 'HOLD' ? Math.max(0, cycleElapsed - config.inhale_seconds)
    : update.phase === 'EXHALE' ? Math.max(0, cycleElapsed - config.inhale_seconds - config.hold_seconds)
    : Math.max(0, cycleElapsed - config.inhale_seconds - config.hold_seconds - config.exhale_seconds);
  const phaseRemaining = update.phase === 'READY' ? Math.max(0, Math.ceil(config.inhale_seconds)) : Math.max(0, Math.ceil(phaseSeconds - phaseElapsed));
  const circleScale = useMemo(() => update.phase === 'INHALE' ? 1.18 : update.phase === 'EXHALE' ? .82 : 1, [update.phase]);

  useEffect(() => {
    if (!running || finished || finishedRequestedRef.current || update.completed_cycles < config.target_cycles) return;
    finishedRequestedRef.current = true;
    void finish('COMPLETED', timerOnlyRef.current);
  }, [config.target_cycles, finish, finished, running, update.completed_cycles]);

  return <div className="deep-breathing-page">
    <div className="deep-breathing-header"><div><span className="badge badge-info"><Wind size={14} /> GUIDED BREATHING</span><h1>Hít thở sâu có hướng dẫn</h1><p>Chuyển động vai chỉ là tín hiệu quan sát hỗ trợ, không phải đo chức năng hô hấp hay chẩn đoán y khoa.</p></div><div className="deep-breathing-safety"><ShieldCheck size={20} /><span>Không lưu video gốc</span></div></div>
    <div className="deep-breathing-alert deep-breathing-safety-alert" role="note">Dừng bài tập ngay nếu chóng mặt, đau ngực, khó thở bất thường hoặc có triệu chứng đáng lo; hãy tìm hỗ trợ y tế phù hợp.</div>
    {error && <div className="deep-breathing-alert" role="alert">{error}</div>}
    {!running && !finished && <section className="glass-card deep-breathing-start"><div className="deep-breathing-protocol"><strong>Protocol v1</strong><span>Hít {config.inhale_seconds}s · Thở {config.exhale_seconds}s · {config.target_cycles} chu kỳ</span></div><p>Ngồi đối diện camera, để hai vai và thân trên nằm rõ trong khung. Bạn có thể bật timer-only nếu thiết bị không cho phép camera.</p><div style={{ margin: '.8rem 0' }}><small style={{ color: 'var(--muted)', fontSize: '.78rem' }}>Video mẫu — xem trước nhịp thở khi vận động</small><video controls playsInline preload="metadata" src="/videos/huong-dan-gap-khuyu-tay.mp4" aria-label="Video mẫu hướng dẫn hít thở sâu" style={{ width: '100%', maxWidth: '340px', display: 'block', margin: '.4rem 0 0', borderRadius: '.6rem', background: '#000' }} /></div><label className="deep-breathing-fallback"><input type="checkbox" checked={timerOnly} onChange={event => { timerOnlyRef.current = event.target.checked; setTimerOnly(event.target.checked); }} /> Bắt đầu bằng guided timer-only (tracking unavailable)</label><button className="btn btn-primary" type="button" onClick={() => void start()}><Play size={17} /> Bắt đầu</button></section>}
    {(running || finished) && <section className="deep-breathing-workspace"><div className="glass-card deep-breathing-stage"><div className="deep-breathing-stage-top"><span className="badge badge-info">{phaseLabel(update.phase)}</span><span>Chu kỳ {Math.min(update.cycle_index || 1, config.target_cycles)}/{config.target_cycles}</span></div><div className={`deep-breathing-circle phase-${update.phase.toLowerCase()}`} style={{ transform: `scale(${circleScale})`, transitionDuration: `${Math.max(phaseSeconds, 1)}s` }}><span>{phaseLabel(update.phase)}</span><b>{phaseRemaining}</b></div><p className="deep-breathing-instruction">{paused ? 'Buổi tập đang tạm dừng.' : update.phase === 'READY' && !timerOnly ? 'Giữ yên trong khung để hiệu chỉnh vị trí vai.' : timerOnly ? 'Guided timer đang chạy — tracking unavailable' : trackingLabels[update.tracking_quality] || 'Đang theo dõi'}</p><div className="deep-breathing-actions">{!finished && <><button className="btn btn-outline" type="button" onClick={togglePause}>{paused ? <Play size={16} /> : <Pause size={16} />}{paused ? 'Tiếp tục' : 'Tạm dừng'}</button><button className="btn btn-danger" type="button" onClick={stop}><CircleStop size={16} /> Dừng</button></>}{finished && <button className="btn btn-primary" type="button" onClick={reset}><RotateCcw size={16} /> Tập lại</button>}</div></div><div className="glass-card deep-breathing-camera"><video ref={videoRef} muted playsInline aria-label="Camera theo dõi vai" /><canvas ref={canvasRef} width={640} height={480} hidden />{(!cameraAvailable || timerOnly) && <div className="deep-breathing-camera-overlay"><Camera size={25} /><span>{timerOnly ? 'Timer-only · tracking unavailable' : 'Camera chưa sẵn sàng'}</span></div>}</div><div className="deep-breathing-stats glass-card"><div><span>Đã hoàn thành</span><strong>{update.completed_cycles}/{config.target_cycles}</strong></div><div><span>Chu kỳ gián đoạn</span><strong>{update.interrupted_cycles}</strong></div><div><span>Chất lượng tracking</span><strong>{timerOnly ? 'UNAVAILABLE' : update.tracking_quality}</strong></div><small>Chất lượng tracking không phải đánh giá đúng/sai y khoa.</small></div></section>}
    {sessionId && !finished && <p className="deep-breathing-session-id">Session: {sessionId}</p>}
  </div>;
}
