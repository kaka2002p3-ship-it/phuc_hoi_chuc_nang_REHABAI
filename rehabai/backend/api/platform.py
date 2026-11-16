"""Product APIs: authentication, pain, sessions, reports and settings."""

from __future__ import annotations

import json
import base64
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.core.db import (AuditEvent, ChatConversation, ChatMessage, DeepBreathingEvent,
                             DeepBreathingSession, ExerciseSession,
                             MovementFeedback, MovementPrediction, PainAssessment, Report,
                             SessionRepetition, SystemSetting, User, get_db)
from backend.core.exercise_names import DISPLAY_EXERCISE_NAMES
from backend.core.session_status import completion_status
from backend.core.model_loader import model_loader
from backend.core.security import create_token, current_user, hash_password, verify_password


router = APIRouter()


class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    bio: str | None = Field(default=None, max_length=300)
    avatar_data_url: str | None = Field(default=None, max_length=1_100_000)
    weekly_goal: int | None = Field(default=None, ge=1, le=14)
    height_cm: float | None = Field(default=None, ge=50, le=260)
    weight_kg: float | None = Field(default=None, ge=10, le=500)


def user_payload(user: User) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "phone": user.phone,
            "bio": user.bio, "avatar_data_url": user.avatar_data_url, "weekly_goal": user.weekly_goal,
            "height_cm": user.height_cm, "weight_kg": user.weight_kg, "role": getattr(user, "role", "patient"),
            "created_at": user.created_at.isoformat()}


def _clean_optional(value: str | None) -> str | None:
    cleaned = value.strip() if value else ""
    return cleaned or None


