# CLAUDE.md - RehabAI Project Guide

## Project Overview
RehabAI là hệ thống AI nhận dạng bài tập phục hồi chức năng cho bệnh nhân đột quỵ.
- **4 bài tập**: Shoulder lift, Elbow extension, Wrist flexion/extension, Hand opening
- **Model**: RehabMotionNet v2 (TorchScript)
- **Performance**: 43.79% Accuracy LOSO (research/demo level)

## Key Paths
- Main code: `rehabai/`
- Backend: `rehabai/backend/`
- Frontend: `rehabai/frontend/`
- Training: `rehabai/training/`
- Artifacts: `rehabai/artifacts/model_v2/`
- Database: `rehabai/backend/data/rehabai_sessions.db`

## Important Notes
- Backend port: 8000, Frontend port: 8080
- Database: SQLite (dev), PostgreSQL (prod)
- PyTorch version: 2.2.2 (inference), 2.7.0 (training)
- All paths relative to `rehabai/` directory
- Set PYTHONPATH=. when running from parent directory

## Common Commands
```bash
# Development
cd rehabai
$env:PYTHONPATH="."
uvicorn backend.main:app --reload

# Docker
cd rehabai/deployment
docker compose up --build

# Testing
python -m pytest tests shared/tests -q
```

## Architecture
```
Video/Webcam → MediaPipe → 96 frames × 237 features → TorchScript → 4-class prediction
                                                              ↓
Backend (FastAPI + WebSocket) ← → React Frontend ← → SQLite Database
```

## Database Schema
- Table: sessions
- Key columns: session_uuid, exercise_id, pain_before/after, target_reps, metrics (JSON)

## Known Limitations
- Small dataset: 10 subjects, 387 samples
- High variance between LOSO folds (5%-74% accuracy)
- No clinical validation yet
- Authentication: JWT-based (basic)
