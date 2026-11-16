"""Notification APIs: patient inbox, read receipts, and clinic information."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.core.db import ClinicInfo, DoctorSchedule, Notification, Prescription, User, get_db
from backend.core.security import current_user

router = APIRouter()


def notification_payload(row: Notification) -> dict:
    return {"id": row.id, "type": row.type, "title": row.title, "body": row.body,
            "payload": row.payload, "is_read": row.is_read, "created_at": row.created_at.isoformat()}


@router.get("/notifications")
def list_notifications(limit: int = Query(default=50, ge=1, le=200),
                       db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(limit).all()
    return {"unread": len(rows) - sum(1 for row in rows if row.is_read), "items": [notification_payload(row) for row in rows]}


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    row = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo.")
    row.is_read = True
    db.commit()
    return notification_payload(row)


@router.post("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).all()
    for row in rows:
        row.is_read = True
    db.commit()
    return {"marked": len(rows)}


# ---------------------------------------------------------------------------
# Clinic information (admin-managed, public read; also mirrored into the
# knowledge base so the chatbot can answer questions about the clinic)
# ---------------------------------------------------------------------------

def clinic_default() -> dict:
    return {"name": "RehabAI",
            "address": "cc Tecco Phù Liên, Phan Đình Phùng, Thái Nguyên",
            "phone": "0978469616",
            "notes": None}


@router.get("/clinic")
def clinic_info(db: Session = Depends(get_db)):
    """Public clinic information; any visitor may read it."""
    row = db.query(ClinicInfo).first()
    base = clinic_default()
    return {"name": row.name if row else base["name"],
            "address": row.address if row else base["address"],
            "phone": row.phone if row else base["phone"],
            "notes": row.notes if row else base["notes"]}


@router.get("/clinic/doctor-schedules")
def doctor_schedules(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Combined working-hours rows across all active doctors, for the clinic page."""
    rows = (db.query(DoctorSchedule)
            .join(User, User.id == DoctorSchedule.doctor_id)
            .filter(User.role.in_(["doctor", "admin"]), User.is_active == True)
            .order_by(DoctorSchedule.day_of_week, DoctorSchedule.start_time).all())
    return [{"day_of_week": row.day_of_week, "start_time": row.start_time, "end_time": row.end_time, "note": row.note}
            for row in rows]


@router.get("/clinic/my-prescriptions")
def my_prescriptions(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Patient's active and recent exercise assignments from their doctor."""
    rows = db.query(Prescription).filter(Prescription.patient_id == user.id).order_by(Prescription.created_at.desc()).limit(50).all()
    return [
        {"id": row.id, "exercise_id": row.exercise_id, "exercise": row.exercise_name,
         "target_reps": row.target_reps, "sessions_per_day": row.sessions_per_day,
         "note": row.note, "status": row.status, "doctor_id": row.doctor_id,
         "created_at": row.created_at.isoformat()}
        for row in rows
    ]
