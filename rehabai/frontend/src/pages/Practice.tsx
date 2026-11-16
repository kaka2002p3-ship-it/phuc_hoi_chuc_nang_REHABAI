import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Camera, CheckCircle, Minus, Play, Plus, Pause, RotateCcw, Video, ShieldCheck, SkipForward } from 'lucide-react';
import { useAuth } from '../auth';
import { authHeaders } from '../api';
import { ClinicalDisclaimer } from '../components/ClinicalDisclaimer';
import { useUiHideSettings } from '../ui-hide-settings';

const DEFAULT_TARGET_REPS = 5;
const MIN_TARGET_REPS = 1;
const MAX_TARGET_REPS = 30;
const PREDICTION_CONFIRMATIONS = 2;
const ENABLED_EXERCISE_IDS = new Set([2, 4, 6]);
const names: Record<number, string> = {
  1: 'Vai - Nâng vật',
  2: 'Khuỷu tay - Gập/duỗi khuỷu tay',
  3: 'Cổ tay - Gập/duỗi cổ tay',
  4: 'Bàn tay - Mở bàn tay',
  6: 'Cổ - Nghiêng cổ sang hai bên',
};

const tutorials: Record<number, { video: string; tips: string[] }> = {
  2: {
    video: '/videos/huong-dan-gap-khuyu-tay.mp4',
    tips: [
      'Giữ cánh tay sát thân người và thả lỏng vai.',
      'Gập, duỗi khuỷu tay chậm rãi trong phạm vi không gây đau.',
      'Đứng đủ xa để camera nhìn rõ vai, khuỷu tay và cổ tay.',
    ],
  },
  4: {
    video: '/videos/huong-dan-mo-ban-tay.mp4',
    tips: [
      'Đưa toàn bộ bàn tay vào giữa khung hình.',
      'Mở các ngón tay từ từ, không giật hoặc vung cổ tay.',
      'Giữ cổ tay ổn định và dừng lại nếu mức đau tăng.',
    ],
  },
  6: {
    video: '/videos/huong-dan-mo-ban-tay.mp4',
    tips: [
      'Giữ đầu và hai vai nằm rõ trong khung hình, nhìn thẳng để hiệu chỉnh.',
      'Nghiêng đầu nhẹ sang một bên, giữ vai tương đối ổn định và giữ tư thế theo hướng dẫn.',
      'Quay lại chính giữa để hoàn tất một lần; dừng nếu đau, tê hoặc chóng mặt.',
    ],
  },
};

