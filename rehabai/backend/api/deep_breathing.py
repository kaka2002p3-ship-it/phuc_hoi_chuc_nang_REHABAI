"""Authenticated API and WebSocket for non-clinical guided breathing."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import datetime

import cv2
import mediapipe as mp
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.db import (
    AuditEvent,
    DeepBreathingEvent,
    DeepBreathingSession,
    SessionLocal,
    User,
    get_db,
)
from backend.core.security import current_user, user_id_from_token
from backend.deep_breathing.analyzer import BreathingAnalyzer
from backend.deep_breathing.config import DeepBreathingConfig
from backend.deep_breathing.types import PoseFrame, SessionStatus

router = APIRouter()
ws_router = APIRouter()
logger = logging.getLogger("rehabai.deep_breathing")
ALLOWED_FINAL_STATUSES = {item.value for item in SessionStatus}


class SessionCreate(BaseModel):
    inhale_seconds: float | None = Field(default=None, ge=2, le=10)
    hold_seconds: float | None = Field(default=None, ge=0, le=10)
    exhale_seconds: float | None = Field(default=None, ge=2, le=15)
    rest_seconds: float | None = Field(default=None, ge=0, le=10)
    target_cycles: int | None = Field(default=None, ge=1, le=20)


class SessionFinish(BaseModel):
    session_status: str = "COMPLETED"
    tracking_mode: str = Field(default="POSE_SHOULDER", pattern="^(POSE_SHOULDER|GUIDED_TIMER_ONLY)$")
    guided_cycles_completed: int | None = Field(default=None, ge=0, le=20)


def _owned(db: Session, session_id: str, user_id: str) -> DeepBreathingSession:
    item = db.query(DeepBreathingSession).filter(
        DeepBreathingSession.id == session_id,
        DeepBreathingSession.user_id == user_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Khong tim thay buoi tap hit tho duoc phep truy cap.")
    return item


def _payload(item: DeepBreathingSession, include_events: bool = False, db: Session | None = None) -> dict:
    data = {
        "session_id": item.id,
        "exercise": "DEEP_BREATHING",
        "protocol_version": item.protocol_version,
        "config": item.config,
        "target_cycles": item.target_cycles,
        "completed_cycles": item.completed_cycles,
        "interrupted_cycles": item.interrupted_cycles,
        "average_cycle_duration": item.average_cycle_duration,
        "tracking_quality": item.tracking_quality,
        "tracking_coverage": item.tracking_coverage,
        "session_status": item.session_status,
        "started_at": item.started_at.isoformat(),
        "ended_at": item.ended_at.isoformat() if item.ended_at else None,
        "privacy": {"raw_video_stored": False, "derived_events_only": True},
    }
    if include_events and db is not None:
        rows = db.query(DeepBreathingEvent).filter(
            DeepBreathingEvent.session_id == item.id,
            DeepBreathingEvent.user_id == item.user_id,
        ).order_by(DeepBreathingEvent.created_at).all()
        data["events"] = [{
            "event_type": row.event_type,
            "phase": row.phase,
            "cycle_index": row.cycle_index,
            "elapsed_seconds": row.elapsed_seconds,
            "payload": row.payload,
            "created_at": row.created_at.isoformat(),
        } for row in rows]
    return data


@router.get("/deep-breathing/config")
def get_config(user: User = Depends(current_user)):
    del user
    return DeepBreathingConfig.from_env().as_dict()


@router.post("/deep-breathing/sessions", status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    defaults = DeepBreathingConfig.from_env()
    overrides = {name: value for name, value in payload.model_dump().items() if value is not None}
    try:
        config = DeepBreathingConfig(**{**defaults.__dict__, **overrides})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Cau hinh protocol khong hop le: {exc}") from exc
    item = DeepBreathingSession(
        user_id=user.id,
        protocol_version=config.protocol_version,
        config=config.as_dict(),
        target_cycles=config.target_cycles,
        session_status="IN_PROGRESS",
        tracking_quality="UNAVAILABLE",
    )
    db.add(item)
    db.flush()
    db.add(AuditEvent(user_id=user.id, action="deep_breathing.start", resource_type="deep_breathing_session", resource_id=item.id, payload={"target_cycles": config.target_cycles}))
    db.commit()
    db.refresh(item)
    logger.info('{"session_id":"%s","event":"session_started"}', item.id)
    return _payload(item)


@router.get("/deep-breathing/sessions")
def list_sessions(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(DeepBreathingSession).filter(DeepBreathingSession.user_id == user.id).order_by(DeepBreathingSession.started_at.desc()).all()
    return [_payload(item) for item in rows]


@router.get("/deep-breathing/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _payload(_owned(db, session_id, user.id), include_events=True, db=db)


@router.post("/deep-breathing/sessions/{session_id}/finish")
def finish_session(session_id: str, payload: SessionFinish, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = _owned(db, session_id, user.id)
    if payload.session_status not in ALLOWED_FINAL_STATUSES:
        raise HTTPException(status_code=422, detail="Trang thai ket thuc khong hop le.")
    # Idempotent finish: repeat requests return the original persisted result.
    if item.session_status != "IN_PROGRESS":
        return _payload(item)
    item.session_status = payload.session_status
    item.ended_at = datetime.utcnow()
    item.config = {**(item.config or {}), "tracking_mode": payload.tracking_mode}
    if payload.tracking_mode == "GUIDED_TIMER_ONLY":
        item.completed_cycles = min(payload.guided_cycles_completed or 0, item.target_cycles)
        item.tracking_quality = "UNAVAILABLE"
        item.tracking_coverage = 0.0
    elif (item.tracking_quality not in {"GOOD", "MEDIUM"} or item.completed_cycles < item.target_cycles) and payload.session_status == "COMPLETED":
        # A camera-mode session with no validated observations cannot claim a
        # camera-observed completion.
        item.session_status = SessionStatus.TRACKING_INSUFFICIENT.value
    if item.completed_cycles:
        duration = max(0.0, (item.ended_at - item.started_at).total_seconds())
        item.average_cycle_duration = duration / item.completed_cycles
    db.add(DeepBreathingEvent(
        session_id=item.id,
        user_id=user.id,
        event_type="session_completed" if item.session_status == "COMPLETED" else "session_interrupted",
        cycle_index=item.completed_cycles,
        payload={"tracking_mode": payload.tracking_mode, "tracking_quality": item.tracking_quality},
    ))
    db.add(AuditEvent(user_id=user.id, action="deep_breathing.finish", resource_type="deep_breathing_session", resource_id=item.id, payload={"status": item.session_status}))
    db.commit()
    db.refresh(item)
    logger.info('{"session_id":"%s","event":"session_finished","status":"%s"}', item.id, item.session_status)
    return _payload(item)


def _decode_image(value: str) -> np.ndarray:
    if "," in value:
        value = value.split(",", 1)[1]
    raw = base64.b64decode(value, validate=True)
    image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Cannot decode frame")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


class PoseExtractor:
    """Small pose-only adapter that retains landmark visibility."""
    def __init__(self):
        self.pose = mp.solutions.pose.Pose(static_image_mode=False, model_complexity=1, enable_segmentation=False, min_detection_confidence=0.5, min_tracking_confidence=0.5)

    def process(self, image_rgb: np.ndarray) -> PoseFrame:
        result = self.pose.process(image_rgb)
        if not result.pose_landmarks:
            return PoseFrame()
        points = result.pose_landmarks.landmark
        xyz = lambda index: (float(points[index].x), float(points[index].y), float(points[index].z))
        return PoseFrame(
            left_shoulder=xyz(11), right_shoulder=xyz(12),
            left_visibility=float(points[11].visibility), right_visibility=float(points[12].visibility),
            left_hip=xyz(23), right_hip=xyz(24), nose=xyz(0),
        )

    def close(self) -> None:
        self.pose.close()


@ws_router.websocket("/ws/deep-breathing/{session_id}")
async def deep_breathing_websocket(websocket: WebSocket, session_id: str):
    token = websocket.query_params.get("token", "")
    try:
        user_id = user_id_from_token(token)
    except Exception:
        await websocket.close(code=1008, reason="Authentication required")
        return
    db = SessionLocal()
    try:
        item = db.query(DeepBreathingSession).filter(DeepBreathingSession.id == session_id, DeepBreathingSession.user_id == user_id).first()
        if not item or item.session_status != "IN_PROGRESS":
            await websocket.close(code=1008, reason="Active owned session required")
            return
        config_values = {key: value for key, value in (item.config or {}).items() if key in DeepBreathingConfig.__dataclass_fields__ and key != "cycle_seconds"}
        analyzer = BreathingAnalyzer(DeepBreathingConfig(**config_values))
    finally:
        db.close()

    await websocket.accept()
    extractor: PoseExtractor | None = None
    pose_unavailable = False
    total_frames = good_frames = 0
    last_persisted_phase: str | None = None
    try:
        while True:
            try:
                message = json.loads(await websocket.receive_text())
                frame_data = message.get("frame")
                timestamp = float(message.get("timestamp", 0)) / 1000.0
                if not frame_data or timestamp <= 0:
                    await websocket.send_json({"type": "ERROR", "code": "INVALID_FRAME", "message": "Khung hinh khong hop le."})
                    continue
                image = await asyncio.to_thread(_decode_image, frame_data)
                if pose_unavailable:
                    await websocket.send_json({"type": "ERROR", "code": "CAMERA_UNAVAILABLE", "message": "MediaPipe khong kha dung. Hay chuyen sang guided timer-only; tracking unavailable."})
                    continue
                if extractor is None:
                    try:
                        extractor = PoseExtractor()
                    except Exception as exc:
                        pose_unavailable = True
                        logger.exception("MediaPipe Pose unavailable for %s: %s", session_id, exc)
                        await websocket.send_json({"type": "ERROR", "code": "CAMERA_UNAVAILABLE", "message": "Theo doi MediaPipe khong kha dung. Guided timer-only van co the tiep tuc; tracking unavailable."})
                        continue
                pose_frame = await asyncio.to_thread(extractor.process, image)
                update = analyzer.update(pose_frame, timestamp)
                total_frames += 1
                if update.tracking_quality.value == "GOOD":
                    good_frames += 1
                response = {
                    "type": "BREATH_CYCLE_COMPLETED" if update.event == "cycle_completed" else "BREATH_PHASE",
                    "phase": update.phase.value,
                    "cycle_index": update.cycle_index,
                    "completed_cycles": update.completed_cycles,
                    "interrupted_cycles": update.interrupted_cycles,
                    "tracking_quality": update.tracking_quality.value,
                    "signal_quality": update.signal_quality.value,
                    "phase_confidence": update.confidence,
                    "elapsed_seconds": round(update.elapsed_seconds, 3),
                    "event": update.event,
                }
                await websocket.send_json(response)
                phase_changed = update.phase.value != last_persisted_phase
                if update.event or phase_changed or total_frames % 15 == 0:
                    persistence = SessionLocal()
                    try:
                        owned = persistence.query(DeepBreathingSession).filter(DeepBreathingSession.id == session_id, DeepBreathingSession.user_id == user_id).first()
                        if not owned or owned.session_status != "IN_PROGRESS":
                            await websocket.close(code=1008, reason="Session no longer active")
                            return
                        owned.completed_cycles = update.completed_cycles
                        owned.interrupted_cycles = update.interrupted_cycles
                        owned.tracking_coverage = good_frames / max(total_frames, 1)
                        owned.tracking_quality = "GOOD" if owned.tracking_coverage >= analyzer.config.min_good_frames_ratio else "POOR"
                        if update.event or phase_changed:
                            persistence.add(DeepBreathingEvent(
                                session_id=session_id, user_id=user_id, event_type=update.event or "phase_transition",
                                phase=update.phase.value, cycle_index=update.cycle_index,
                                elapsed_seconds=update.elapsed_seconds,
                                payload={"tracking_quality": update.tracking_quality.value, "signal_quality": update.signal_quality.value},
                            ))
                        persistence.commit()
                        last_persisted_phase = update.phase.value
                    finally:
                        persistence.close()
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                logger.warning('{"session_id":"%s","error":"frame_processing","detail":"%s"}', session_id, str(exc))
                await websocket.send_json({"type": "ERROR", "code": "UNKNOWN_ERROR", "message": "Khong the phan tich khung hinh. Vui long thu lai."})
    except WebSocketDisconnect:
        logger.info('{"session_id":"%s","event":"websocket_disconnected"}', session_id)
    except Exception as exc:
        logger.exception("Deep breathing WebSocket failure for %s: %s", session_id, exc)
        try:
            await websocket.send_json({"type": "ERROR", "code": "UNKNOWN_ERROR", "message": "Theo doi camera tam thoi gian doan. Ban co the chuyen sang che do hen gio."})
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        if extractor is not None:
            extractor.close()
