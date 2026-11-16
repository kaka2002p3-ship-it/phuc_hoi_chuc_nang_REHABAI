"""Public metadata/health APIs and authenticated compatibility aliases."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from backend.core.db import ExerciseSession, User, get_db, SessionLocal, DATABASE_URL
from backend.core.exercise_names import DISPLAY_EXERCISE_NAMES, EXERCISE_SEMANTICS
from backend.core.model_loader import ARTIFACTS_DIR, model_loader
from backend.core.rate_limit import login_rate_limiter
from backend.core.security import current_user, create_token, hash_password, verify_password
from backend.core.session_status import completion_status

router = APIRouter()

# Auth schemas
class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2, max_length=160)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str = "patient"
    user: UserResponse  # Include full user info for frontend compatibility


class UserLoginResponse(BaseModel):
    """Response format for login that includes full user object."""
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool = True
    role: Optional[str] = "patient"
    access_token: Optional[str] = None


# Auth endpoints
@router.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Login endpoint - authenticate user and return JWT token.
    """
    # Check rate limit
    client_ip = request.client.host if request.client else "unknown"
    allowed, seconds_left = login_rate_limiter.is_allowed(client_ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Quá nhiều yêu cầu. Vui lòng thử lại sau {seconds_left} giây.",
                "error": "rate_limit_exceeded",
                "retry_after": seconds_left
            }
        )

    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Email hoặc mật khẩu không đúng.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản đã bị khóa.",
        )
    token = create_token(user.id)
    role = getattr(user, "role", "patient") or "patient"

    # Return response with full user info for frontend compatibility
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": role,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "bio": user.bio,
            "is_active": user.is_active,
            "role": role,
        }
    }


@router.post("/auth/register", response_model=UserResponse, tags=["Authentication"])
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register new user account.
    """
    email = payload.email.lower().strip()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email đã được sử dụng.",
        )
    user = User(
        id=email.split("@")[0] + "_" + str(datetime.utcnow().timestamp())[:10],
        email=email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create token for immediate login
    token = create_token(user.id)

    return JSONResponse(
        status_code=201,
        content={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "bio": user.bio,
            "is_active": user.is_active,
            "access_token": token,
        }
    )


@router.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_current_user_info(user: User = Depends(current_user)):
    """
    Get current authenticated user information.
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        bio=user.bio,
        is_active=user.is_active,
    )

class SessionCreate(BaseModel):
    exercise_id: int = Field(ge=1, le=6)
    target_reps: int = Field(default=5, ge=1, le=30)
    pain_before: int = Field(default=0, ge=0, le=10)

class SessionResponse(BaseModel):
    id: int
    session_uuid: str
    exercise_id: int
    exercise_name: str
    start_time: str
    status: str
    completion_score: Optional[float] = None
    target_reps: Optional[int] = None
    pain_before: Optional[int] = None
    pain_after: Optional[int] = None
    recommendation: Optional[str] = None