export default function Practice() {
  const { token } = useAuth();
  const uiHide = useUiHideSettings();
  const { id } = useParams();
  const navigate = useNavigate();
  const exerciseId = Number.parseInt(id || '1', 10);
  const tutorialRef = useRef<HTMLVideoElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const sessionRef = useRef<string | null>(null);
  const assessmentOpenRef = useRef(false);
  const targetRepsRef = useRef(DEFAULT_TARGET_REPS);
  const statusRef = useRef('Chuẩn bị buổi tập');
  const completedRepsRef = useRef(0);
  const predictionCandidateRef = useRef({ exerciseId: 0, count: 0 });
  const acceptedPredictionRef = useRef(0);
  const pausedRef = useRef(false);
  const maxTutorialTimeRef = useRef(0);

  const [status, setStatus] = useState('Chuẩn bị buổi tập');
  const [recognizedExercise, setRecognizedExercise] = useState(exerciseId === 6 ? 'Rule-based geometry' : 'Đang chờ dữ liệu nhận diện...');
  const [recognitionConfidence, setRecognitionConfidence] = useState<number | null>(null);
  const [liveAssessment, setLiveAssessment] = useState<'matched' | 'mismatched' | 'unassessed'>(exerciseId === 6 ? 'matched' : 'unassessed');
  const [landmarkRate, setLandmarkRate] = useState<number | null>(null);
  const [qualityReason, setQualityReason] = useState('Đang chờ đủ dữ liệu camera.');
  const [completedReps, setCompletedReps] = useState(0);
  const [formFeedback, setFormFeedback] = useState<{ pace?: string; angle?: string; label?: string } | null>(null);
  const [targetReps, setTargetReps] = useState(DEFAULT_TARGET_REPS);
  const [painBefore, setPainBefore] = useState<number | null>(null);
  const [painAfter, setPainAfter] = useState<number | null>(null);
  const [showFinish, setShowFinish] = useState(false);
  const [completedAutomatically, setCompletedAutomatically] = useState(false);
  const [started, setStarted] = useState(false);
  const [cameraChecking, setCameraChecking] = useState(false);
  const [cameraStreamReady, setCameraStreamReady] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraCheckMessage, setCameraCheckMessage] = useState(exerciseId === 6
    ? 'Đã đọc hướng dẫn. Bạn có thể chuyển sang kiểm tra camera.'
    : 'Xem hết video hướng dẫn để mở khóa bước kiểm tra camera.');
  const [finishResult, setFinishResult] = useState<any>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [finishError, setFinishError] = useState('');
  const [startError, setStartError] = useState('');
  const [paused, setPaused] = useState(false);
  const [timeline, setTimeline] = useState<{rep:number;timestamp:string}[]>([]);
  const [tutorialCompleted, setTutorialCompleted] = useState(exerciseId === 6);
  const [tutorialSkipped, setTutorialSkipped] = useState(false);
  const [tutorialProgress, setTutorialProgress] = useState(0);
  const [cameraResolution, setCameraResolution] = useState('640x480');

  const apiBase = import.meta.env.VITE_API_BASE || '';
  const wsBase = (import.meta.env.VITE_WS_BASE || `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`).replace(/\/$/, '');
  const tutorial = tutorials[exerciseId];
  const hasTutorialVideo = Boolean(tutorial?.video);

  // The preview element is mounted only after cameraChecking becomes true.
  // Attach the stream in an effect so getUserMedia resolving quickly cannot
  // race the React render and leave the user with no visible preview.
  useEffect(() => {
    if (started || !cameraChecking || !cameraStreamReady || !streamRef.current || !videoRef.current) return;
    const player = videoRef.current;
    if (player.srcObject !== streamRef.current) player.srcObject = streamRef.current;
    void player.play().catch(() => {
      setCameraCheckMessage('Camera đã được cấp quyền nhưng chưa phát được hình. Hãy đóng ứng dụng khác đang dùng camera rồi thử lại.');
      setCameraChecking(false);
    });
  }, [cameraChecking, cameraStreamReady, started]);

  const cameraSize = useCallback(() => {
    const [width, height] = cameraResolution.split('x').map(Number);
    return Number.isFinite(width) && Number.isFinite(height)
      ? { width, height }
      : { width: 640, height: 480 };
  }, [cameraResolution]);

  useEffect(() => {
    let active = true;
    fetch(`${apiBase}/api/settings`, { headers: authHeaders(token) })
      .then(response => response.ok ? response.json() : null)
      .then(settings => {
        if (active && typeof settings?.camera_resolution === 'string') setCameraResolution(settings.camera_resolution);
      })
      .catch(() => { /* Giữ cấu hình tương thích mặc định nếu không tải được. */ });
    return () => { active = false; };
  }, [apiBase, token]);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    wsRef.current?.close();
    wsRef.current = null;
    setCameraStreamReady(false);
  }, []);

  const updateStatus = useCallback((nextStatus: string) => {
    if (statusRef.current === nextStatus) return;
    statusRef.current = nextStatus;
    setStatus(nextStatus);
  }, []);

  const updateTargetReps = (value: number) => {
    const nextValue = Math.min(MAX_TARGET_REPS, Math.max(MIN_TARGET_REPS, Math.round(value) || MIN_TARGET_REPS));
    setTargetReps(nextValue);
    targetRepsRef.current = nextValue;
  };

  const updateTutorialProgress = () => {
    const player = tutorialRef.current;
    if (!player || !Number.isFinite(player.duration) || player.duration <= 0) return;

    // Không cho tua thẳng đến cuối để bỏ qua nội dung hướng dẫn.
    if (!tutorialCompleted && player.currentTime > maxTutorialTimeRef.current + 1.25) {
      player.currentTime = maxTutorialTimeRef.current;
      return;
    }
    maxTutorialTimeRef.current = Math.max(maxTutorialTimeRef.current, player.currentTime);
    setTutorialProgress(Math.min(100, Math.round((maxTutorialTimeRef.current / player.duration) * 100)));
  };

  const completeTutorial = () => {
    const player = tutorialRef.current;
    if (player?.duration) maxTutorialTimeRef.current = player.duration;
    setTutorialProgress(100);
    setTutorialSkipped(false);
    setTutorialCompleted(true);
    setCameraCheckMessage('Đã xem hướng dẫn. Bạn có thể chuyển sang kiểm tra camera.');
  };

  const skipTutorial = () => {
    tutorialRef.current?.pause();
    setTutorialSkipped(true);
    setTutorialCompleted(true);
    setCameraCheckMessage('Đã bỏ qua video. Bạn có thể chuyển sang kiểm tra camera.');
  };

  const replayTutorial = () => {
    const player = tutorialRef.current;
    if (!player) return;
    setTutorialSkipped(false);
    setTutorialCompleted(false);
    setTutorialProgress(0);
    maxTutorialTimeRef.current = 0;
    player.currentTime = 0;
    void player.play();
  };

  const openPainAssessment = useCallback((automatic: boolean) => {
    if (assessmentOpenRef.current) return;
    assessmentOpenRef.current = true;
    setPainAfter(null);
    setCompletedAutomatically(automatic);
    setShowFinish(true);
    const goal = targetRepsRef.current;
    updateStatus(automatic ? `Hoàn thành bài tập ${goal}/${goal}` : 'Đã kết thúc bài tập');
    stopCamera();
  }, [stopCamera, updateStatus]);

  const drawSkeleton = useCallback((skeleton: any) => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, 640, 480);
    const draw = (items: any[], color: string) => {
      if (!Array.isArray(items)) return;
      ctx.fillStyle = color;
      items.forEach((lm: any) => {
        const x = Array.isArray(lm) ? lm[0] : lm.x;
        const y = Array.isArray(lm) ? lm[1] : lm.y;
        if (Number.isFinite(x) && Number.isFinite(y) && (x !== 0 || y !== 0)) {
          ctx.beginPath();
          ctx.arc(x * 640, y * 480, 3, 0, 2 * Math.PI);
          ctx.fill();
        }
      });
    };
    draw(skeleton.pose, '#10b981');
    draw(skeleton.left_hand, '#3b82f6');
    draw(skeleton.right_hand, '#8b5cf6');
  }, []);

  const startStreaming = useCallback((sessionUuid: string) => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 640;
    canvas.height = 480;
    const sendFrame = () => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
      if (!pausedRef.current && videoRef.current && ctx) {
        ctx.drawImage(videoRef.current, 0, 0, 640, 480);
        wsRef.current.send(JSON.stringify({
          timestamp: Date.now(),
          session_id: sessionUuid,
          frame: canvas.toDataURL('image/jpeg', 0.6).split(',')[1],
        }));
      }
      window.setTimeout(sendFrame, 1000 / 15);
    };
    sendFrame();
  }, []);

  const connectWebSocket = useCallback((sessionUuid: string) => {
    const ws = new WebSocket(`${wsBase}/ws/inference?token=${encodeURIComponent(token || '')}`);
    wsRef.current = ws;
    ws.onopen = () => {
      updateStatus('Sẵn sàng tập luyện');
      startStreaming(sessionUuid);
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.skeleton) drawSkeleton(data.skeleton);
      if (data.quality) {
        const rate = Number(data.quality.landmark_rate);
        setLandmarkRate(Number.isFinite(rate) ? rate : null);
        if (data.quality.ready) setQualityReason('Đã đủ dữ liệu camera để nhận diện.');
        else if (data.quality.code === 'collecting_window') setQualityReason('Đang thu thập thêm khung hình ổn định.');
        else if (typeof data.quality.message_vi === 'string') setQualityReason(data.quality.message_vi);
      }

      if (data.quality && !data.quality.ready && !data.inference) {
        const qualityStatus = data.quality.code === 'collecting_window'
          ? 'Đang thu thập chuyển động...'
          : data.quality.message_vi;
        updateStatus(qualityStatus);
      } else if (data.inference) {
        if (data.inference.assessment === 'matched' || data.inference.assessment === 'mismatched' || data.inference.assessment === 'unassessed') setLiveAssessment(data.inference.assessment);
        const predictedId = Number(data.inference.exercise_id) || 0;
        const candidate = predictionCandidateRef.current;
        if (candidate.exerciseId === predictedId) {
          candidate.count += 1;
        } else {
          predictionCandidateRef.current = { exerciseId: predictedId, count: 1 };
        }

        if (predictionCandidateRef.current.count >= PREDICTION_CONFIRMATIONS) {
          acceptedPredictionRef.current = predictedId;
          setRecognizedExercise(data.inference.exercise_name_vi || names[predictedId] || 'Không xác định');
          const nextConfidence = Number(data.inference.confidence);
          if (Number.isFinite(nextConfidence)) setRecognitionConfidence(nextConfidence);
          updateStatus(predictedId === exerciseId
            ? 'Đang theo dõi động tác'
            : `Hãy thực hiện đúng bài: ${names[exerciseId]}`);
        }
      }

      if (data.rep?.rep_count !== undefined) {
        if (exerciseId === 6) {
          setRecognizedExercise('NECK_LATERAL_STRETCH · Rule-based geometry');
          setLiveAssessment('matched');
          const neckState = String(data.rep.state || '');
          const neckMessages: Record<string, string> = {
            CENTER: 'Giữ ở chính giữa.', MOVING_LEFT: 'Nghiêng nhẹ sang trái.', MOVING_RIGHT: 'Nghiêng nhẹ sang phải.',
            HOLD_LEFT: 'Giữ tư thế bên trái.', HOLD_RIGHT: 'Giữ tư thế bên phải.',
            RETURNING_FROM_LEFT: 'Từ từ trở về chính giữa.', RETURNING_FROM_RIGHT: 'Từ từ trở về chính giữa.',
            TRACKING_INSUFFICIENT: 'Chưa thấy rõ tai và vai — hãy chỉnh lại khung hình.',
          };
          updateStatus(neckMessages[neckState] || 'Đang theo dõi bằng hình học cổ-vai');
          setQualityReason(data.rep.tracking_quality === 'POOR' ? 'Tracking chưa đủ ổn định.' : data.rep.compensation_detected ? 'Giữ hai vai tương đối ổn định.' : 'Tracking tốt · không dùng classifier đã train.');
        }
        const goal = targetRepsRef.current;
        const nextCount = Math.min(goal, Number(data.rep.rep_count) || 0);
        if (completedRepsRef.current !== nextCount) {
          completedRepsRef.current = nextCount;
          setCompletedReps(nextCount);
          if (nextCount > 0) setTimeline(items => items.some(item => item.rep === nextCount) ? items : [...items, { rep: nextCount, timestamp: new Date().toLocaleTimeString('vi-VN') }]);
        }
        if (nextCount >= goal) openPainAssessment(true);
      }

      // Rule-based form/pace check: latest completed repetition cycle.
      if (Array.isArray(data.form_quality) && data.form_quality.length) {
        const latest = data.form_quality[data.form_quality.length - 1];
        const paceLabels: Record<string, string> = { ok: 'Tốc độ phù hợp', too_fast: 'Tập nhanh hơn khuyến nghị', too_slow: 'Tập chậm hơn khuyến nghị', unknown: 'Đang đo tốc độ' };
        const angleLabels: Record<string, string> = { ok: 'Biên độ (góc) đạt yêu cầu', short_range: 'Biên độ góc chưa đủ — tập đầy hơn nếu không đau', unknown: 'Đang đo biên độ' };
        setFormFeedback({
          pace: latest.pace, angle: latest.angle,
          label: `${latest.rep ?? ''} · ${paceLabels[latest.pace] || ''}${latest.angle && latest.angle !== 'unknown' ? ` · ${angleLabels[latest.angle]}` : ''}`,
        });
      }
    };
    ws.onclose = () => {
      if (!assessmentOpenRef.current) updateStatus('Mất kết nối AI');
    };
  }, [drawSkeleton, exerciseId, openPainAssessment, startStreaming, token, updateStatus, wsBase]);

  const startCameraCheck = useCallback(async () => {
    if (!tutorialCompleted) {
      setCameraCheckMessage('Hãy xem hết video hướng dẫn trước khi kiểm tra camera.');
      return;
    }
    tutorialRef.current?.pause();
    setCameraChecking(true);
    setCameraReady(false);
    setCameraCheckMessage('Đang xin quyền truy cập camera...');
    try {
      const size = cameraSize();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: size.width }, height: { ideal: size.height }, facingMode: 'user' },
      });
      streamRef.current = stream;
      setCameraStreamReady(true);
      const ws = new WebSocket(`${wsBase}/ws/inference?token=${encodeURIComponent(token || '')}`);
      wsRef.current = ws;
      ws.addEventListener('error', () => {
        setCameraCheckMessage('Không kết nối được máy chủ AI. Vui lòng kiểm tra backend có đang chạy không (port 8000).');
      });
      ws.addEventListener('close', (event) => {
        if (event.code === 1008) {
          setCameraCheckMessage('Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.');
        } else if (event.code !== 1000 && !cameraReady) {
          setCameraCheckMessage(`Kết nối bị ngắt (code: ${event.code}). Hãy thử lại.`);
        }
      });
      ws.onopen = () => {
        setCameraCheckMessage('Đã bật camera. Hãy đứng trong khung hình...');
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 480;
        const ctx = canvas.getContext('2d');
        const sendPreview = () => {
          if (wsRef.current !== ws || ws.readyState !== WebSocket.OPEN) return;
          if (videoRef.current && ctx) {
            ctx.drawImage(videoRef.current, 0, 0, 640, 480);
            ws.send(JSON.stringify({ timestamp: Date.now(), preview: true, exercise_id: exerciseId, frame: canvas.toDataURL('image/jpeg', 0.6).split(',')[1] }));
          }
          window.setTimeout(sendPreview, 1000 / 10);
        };
        sendPreview();
      };
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.skeleton) {
          drawSkeleton(data.skeleton);
          const pose = Array.isArray(data.skeleton.pose) ? data.skeleton.pose : [];
          const leftHand = Array.isArray(data.skeleton.left_hand) ? data.skeleton.left_hand : [];
          const rightHand = Array.isArray(data.skeleton.right_hand) ? data.skeleton.right_hand : [];
          const visible = (index: number) => Array.isArray(pose[index]) && pose[index].some((value: number) => Math.abs(value) > 1e-6);
          const hasPose = exerciseId === 6 ? [7, 8, 11, 12].every(visible) : [11, 13, 15].every(visible) || [12, 14, 16].every(visible);
          const hasHand = [leftHand, rightHand].some((hand) => hand.some((point: number[]) => point.some((value) => Math.abs(value) > 1e-6)));
          const landmarksReady = exerciseId === 4 ? hasHand : hasPose;
          const qualityReady = Boolean(data.quality?.ready) && landmarksReady;
          if (qualityReady) {
            setCameraReady(true);
            setCameraCheckMessage('Camera đạt yêu cầu. Bạn có thể bắt đầu tập.');
          } else if (data.quality?.message_vi) {
            setCameraCheckMessage(exerciseId === 4 && !hasHand ? 'Chưa thấy bàn tay rõ. Hãy đưa cả bàn tay vào khung hình.' : data.quality.message_vi);
          }
        }
      };
      ws.onerror = () => setCameraCheckMessage('Không thể kết nối bộ kiểm tra camera. Hãy thử lại.');
      ws.onclose = () => {
        if (!cameraReady) {
          setCameraCheckMessage('Kết nối kiểm tra camera đã bị ngắt. Hãy bấm “Kiểm tra camera” để thử lại.');
          stream.getTracks().forEach(track => track.stop());
          if (streamRef.current === stream) streamRef.current = null;
          setCameraStreamReady(false);
          setCameraChecking(false);
        }
      };
    } catch (cause) {
      setCameraChecking(false);
      const name = cause instanceof Error ? cause.name : '';
      setCameraCheckMessage(name === 'NotAllowedError'
        ? 'Trình duyệt chưa cho phép camera. Hãy bấm biểu tượng khóa trên thanh địa chỉ → Camera → Cho phép, rồi thử lại.'
        : name === 'NotReadableError'
          ? 'Camera đang được ứng dụng khác sử dụng. Hãy đóng ứng dụng đó rồi thử lại.'
          : 'Không thể truy cập camera. Hãy kiểm tra quyền camera của trình duyệt.');
    }
  }, [cameraReady, cameraSize, drawSkeleton, exerciseId, token, tutorialCompleted, wsBase]);

  const startCamera = useCallback(async (sessionUuid: string) => {
    try {
      const size = cameraSize();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: size.width }, height: { ideal: size.height }, facingMode: 'user' },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      updateStatus('Đang kết nối AI...');
      connectWebSocket(sessionUuid);
    } catch {
      updateStatus('Không thể truy cập camera');
    }
  }, [cameraSize, connectWebSocket, updateStatus]);

  const beginSession = async () => {
    if (!tutorialCompleted || (exerciseId !== 6 && (painBefore === null || painBefore >= 7)) || !cameraReady) return;
    setStartError('');
    stopCamera();
    setCameraChecking(false);
    targetRepsRef.current = targetReps;
    completedRepsRef.current = 0;
    predictionCandidateRef.current = { exerciseId: 0, count: 0 };
    acceptedPredictionRef.current = 0;
    setCompletedReps(0);
    setTimeline([]);
    pausedRef.current = false;
    setPaused(false);
    setRecognizedExercise(exerciseId === 6 ? 'Rule-based geometry' : 'Đang chờ dữ liệu nhận diện...');
    setRecognitionConfidence(null);
    setLiveAssessment('unassessed');
    setLandmarkRate(null);
    setQualityReason('Đang chờ đủ dữ liệu camera.');
    const response = await fetch(`${apiBase}/api/exercise/session/start`, {
      method: 'POST',
      headers: authHeaders(token, true),
      body: JSON.stringify({ exercise_id: exerciseId, target_reps: targetReps, ...(exerciseId === 6 ? {} : { pain_before: painBefore }) }),
    });
    if (!response.ok) {
      let message = 'Không thể tạo buổi tập.';
      try {
        const payload = await response.json();
        if (typeof payload.detail === 'string') message = payload.detail;
      } catch { /* giữ thông báo mặc định */ }
      setStartError(message);
      updateStatus('Không thể tạo buổi tập');
      return;
    }
    const data = await response.json();
    sessionRef.current = data.session_id;
    sessionStorage.setItem('rehabai_active_session', data.session_id);
    assessmentOpenRef.current = false;
    setStarted(true);
    window.requestAnimationFrame(() => startCamera(data.session_id));
  };

  const finishSession = async () => {
    if (!sessionRef.current || (exerciseId !== 6 && painAfter === null) || isSaving) return;
    setIsSaving(true);
    setFinishError('');
    try {
      const response = await fetch(`${apiBase}/api/exercise/session/end`, {
        method: 'POST',
        headers: authHeaders(token, true),
        body: JSON.stringify({ session_id: sessionRef.current, pain_after: exerciseId === 6 ? null : painAfter, repetition: completedReps }),
      });
      if (!response.ok) throw new Error('Không thể lưu kết quả buổi tập.');
      setFinishResult(await response.json());
      sessionStorage.removeItem('rehabai_active_session');
      setShowFinish(false);
    } catch (error) {
      setFinishError(error instanceof Error ? error.message : 'Không thể lưu kết quả buổi tập.');
    } finally {
      setIsSaving(false);
    }
  };

  useEffect(() => () => stopCamera(), [stopCamera]);

  if (!ENABLED_EXERCISE_IDS.has(exerciseId)) {
    return (
      <div className="practice-setup glass-card unavailable-exercise">
        <h2>Bài tập đang được hoàn thiện</h2>
        <p>Phiên bản hiện tại chỉ mở bài khuỷu tay và mở bàn tay để tập trung nâng cao chất lượng nhận diện và đếm số lần.</p>
        <Link to="/app/exercises" className="btn btn-primary">Chọn bài tập đang hỗ trợ</Link>
      </div>
    );
  }

  if (!started) {
    return (
      <div className="practice-setup glass-card">
        {!uiHide.hide_clinical_warning && <ClinicalDisclaimer className="mb-4" />}
        <div className="badge badge-success">Chuẩn bị buổi tập</div>
        <h2>Chuẩn bị: {names[exerciseId]}</h2>
        <p className="practice-setup-intro">Hoàn thành lần lượt 3 bước để buổi tập an toàn và có kết quả ổn định.</p>
        <div className="practice-steps" aria-label="Các bước chuẩn bị buổi tập">
          <div className={`practice-step ${tutorialCompleted ? 'is-complete' : 'is-current'}`}><span>1</span><div><strong>{hasTutorialVideo ? (tutorialSkipped ? 'Bỏ qua hướng dẫn' : 'Xem hướng dẫn') : 'Đọc hướng dẫn'}</strong><small>{hasTutorialVideo ? (tutorialSkipped ? 'Đã bỏ qua theo lựa chọn' : tutorialCompleted ? 'Đã xem hết video' : 'Có thể bỏ qua nếu đã nắm động tác') : 'Đã có hướng dẫn thực hiện bên dưới'}</small></div><CheckCircle size={17} /></div>
          <div className={`practice-step ${tutorialCompleted ? (cameraReady ? 'is-complete' : 'is-current') : 'is-locked'}`}><span>2</span><div><strong>Kiểm tra camera</strong><small>{cameraReady ? 'Camera đã sẵn sàng' : 'Đảm bảo đủ sáng và thấy rõ cơ thể'}</small></div><Camera size={17} /></div>
          <div className={`practice-step ${cameraReady ? 'is-current' : 'is-locked'}`}><span>3</span><div><strong>Thiết lập & bắt đầu</strong><small>Chọn số lần và mức đau trước tập</small></div><Play size={17} /></div>
        </div>
        {hasTutorialVideo ? <section className="tutorial-card" aria-labelledby="tutorial-title">
          <div className="tutorial-heading">
            <div><span className="eyebrow"><Video size={15} /> Video mẫu</span><h3 id="tutorial-title">Cách thực hiện đúng</h3><p>Xem hết video một lần hoặc bỏ qua nếu bạn đã biết động tác.</p></div>
            {tutorialCompleted && <span className={`tutorial-done ${tutorialSkipped ? 'is-skipped' : ''}`}><CheckCircle size={16} /> {tutorialSkipped ? 'Đã bỏ qua' : 'Đã xem'}</span>}
          </div>
          <div className="tutorial-video-frame">
            <video ref={tutorialRef} controls playsInline preload="metadata" src={tutorial?.video} onTimeUpdate={updateTutorialProgress} onEnded={completeTutorial} aria-label={`Video hướng dẫn ${names[exerciseId]}`} />
          </div>
          <div className="tutorial-progress" role="progressbar" aria-label="Tiến độ xem video" aria-valuemin={0} aria-valuemax={100} aria-valuenow={tutorialProgress}><span style={{ width: `${tutorialProgress}%` }} /></div>
          <div className="tutorial-footer"><span>{tutorialSkipped ? 'Bạn đã bỏ qua video. Hãy thực hiện đúng theo hướng dẫn khi tập.' : tutorialCompleted ? 'Bạn đã xem xong. Có thể kiểm tra camera.' : `Đã xem ${tutorialProgress}% · có thể bỏ qua`}</span><div className="tutorial-actions">{!tutorialCompleted && <button type="button" className="tutorial-skip" onClick={skipTutorial}><SkipForward size={14} /> Bỏ qua video</button>}{tutorialCompleted && <button type="button" className="tutorial-replay" onClick={replayTutorial}><RotateCcw size={14} /> Xem lại</button>}</div></div>
          <ul className="tutorial-tips">{tutorial?.tips.map((tip) => <li key={tip}><ShieldCheck size={15} /> <span>{tip}</span></li>)}</ul>
        </section> : <section className="tutorial-card" aria-labelledby="tutorial-title">
          <div className="tutorial-heading">
            <div><h3 id="tutorial-title">Hướng dẫn thực hiện</h3><p>Đọc kỹ các lưu ý trước khi kiểm tra camera và bắt đầu bài tập.</p></div>
            <span className="tutorial-done"><CheckCircle size={16} /> Đã sẵn sàng</span>
          </div>
          <ul className="tutorial-tips">{tutorial?.tips.map((tip) => <li key={tip}><ShieldCheck size={15} /> <span>{tip}</span></li>)}</ul>
        </section>}
        {cameraChecking && <div className="camera-check-preview"><video ref={videoRef} muted playsInline /><canvas ref={canvasRef} width={640} height={480} /></div>}
        <div className={`camera-check-message ${cameraReady ? 'is-ready' : ''}`} role="status"><Camera size={18} /> {cameraCheckMessage}</div>
        {!cameraReady && <button className="btn btn-secondary" onClick={startCameraCheck} disabled={!tutorialCompleted || cameraChecking}><Camera size={18} /> {cameraChecking ? 'Đang kiểm tra...' : tutorialCompleted ? 'Kiểm tra camera' : 'Xem video để mở khóa camera'}</button>}
        <div className="target-reps-card">
          <div className="target-reps-copy">
            <span>Số lần tập mục tiêu</span>
            <small>Có thể chọn từ {MIN_TARGET_REPS} đến {MAX_TARGET_REPS} lần</small>
          </div>
          <div className="rep-stepper" role="group" aria-label="Điều chỉnh số lần tập mục tiêu">
            <button
              type="button"
              aria-label="Giảm số lần tập"
              disabled={targetReps <= MIN_TARGET_REPS}
              onClick={() => updateTargetReps(targetReps - 1)}
            >
              <Minus size={18} />
            </button>
            <label>
              <span className="sr-only">Số lần tập mục tiêu</span>
              <input
                type="number"
                min={MIN_TARGET_REPS}
                max={MAX_TARGET_REPS}
                inputMode="numeric"
                value={targetReps}
                onChange={(event) => updateTargetReps(Number(event.target.value))}
                aria-label="Số lần tập mục tiêu"
              />
              <small>lần</small>
            </label>
            <button
              type="button"
              aria-label="Tăng số lần tập"
              disabled={targetReps >= MAX_TARGET_REPS}
              onClick={() => updateTargetReps(targetReps + 1)}
            >
              <Plus size={18} />
            </button>
          </div>
        </div>
        {exerciseId !== 6 && <div className="pain-picker">
          <strong>Đau trước khi tập: {painBefore === null ? 'chưa chọn' : `${painBefore}/10`}</strong>
          <div>{Array.from({ length: 11 }, (_, n) => <button type="button" key={n} className={painBefore === n ? 'selected' : ''} onClick={() => { setPainBefore(n); setStartError(''); }}>{n}</button>)}</div>
        </div>}
        {exerciseId !== 6 && painBefore !== null && painBefore >= 7 && <div className="pain-safety-message is-blocked" role="alert"><strong>Không nên bắt đầu tập.</strong><span>Mức đau hiện tại đang cao. Bạn nên dừng tập và liên hệ bác sĩ hoặc chuyên viên y tế để được đánh giá và điều trị phù hợp.</span></div>}
        {exerciseId !== 6 && painBefore !== null && painBefore < 7 && <div className="pain-safety-message" role="status"><strong>Có thể bắt đầu khi camera đạt yêu cầu.</strong><span>Hãy tập nhẹ nhàng, chậm rãi và dừng lại nếu đau tăng hoặc xuất hiện triệu chứng bất thường.</span></div>}
        {exerciseId === 6 && <div className="pain-safety-message" role="status"><strong>Bài thư giãn cổ.</strong><span>Không cần đánh giá cơn đau trước/sau; hãy dừng nếu thấy đau, tê hoặc chóng mặt.</span></div>}
        {startError && <div className="finish-error" role="alert">{startError}</div>}
        <button className="btn btn-primary" disabled={!tutorialCompleted || (exerciseId !== 6 && (painBefore === null || painBefore >= 7)) || !cameraReady} onClick={beginSession}><Play size={18} /> Bắt đầu tập</button>
      </div>
    );
  }

  if (finishResult) {
    return (
      <div className="practice-setup glass-card">
        <h2>Đã hoàn tất buổi tập</h2>
        <p>Bạn đã thực hiện <strong>{completedReps}/{targetReps} lần</strong>.</p>
        {exerciseId !== 6 && <p>Đau sau tập: <strong>{finishResult.pain_after}/10</strong></p>}
        <div className="recommendation">{finishResult.recommendation}</div>
        <button className="btn btn-primary" onClick={() => navigate('/app/history')}>Xem lịch sử</button>
      </div>
    );
  }

  return (
    <div className="practice-page">
      <div className="practice-header">
        <h2>Tập luyện</h2>
        <div className={`practice-status ${completedReps >= targetReps ? 'is-complete' : ''}`} title={status} aria-live="polite">
          {completedReps >= targetReps ? <CheckCircle size={16} /> : <Camera size={16} />}
          <span>{status}</span>
        </div>
      </div>
      <div className="grid-cols-3 practice-grid">
        <div className="glass-card practice-camera">
          <video ref={videoRef} muted playsInline />
          <canvas ref={canvasRef} width={640} height={480} />
        </div>
        <div className="glass-card practice-results">
          <h3>Kết quả phân tích</h3>
          <div className="result-box"><span>Bài tập đã chọn</span><strong>{names[exerciseId]}</strong></div>
          <div className="result-box recognition-result">
            <span>Bài tập nhận diện</span>
            <strong title={recognizedExercise}>{recognizedExercise}</strong>
            <small className={recognitionConfidence === null ? 'is-placeholder' : ''}>
              {recognitionConfidence === null ? 'Chưa có độ tự tin' : `Độ tự tin tương đối: ${(recognitionConfidence * 100).toFixed(1)}%`}
            </small>
          </div>
          <div className={`result-box quality-result live-assessment ${liveAssessment}`}>
            <span>Phạm vi đánh giá hiện tại</span>
            <strong>{liveAssessment === 'matched' ? 'AI nhận diện đúng bài đã chọn' : liveAssessment === 'mismatched' ? 'AI nhận diện bài khác' : 'Chưa đủ dữ liệu để kết luận'}</strong>
            <small>{qualityReason}{landmarkRate !== null ? ` · Landmark hợp lệ: ${(landmarkRate * 100).toFixed(0)}%` : ''}</small>
          </div>
          <div className={`result-box rep-result ${completedReps >= targetReps ? 'is-complete' : ''}`}>
            <span>Tiến độ mục tiêu</span>
            <strong className="rep-progress">{completedReps}/{targetReps}</strong>
            <div className="rep-progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={targetReps} aria-valuenow={completedReps}>
              <span style={{ width: `${(completedReps / targetReps) * 100}%` }} />
            </div>
            <small>{completedReps >= targetReps ? 'Đã hoàn thành mục tiêu' : `Còn ${targetReps - completedReps} lần để hoàn thành`}</small>
          </div>
          {formFeedback && (formFeedback.pace || formFeedback.angle) && exerciseId !== 6 && (
            <div className={`result-box form-result ${formFeedback.pace === 'ok' ? 'is-good' : formFeedback.pace === 'unknown' ? '' : 'is-warn'}`}>
              <span>Đúng/Sai & tốc độ</span>
              <strong>{formFeedback.label}</strong>
              <small>Đánh giá theo góc khớp và tốc độ thực tế — không thay thế đánh giá của chuyên viên y tế.</small>
            </div>
          )}
          <button className="btn btn-primary" onClick={() => openPainAssessment(false)}><CheckCircle size={18} /> Kết thúc bài tập</button>
          <button className="btn btn-secondary" onClick={()=>setPaused(value=>{pausedRef.current=!value;return !value})}>{paused?<><RotateCcw size={18}/> Tiếp tục</>:<><Pause size={18}/> Tạm dừng</>}</button>
        </div>
      </div>
      <section className="surface session-timeline" aria-label="Dòng thời gian lần lặp"><div className="section-heading"><div><h3>Dòng thời gian buổi tập</h3><p>Chỉ hiển thị các lần lặp đã được bộ đếm xác nhận; chưa phải chấm đúng/sai kỹ thuật.</p></div><span className="badge badge-info">{timeline.length}/{targetReps} lần</span></div><div className="timeline-track">{timeline.length===0?<div className="timeline-empty">Chưa có lần lặp được xác nhận. Hãy đứng trong vùng quan sát camera.</div>:timeline.map(item=><div key={item.rep} className="timeline-rep" title={`Lần ${item.rep} · ${item.timestamp}`}><CheckCircle size={17}/><strong>Lần {item.rep}</strong><small>{item.timestamp}</small></div>)}</div></section>

      {showFinish && (
        <div className="finish-overlay" role="dialog" aria-modal="true" aria-labelledby="finish-title" aria-describedby="finish-description">
          <div className="finish-dialog glass-card">
            <div className="finish-icon"><CheckCircle size={36} /></div>
          <h3 id="finish-title">{exerciseId === 6 ? (completedAutomatically ? 'Hoàn thành bài thư giãn!' : 'Kết thúc bài thư giãn') : (completedAutomatically ? 'Hoàn thành bài tập!' : 'Đánh giá sau tập')}</h3>
            <p id="finish-description">{exerciseId === 6 ? `Bạn đã thực hiện ${completedReps}/${targetReps} lần. Không cần đánh giá cơn đau cho bài thư giãn này.` : (completedAutomatically ? `Bạn đã hoàn thành đủ ${targetReps}/${targetReps} lần. Hãy đánh giá cơn đau sau khi tập.` : `Bạn đã thực hiện ${completedReps}/${targetReps} lần. Hãy đánh giá cơn đau sau khi tập.`)}</p>
            {exerciseId !== 6 && <><strong>Mức đau sau tập: {painAfter === null ? 'chưa chọn' : `${painAfter}/10`}</strong><div className="pain-scale">{Array.from({ length: 11 }, (_, n) => <button type="button" key={n} className={painAfter === n ? 'selected' : ''} onClick={() => setPainAfter(n)}>{n}</button>)}</div><small>0 = không đau · 10 = đau dữ dội</small></>}
            {finishError && <p className="finish-error" role="alert">{finishError}</p>}
            <button className="btn btn-primary" disabled={(exerciseId !== 6 && painAfter === null) || isSaving} onClick={finishSession}>{isSaving ? 'Đang lưu...' : exerciseId === 6 ? 'Lưu kết quả' : 'Lưu và xem khuyến nghị'}</button>
          </div>
        </div>
      )}
    </div>
  );
}
