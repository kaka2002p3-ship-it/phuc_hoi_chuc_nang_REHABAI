"""Admin APIs: account/role management, system audit log and clinic settings."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.core.db import (AuditEvent, ClinicInfo, DoctorSchedule, Notification,
                             Prescription, User, get_db)
from backend.core.security import admin_only, hash_password
from backend.core.exercise_names import DISPLAY_EXERCISE_NAMES

router = APIRouter()


def audit(db: Session, admin: User, action: str, resource_type: str, resource_id: str | None = None, payload: dict | None = None):
    db.add(AuditEvent(user_id=admin.id, action=action, resource_type=resource_type, resource_id=resource_id, payload=payload))


def account_payload(user: User) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "phone": user.phone,
            "role": user.role, "is_active": user.is_active, "created_at": user.created_at.isoformat()}


class CreateAccountIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(doctor|patient)$")
    phone: str | None = Field(default=None, max_length=32)


@router.post("/admin/users", status_code=201)
def create_account(payload: CreateAccountIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email đã được sử dụng.")
    user = User(email=email, full_name=payload.full_name.strip(), role=payload.role,
                 phone=payload.phone, password_hash=hash_password(payload.password), is_active=True)
    db.add(user); db.flush()
    audit(db, admin, "account.create", "user", user.id, {"email": email, "role": payload.role})
    db.commit(); db.refresh(user)
    return account_payload(user)


class RoleIn(BaseModel):
    role: str = Field(pattern="^(admin|doctor|patient)$")


@router.put("/admin/users/{user_id}/role")
def set_role(user_id: str, payload: RoleIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if user.role == "admin" and payload.role != "admin":
        admins = db.query(User).filter(User.role == "admin", User.is_active == True).count()
        if admins <= 1:
            raise HTTPException(status_code=409, detail="Hệ thống cần giữ lại ít nhất một quản trị viên.")
    previous_role = user.role
    user.role = payload.role; user.updated_at = datetime.utcnow()
    audit(db, admin, "account.role_change", "user", user.id, {"from": previous_role, "to": payload.role})
    db.commit()
    return account_payload(user)


class ActiveIn(BaseModel):
    is_active: bool


@router.put("/admin/users/{user_id}/active")
def set_active(user_id: str, payload: ActiveIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if user.role == "admin" and not payload.is_active:
        admins = db.query(User).filter(User.role == "admin", User.is_active == True).count()
        if admins <= 1:
            raise HTTPException(status_code=409, detail="Hệ thống cần giữ lại ít nhất một quản trị viên đang hoạt động.")
    user.is_active = payload.is_active; user.updated_at = datetime.utcnow()
    audit(db, admin, "account.activate" if payload.is_active else "account.deactivate", "user", user.id)
    db.commit()
    return account_payload(user)


@router.get("/admin/users")
def list_accounts(role: str | None = Query(default=None, pattern="^(admin|doctor|patient)$"),
                 db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return [account_payload(user) for user in query.order_by(User.created_at.desc()).limit(500).all()]


class AccountIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=32)


@router.put("/admin/users/{user_id}")
def update_account(user_id: str, payload: AccountIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if payload.full_name:
        user.full_name = payload.full_name.strip()
    user.phone = payload.phone
    user.updated_at = datetime.utcnow()
    audit(db, admin, "account.update", "user", user.id)
    db.commit()
    return account_payload(user)


class PasswordIn(BaseModel):
    password: str = Field(min_length=8, max_length=128)


@router.put("/admin/users/{user_id}/password")
def reset_password(user_id: str, payload: PasswordIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    user.password_hash = hash_password(payload.password)
    user.updated_at = datetime.utcnow()
    audit(db, admin, "account.password_reset", "user", user.id)
    db.commit()
    return {"message": "Đã đặt lại mật khẩu."}


@router.get("/admin/audit-logs")
def audit_logs(limit: int = Query(default=100, ge=1, le=1000),
               resource_type: str | None = None,
               db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    query = db.query(AuditEvent)
    if resource_type:
        query = query.filter(AuditEvent.resource_type == resource_type)
    rows = query.order_by(AuditEvent.created_at.desc()).limit(limit).all()
    return [{
        "id": row.id,
        "user_id": row.user_id,
        "user_email": (db.get(User, row.user_id).email if row.user_id else None),
        "action": row.action,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "payload": row.payload,
        "created_at": row.created_at.isoformat(),
    } for row in rows]


@router.get("/admin/health-summary")
def health_summary(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    """Server load snapshot: account counts, active sessions, recent activity."""
    active_sessions = db.query(Prescription).filter(Prescription.status == "ACTIVE").count()
    return {
        "accounts": {role: db.query(User).filter(User.role == role).count() for role in ("admin", "doctor", "patient")},
        "active_accounts": db.query(User).filter(User.is_active == True).count(),
        "active_prescriptions": active_sessions,
        "audit_events_today": db.query(AuditEvent).filter(AuditEvent.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)).count(),
    }


class ClinicIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=32)
    notes: dict | None = None


@router.put("/admin/clinic")
def update_clinic(payload: ClinicIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    row = db.query(ClinicInfo).first()
    if not row:
        row = ClinicInfo(id="clinic", name=payload.name, address=payload.address, phone=payload.phone, notes=payload.notes)
        db.add(row)
    else:
        row.name = payload.name
        row.address = payload.address if payload.address is not None else row.address
        row.phone = payload.phone if payload.phone is not None else row.phone
        row.notes = payload.notes
        row.updated_at = datetime.utcnow()
    audit(db, admin, "clinic.update", "clinic", "clinic", {"name": payload.name})
    db.commit()
    return {"name": row.name, "address": row.address, "phone": row.phone, "notes": row.notes}


_TIME_RE = r"^([01]\d|2[0-3]):[0-5]\d$"


class ScheduleIn(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: str = Field(pattern=_TIME_RE)
    end_time: str = Field(pattern=_TIME_RE)
    note: str | None = Field(default=None, max_length=200)


@router.put("/admin/schedules/{doctor_id}")
def update_doctor_schedule(doctor_id: str, payload: list[ScheduleIn], db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    doctor = db.get(User, doctor_id)
    if not doctor or doctor.role not in {"doctor", "admin"}:
        raise HTTPException(status_code=404, detail="Không tìm thấy bác sĩ.")
    db.query(DoctorSchedule).filter(DoctorSchedule.doctor_id == doctor_id).delete()
    for item in payload:
        db.add(DoctorSchedule(doctor_id=doctor_id, day_of_week=item.day_of_week,
                              start_time=item.start_time, end_time=item.end_time, note=item.note))
    audit(db, admin, "doctor_schedule.update", "doctor", doctor_id, {"days": [item.day_of_week for item in payload]})
    db.commit()
    return get_doctor_schedule(doctor_id, db, doctor)


def get_doctor_schedule(doctor_id: str, db: Session, actor: User) -> list[dict]:
    return [{"id": row.id, "day_of_week": row.day_of_week, "start_time": row.start_time,
             "end_time": row.end_time, "note": row.note}
            for row in db.query(DoctorSchedule).filter(DoctorSchedule.doctor_id == doctor_id).order_by(DoctorSchedule.day_of_week).all()]


@router.get("/admin/schedules/{doctor_id}")
def get_admin_doctor_schedule(doctor_id: str, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    target = db.get(User, doctor_id)
    if not target or target.role not in {"doctor", "admin"}:
        raise HTTPException(status_code=404, detail="Không tìm thấy bác sĩ.")
    return get_doctor_schedule(doctor_id, db, admin)


@router.get("/admin/notifications")
def broadcast(target_role: str = Query(default="patient", pattern="^(patient|doctor)$"),
              db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    """Preview of who would receive a broadcast (used before POSTing one)."""
    users = db.query(User).filter(User.role == target_role, User.is_active == True).all()
    return {"target_role": target_role, "recipients": [account_payload(user) for user in users]}


class BroadcastIn(BaseModel):
    target_role: str = Field(default="patient", pattern="^(patient|doctor)$")
    title: str = Field(min_length=2, max_length=200)
    body: str | None = Field(default=None, max_length=600)


@router.post("/admin/broadcast", status_code=201)
def broadcast_message(payload: BroadcastIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    users = db.query(User).filter(User.role == payload.target_role, User.is_active == True).all()
    for user in users:
        db.add(Notification(user_id=user.id, type="system", title=payload.title, body=payload.body))
    audit(db, admin, "notification.broadcast", "user", admin.id, {"target_role": payload.target_role, "recipients": len(users)})
    db.commit()
    return {"recipients": len(users)}
