import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Play } from 'lucide-react';
import handOpening from '../assets/illustrations/hand-opening.svg';
import elbowExtension from '../assets/illustrations/elbow-extension.svg';

// Neck (id 6) and guided deep breathing (id 5) are hidden from the picker.
// The backend, data and direct practice pages are intentionally kept.
const ENABLED_EXERCISE_IDS = new Set([2, 4]);

interface Exercise {
  id: number;
  display_order: number;
  name_vi: string;
  description: string;
}

export default function ExerciseSelection() {
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const apiBase = import.meta.env.VITE_API_BASE || '';

  useEffect(() => {
    fetch(`${apiBase}/api/exercises`)
      .then(res => res.json())
      .then(data => {
        setExercises(
          [...data]
            .filter((exercise: Exercise) => ENABLED_EXERCISE_IDS.has(exercise.id))
            .sort((a: Exercise, b: Exercise) => a.display_order - b.display_order),
        );
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch exercises:', err);
        setError('Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại Backend.');
        setLoading(false);
      });
  }, [apiBase]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 'var(--space-2xl)' }}>
        <div className="spinner"></div>
        <p style={{ marginTop: 'var(--space-md)' }}>Đang tải danh sách bài tập...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card" style={{ borderColor: 'var(--danger)', textAlign: 'center' }}>
        <h3 className="text-danger">Lỗi kết nối</h3>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="exercise-selection-heading">
        <div className="badge badge-success">Đang hỗ trợ {exercises.length} bài tập</div>
        <h2>Chọn bài tập</h2>
        <p>Phiên bản hiện tại tập trung vào bài khuỷu tay và mở bàn tay. Khi đạt đủ số lần đã chọn, hệ thống sẽ tự kết thúc và mở bảng đánh giá cơn đau.</p>
      </div>

      <div className="grid-cols-2">
        {exercises.map((ex) => (
          <div key={ex.id} className="glass-card exercise-selection-card">
              <div className={`exercise-selection-art ${ex.id === 2 ? 'coral' : 'violet'}`}>
              <img src={ex.id === 2 ? elbowExtension : handOpening} alt="" aria-hidden="true" />
            </div>
            <div>
              <div className="badge badge-info" style={{ marginBottom: 'var(--space-sm)' }}>
                {ex.id === 2 ? 'Khuỷu tay' : 'Bàn tay'}
              </div>
              <h3 style={{ fontSize: '1.25rem' }}>{ex.name_vi}</h3>
            </div>

            <div className="exercise-selection-action">
              <Link to={`/app/practice/${ex.id}`} className="btn btn-primary" style={{ width: '100%' }}>
                <Play size={18} />
                Chọn bài này
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