def _owned_session(db: Session, session_id: str, user: User) -> ExerciseSession:
    item = db.query(ExerciseSession).filter(ExerciseSession.session_uuid == session_id, ExerciseSession.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi tập.")
    return item

def _session_payload(item: ExerciseSession) -> dict:
    return {"id": item.id, "session_uuid": item.session_uuid, "exercise_id": item.exercise_id,
            "exercise_name": item.exercise_name, "start_time": item.start_time.isoformat(), "status": item.status,
            "completion_score": item.completion_score, "target_reps": item.target_reps,
            "pain_before": item.pain_before, "pain_after": item.pain_after, "recommendation": item.recommendation}

def _deprecated(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Thu, 31 Dec 2026 23:59:59 GMT"
    response.headers["Link"] = '</api/exercise/session/start>; rel="successor-version"'

@router.get("/health", tags=["Health"])
def health_check():
    """Comprehensive health check endpoint for monitoring and container orchestration."""
    from backend.core.logging_config import get_logger

    health_logger = get_logger("rehabai.health")
    components = {}
    overall_healthy = True

    # Check model loader
    try:
        model_loaded = model_loader.model is not None
        components["model"] = {
            "status": "healthy" if model_loaded else "unhealthy",
            "loaded": model_loaded,
        }
        if not model_loaded:
            overall_healthy = False
    except Exception as e:
        components["model"] = {"status": "error", "error": str(e)}
        overall_healthy = False
        health_logger.error(f"Model health check failed: {e}")

    # Check database
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        components["database"] = {"status": "healthy", "type": "sqlite" if not DATABASE_URL else "postgresql"}
    except Exception as e:
        components["database"] = {"status": "error", "error": str(e)}
        overall_healthy = False
        health_logger.error(f"Database health check failed: {e}")

    # Check Ollama
    ollama_enabled = os.getenv("OLLAMA_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
    components["ollama"] = {
        "status": "healthy" if ollama_enabled else "disabled",
        "enabled": ollama_enabled,
    }

    status_code = 200 if overall_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if overall_healthy else "degraded",
            "message": "RehabAI Backend is running." if overall_healthy else "Some components are unhealthy.",
            "components": components,
            "service": "research/demo",
            "version": "1.0.0",
        }
    )

@router.get("/model-info")
def get_model_info():
    def load(name: str):
        with open(os.path.join(ARTIFACTS_DIR, name), "r", encoding="utf-8") as handle:
            return json.load(handle)
    with open(os.path.join(ARTIFACTS_DIR, "model_card.md"), "r", encoding="utf-8") as handle:
        card = handle.read()
    return {"config": load("model_config.json"), "metrics": load("metrics.json"), "model_card": card}

@router.get("/exercises")
def get_exercises():
    items = [{"id": item["exercise_id"], "display_order": item.get("display_order", item["exercise_id"]),
             "name_vi": DISPLAY_EXERCISE_NAMES.get(item["exercise_id"], item.get("exercise_vi", "")),
             "region_vi": item.get("region_vi", ""), "description": item.get("region_vi", ""),
             "semantics": EXERCISE_SEMANTICS.get(item["exercise_id"])}
            for item in model_loader.registry if "exercise_id" in item]
    items.append({"id": 6, "display_order": 6, "name_vi": DISPLAY_EXERCISE_NAMES[6], "region_vi": "Cổ · Vai", "description": "Bài tập rule-based, không train model."})
    return items

@router.post("/sessions", response_model=SessionResponse)
def create_session(payload: SessionCreate, response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _deprecated(response)
    if payload.exercise_id != 6 and payload.exercise_id not in model_loader.id_to_exercise:
        raise HTTPException(status_code=400, detail="Bài tập không hợp lệ.")
    if payload.pain_before >= 7:
        raise HTTPException(
            status_code=422,
            detail="Mức đau hiện tại quá cao để bắt đầu tập. Bạn nên dừng tập và liên hệ bác sĩ hoặc chuyên viên y tế để được đánh giá và điều trị phù hợp.",
        )
    import uuid
    item = ExerciseSession(session_uuid=str(uuid.uuid4()), user_id=user.id, exercise_id=payload.exercise_id,
        exercise_name=DISPLAY_EXERCISE_NAMES[payload.exercise_id], target_reps=payload.target_reps,
        pain_before=payload.pain_before, status="IN_PROGRESS")
    db.add(item); db.commit(); db.refresh(item)
    return _session_payload(item)

@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _deprecated(response)
    return [_session_payload(item) for item in db.query(ExerciseSession).filter(ExerciseSession.user_id == user.id).order_by(ExerciseSession.id.desc()).all()]

@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _deprecated(response)
    return _session_payload(_owned_session(db, session_id, user))

class SessionFinish(BaseModel):
    pain_after: int = Field(ge=0, le=10)
    rep_count: Optional[int] = Field(default=None, ge=0, le=30)

@router.post("/sessions/{session_id}/finish", response_model=SessionResponse)
def finish_session(session_id: str, payload: SessionFinish, response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _deprecated(response)
    item = _owned_session(db, session_id, user)
    item.pain_after = payload.pain_after; item.end_time = datetime.utcnow()
    repetition = payload.rep_count if payload.rep_count is not None else (item.metrics or {}).get("rep_count", 0)
    item.status = completion_status(repetition, item.target_reps, "ENDED")
    if payload.rep_count is not None: item.metrics = {**(item.metrics or {}), "rep_count": payload.rep_count}
    before = item.pain_before if item.pain_before is not None else 0
    if payload.pain_after >= 5 or payload.pain_after >= before + 2:
        item.recommendation = "Lần sau nên giảm số lần tập khoảng 20–30% và trao đổi với chuyên viên nếu đau còn tăng."
    elif payload.pain_after > before:
        item.recommendation = "Lần sau giữ nguyên hoặc giảm nhẹ số lần; tập chậm và dừng nếu đau tăng."
    else:
        item.recommendation = "Mức đau không tăng. Chỉ tăng số lần khi chuyên viên đồng ý và động tác vẫn không đau."
    db.commit(); db.refresh(item)
    return _session_payload(item)