def _validate_avatar(value: str | None) -> str | None:
    if value is None:
        return None
    allowed = ("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")
    prefix = next((item for item in allowed if value.startswith(item)), None)
    if not prefix:
        raise HTTPException(status_code=422, detail="Ảnh đại diện chỉ hỗ trợ JPEG, PNG hoặc WebP.")
    try:
        raw = base64.b64decode(value[len(prefix):], validate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Dữ liệu ảnh đại diện không hợp lệ.") from exc
    if len(raw) > 750_000:
        raise HTTPException(status_code=413, detail="Ảnh đại diện sau khi tối ưu không được vượt quá 750 KB.")
    return value


def audit(db: Session, user_id: str | None, action: str, resource_type: str, resource_id: str | None = None, payload: dict | None = None):
    db.add(AuditEvent(user_id=user_id, action=action, resource_type=resource_type, resource_id=resource_id, payload=payload))


@router.post("/auth/register", status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email đã được sử dụng.")
    user = User(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": user_payload(user)}


@router.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng.")
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": user_payload(user)}


@router.get("/users/me")
def me(user: User = Depends(current_user)):
    return user_payload(user)


@router.put("/users/me")
def update_me(payload: ProfileIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    user.full_name = payload.full_name.strip()
    user.phone = _clean_optional(payload.phone)
    user.bio = _clean_optional(payload.bio)
    user.avatar_data_url = _validate_avatar(payload.avatar_data_url)
    user.weekly_goal = payload.weekly_goal
    user.height_cm = payload.height_cm
    user.weight_kg = payload.weight_kg
    user.updated_at = datetime.utcnow()
    audit(db, user.id, "profile.update", "user", user.id, {"avatar_changed": payload.avatar_data_url is not None})
    db.commit(); db.refresh(user)
    return user_payload(user)


@router.get("/users/me/export")
def export_my_data(db: Session = Depends(get_db), user: User = Depends(current_user)):
    sessions = db.query(ExerciseSession).filter(ExerciseSession.user_id == user.id).order_by(ExerciseSession.start_time).all()
    breathing_sessions = db.query(DeepBreathingSession).filter(DeepBreathingSession.user_id == user.id).order_by(DeepBreathingSession.started_at).all()
    assessments = db.query(PainAssessment).join(ExerciseSession, PainAssessment.session_uuid == ExerciseSession.session_uuid).filter(ExerciseSession.user_id == user.id).all()
    return {"user": user_payload(user), "sessions": [serialize_session(item) for item in sessions],
            "deep_breathing_sessions": [{"session_id": item.id, "exercise": "DEEP_BREATHING", "config": item.config,
                                          "target_cycles": item.target_cycles, "completed_cycles": item.completed_cycles,
                                          "interrupted_cycles": item.interrupted_cycles, "tracking_quality": item.tracking_quality,
                                          "tracking_coverage": item.tracking_coverage, "session_status": item.session_status,
                                          "started_at": item.started_at.isoformat(), "ended_at": item.ended_at.isoformat() if item.ended_at else None,
                                          "events": [{"event_type": event.event_type, "phase": event.phase, "cycle_index": event.cycle_index,
                                                      "elapsed_seconds": event.elapsed_seconds, "created_at": event.created_at.isoformat()}
                                                     for event in db.query(DeepBreathingEvent).filter(DeepBreathingEvent.session_id == item.id).order_by(DeepBreathingEvent.created_at).all()]}
                                         for item in breathing_sessions],
            "pain_assessments": [{"session_id": item.session_uuid, "phase": item.phase, "pain_score": item.pain_score,
                                  "note": item.note, "timestamp": item.timestamp.isoformat()} for item in assessments]}


@router.delete("/users/me", status_code=204)
def delete_my_account(db: Session = Depends(get_db), user: User = Depends(current_user)):
    session_ids = [row.session_uuid for row in db.query(ExerciseSession.session_uuid).filter(ExerciseSession.user_id == user.id).all()]
    if session_ids:
        db.query(PainAssessment).filter(PainAssessment.session_uuid.in_(session_ids)).delete(synchronize_session=False)
        db.query(MovementPrediction).filter(MovementPrediction.session_uuid.in_(session_ids)).delete(synchronize_session=False)
        db.query(MovementFeedback).filter(MovementFeedback.session_uuid.in_(session_ids)).delete(synchronize_session=False)
        db.query(SessionRepetition).filter(SessionRepetition.session_uuid.in_(session_ids)).delete(synchronize_session=False)
        db.query(ExerciseSession).filter(ExerciseSession.user_id == user.id).delete(synchronize_session=False)
    breathing_ids = [row.id for row in db.query(DeepBreathingSession.id).filter(DeepBreathingSession.user_id == user.id).all()]
    if breathing_ids:
        db.query(DeepBreathingEvent).filter(DeepBreathingEvent.session_id.in_(breathing_ids)).delete(synchronize_session=False)
        db.query(DeepBreathingSession).filter(DeepBreathingSession.user_id == user.id).delete(synchronize_session=False)
    db.query(SystemSetting).filter(SystemSetting.user_id == user.id).delete(synchronize_session=False)
    conversation_ids = [row.id for row in db.query(ChatConversation.id).filter(ChatConversation.user_id == user.id).all()]
    if conversation_ids:
        db.query(ChatMessage).filter(ChatMessage.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
    db.query(ChatConversation).filter(ChatConversation.user_id == user.id).delete(synchronize_session=False)
    db.query(Report).filter(Report.user_id == user.id).delete(synchronize_session=False)
    db.query(AuditEvent).filter(AuditEvent.user_id == user.id).update({AuditEvent.user_id: None}, synchronize_session=False)
    audit(db, None, "account.delete", "user")
    db.delete(user); db.commit()
    return None


class PainIn(BaseModel):
    session_id: str
    pain_score: int = Field(ge=0, le=10)
    note: Optional[str] = Field(default=None, max_length=2000)


def save_pain(phase: str, payload: PainIn, db: Session, user: User) -> dict:
    session = db.query(ExerciseSession).filter(
        ExerciseSession.session_uuid == payload.session_id,
        ExerciseSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi tập.")
    db.add(PainAssessment(session_uuid=session.session_uuid, phase=phase, pain_score=payload.pain_score, note=payload.note))
    if phase == "before": session.pain_before = payload.pain_score
    else: session.pain_after = payload.pain_score
    before = session.pain_before if session.pain_before is not None else payload.pain_score
    high = payload.pain_score >= 7
    increased = phase == "after" and payload.pain_score >= before + 2
    warning = high or increased
    message = (
        "Mức đau đáng lưu ý. Hãy dừng tập và liên hệ bác sĩ hoặc chuyên viên phục hồi chức năng."
        if warning else "Đã ghi nhận mức đau. Tiếp tục theo hướng dẫn và dừng nếu đau tăng."
    )
    audit(db, user.id, f"pain.{phase}", "exercise_session", session.session_uuid, {"pain_score": payload.pain_score})
    db.commit()
    return {"pain_score": payload.pain_score, "warning": warning, "pain_increase": increased, "high_pain": high, "message": message}


@router.post("/pain/before")
def pain_before(payload: PainIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return save_pain("before", payload, db, user)


@router.post("/pain/after")
def pain_after(payload: PainIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return save_pain("after", payload, db, user)


class StartIn(BaseModel):
    exercise_id: int = Field(ge=1, le=6)
    target_reps: int = Field(default=5, ge=1, le=30)
    pain_before: Optional[int] = Field(default=None, ge=0, le=10)


@router.post("/exercise/session/start")
def start_session(payload: StartIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    import uuid
    if payload.exercise_id != 6 and payload.exercise_id not in model_loader.id_to_exercise:
        raise HTTPException(status_code=400, detail="Bài tập không hợp lệ.")
    if payload.pain_before is not None and payload.pain_before >= 7:
        raise HTTPException(
            status_code=422,
            detail="Mức đau hiện tại quá cao để bắt đầu tập. Bạn nên dừng tập và liên hệ bác sĩ hoặc chuyên viên y tế để được đánh giá và điều trị phù hợp.",
        )
    session = ExerciseSession(session_uuid=str(uuid.uuid4()), user_id=user.id, exercise_id=payload.exercise_id,
        exercise_name=DISPLAY_EXERCISE_NAMES[payload.exercise_id], target_reps=payload.target_reps,
        pain_before=payload.pain_before, status="IN_PROGRESS")
    db.add(session)
    db.flush()
    if payload.pain_before is not None:
        db.add(PainAssessment(session_uuid=session.session_uuid, phase="before", pain_score=payload.pain_before))
    audit(db, user.id, "session.start", "exercise_session", session.session_uuid, {"exercise_id": payload.exercise_id})
    db.commit(); db.refresh(session)
    return {"session_id": session.session_uuid, "status": session.status, "start_time": session.start_time.isoformat()}


class EndIn(BaseModel):
    session_id: str
    repetition: int = Field(default=0, ge=0, le=1000)
    pain_after: Optional[int] = Field(default=None, ge=0, le=10)


@router.post("/exercise/session/end")
def end_session(payload: EndIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    session = db.query(ExerciseSession).filter(
        ExerciseSession.session_uuid == payload.session_id,
        ExerciseSession.user_id == user.id,
    ).first()
    if not session: raise HTTPException(status_code=404, detail="Không tìm thấy buổi tập.")
    session.end_time = datetime.utcnow()
    session.status = completion_status(payload.repetition, session.target_reps, "ENDED")
    session.pain_after = payload.pain_after if session.exercise_id != 6 else None
    session.metrics = {**(session.metrics or {}), "rep_count": payload.repetition}
    recorded = db.query(SessionRepetition).filter(
        SessionRepetition.session_uuid == session.session_uuid
    ).count()
    # Keep manually/early-ended sessions internally consistent without
    # claiming that an unobserved repetition was correct or incorrect.
    for repetition_number in range(recorded + 1, payload.repetition + 1):
        db.add(SessionRepetition(
            session_uuid=session.session_uuid,
            repetition_number=repetition_number,
            movement_quality=None,
        ))
    if session.exercise_id != 6 and payload.pain_after is not None:
        db.add(PainAssessment(session_uuid=session.session_uuid, phase="after", pain_score=payload.pain_after))
    audit(db, user.id, "session.end", "exercise_session", session.session_uuid, {"repetition": payload.repetition})
    if session.exercise_id == 6:
        session.recommendation = "Bài thư giãn đã được lưu. Dừng tập nếu xuất hiện đau, tê hoặc chóng mặt."
    else:
        before = session.pain_before if session.pain_before is not None else 0
        if payload.pain_after is not None and (payload.pain_after >= 5 or payload.pain_after >= before + 2):
            session.recommendation = "Lần sau nên giảm số lần tập khoảng 20–30% và trao đổi với chuyên viên nếu đau còn tăng."
        elif payload.pain_after is not None and payload.pain_after > before:
            session.recommendation = "Lần sau giữ nguyên hoặc giảm nhẹ số lần; tập chậm và dừng nếu đau tăng."
        else:
            session.recommendation = "Mức đau không tăng. Chỉ tăng số lần khi chuyên viên đồng ý và động tác vẫn không đau."
    db.commit()
    return {"session_id": session.session_uuid, "status": session.status,
            "duration_seconds": max(0, int((session.end_time - session.start_time).total_seconds())),
            "repetition": payload.repetition, "pain_after": payload.pain_after,
            "movement_quality": None, "recommendation": session.recommendation}


def serialize_session(item: ExerciseSession) -> dict:
    duration = int(((item.end_time or datetime.utcnow()) - item.start_time).total_seconds())
    repetition = (item.metrics or {}).get("rep_count", 0)
    status = completion_status(repetition, item.target_reps, item.status)
    return {"id": item.session_uuid, "exercise_id": item.exercise_id, "exercise": item.exercise_name,
            "start_time": item.start_time.isoformat(), "end_time": item.end_time.isoformat() if item.end_time else None,
            "duration_seconds": max(duration, 0), "repetition": repetition, "target_reps": item.target_reps,
            "movement_quality": item.completion_score, "pain_before": item.pain_before,
            "pain_after": item.pain_after, "status": status, "recommendation": item.recommendation}


@router.get("/exercise/history")
def exercise_history(db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = db.query(ExerciseSession).filter(ExerciseSession.user_id == user.id)
    return [serialize_session(item) for item in query.order_by(ExerciseSession.start_time.desc()).all()]


@router.get("/exercise/history/{session_id}")
def exercise_history_detail(session_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.query(ExerciseSession).filter(
        ExerciseSession.session_uuid == session_id,
        ExerciseSession.user_id == user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi tập được phép truy cập.")
    rows = db.query(SessionRepetition).filter(
        SessionRepetition.session_uuid == item.session_uuid
    ).order_by(SessionRepetition.repetition_number, SessionRepetition.created_at).all()
    repetitions = [{
        "id": row.id,
        "repetition_number": row.repetition_number,
        "result": "matched" if row.movement_quality == 1.0 else "mismatched" if row.movement_quality == 0.0 else "unassessed",
        "legacy_result": "correct" if row.movement_quality == 1.0 else "incorrect" if row.movement_quality == 0.0 else "unassessed",
        # This is deliberately named as recognition, not technique scoring.
        # The production model currently verifies the selected exercise only.
        "assessment_scope": "exercise_recognition",
        "label": "AI nhận diện đúng bài đã chọn" if row.movement_quality == 1.0 else "AI nhận diện bài khác" if row.movement_quality == 0.0 else "Chưa đủ dữ liệu để kết luận",
        "explanation": "Confidence đạt ngưỡng và bài nhận diện trùng bài đã chọn." if row.movement_quality == 1.0 else "Confidence đạt ngưỡng nhưng bài nhận diện không trùng bài đã chọn." if row.movement_quality == 0.0 else "Không có dự đoán hợp lệ tại thời điểm xác nhận lần tập. Đây không phải kết luận tập sai.",
        "technical_status": "not_evaluated",
        "recorded_at": row.created_at.isoformat(),
    } for row in rows]
    detail = serialize_session(item)
    metrics = item.metrics or {}
    detail.update({
        "repetitions": repetitions,
        "matched_reps": sum(row["result"] == "matched" for row in repetitions),
        "mismatched_reps": sum(row["result"] == "mismatched" for row in repetitions),
        # Backward-compatible aliases; clients should prefer matched/mismatched.
        "correct_reps": sum(row["result"] == "matched" for row in repetitions),
        "incorrect_reps": sum(row["result"] == "mismatched" for row in repetitions),
        "unassessed_reps": sum(row["result"] == "unassessed" for row in repetitions),
        "assessment_scope": "exercise_recognition",
        "technical_evaluation": "not_available",
        # Rule-based form/pace check (angle span + speed per rep cycle).
        "form_quality": metrics.get("form_quality"),
        "speed_assessment": metrics.get("speed_assessment"),
    })
    return detail


@router.get("/reports/summary")
def report_summary(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.query(ExerciseSession).filter(ExerciseSession.user_id == user.id).all()
    complete = [x for x in items if completion_status((x.metrics or {}).get("rep_count", 0), x.target_reps, x.status) == "COMPLETED"]
    pains = [x.pain_after for x in complete if x.pain_after is not None]
    return {"total_sessions": len(items), "completed_sessions": len(complete),
            "completion_rate": round(len(complete) / len(items), 3) if items else 0,
            "average_pain": round(sum(pains) / len(pains), 2) if pains else None}


@router.get("/reports/progress")
def report_progress(days: int = 30, db: Session = Depends(get_db), user: User = Depends(current_user)):
    start = datetime.utcnow() - timedelta(days=max(1, min(days, 365)))
    items = db.query(ExerciseSession).filter(
        ExerciseSession.user_id == user.id, ExerciseSession.start_time >= start
    ).order_by(ExerciseSession.start_time).all()
    grouped: dict[str, dict] = {}
    for item in items:
        key = item.start_time.date().isoformat(); point = grouped.setdefault(key, {"date": key, "sessions": 0, "completed": 0, "pain_total": 0, "pain_count": 0})
        status = completion_status((item.metrics or {}).get("rep_count", 0), item.target_reps, item.status)
        point["sessions"] += 1; point["completed"] += int(status == "COMPLETED")
        if item.pain_after is not None: point["pain_total"] += item.pain_after; point["pain_count"] += 1
    return [{"date": x["date"], "sessions": x["sessions"], "completion_rate": x["completed"] / x["sessions"],
             "average_pain": x["pain_total"] / x["pain_count"] if x["pain_count"] else None} for x in grouped.values()]


DEFAULT_SETTINGS = {"language": "vi", "pain_alerts": True, "practice_reminders": True, "theme": "system", "camera_resolution": "1280x720"}


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.query(SystemSetting).filter(SystemSetting.key == f"application:{user.id}", SystemSetting.user_id == user.id).first()
    return json.loads(row.value) if row else DEFAULT_SETTINGS


class SettingsIn(BaseModel):
    language: str = Field(pattern="^(vi|en)$")
    pain_alerts: bool
    practice_reminders: bool
    theme: str = Field(pattern="^(light|dark|system)$")
    camera_resolution: str = Field(pattern="^(640x480|1280x720|1920x1080)$")


@router.put("/settings")
def put_settings(payload: SettingsIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    key = f"application:{user.id}"
    row = db.query(SystemSetting).filter(SystemSetting.key == key, SystemSetting.user_id == user.id).first() or SystemSetting(key=key, user_id=user.id, value="{}")
    row.value = payload.model_dump_json(); db.add(row); db.commit()
    return payload
