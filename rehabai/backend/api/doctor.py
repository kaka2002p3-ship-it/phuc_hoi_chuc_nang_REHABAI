"""Doctor APIs: patient viewing, exercise history, prescription assignment and notifications."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.db import (AuditEvent, DoctorSchedule, ExerciseSession, Notification,
                             Prescription, SessionRepetition, User, get_db)
from backend.core.exercise_names import DISPLAY_EXERCISE_NAMES
from backend.core.session_status import completion_status
from backend.core.security import current_user, doctor_or_admin

router = APIRouter()

VALID_EXERCISE_IDS = set(DISPLAY_EXERCISE_NAMES)


def _patient(user: User) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "phone": user.phone,
            "height_cm": user.height_cm, "weight_kg": user.weight_kg, "weekly_goal": user.weekly_goal,
            "created_at": user.created_at.isoformat()}


@router.get("/doctor/patients")
def list_patients(search: str | None = Query(default=None, max_length=160),
                  db: Session = Depends(get_db), doctor: User = Depends(doctor_or_admin)):
    query = db.query(User).filter(User.role == "patient", User.is_active == True)
    if search:
        needle = search.strip().lower()
        query = query.filter((User.full_name.ilike(f"%{needle}%")) | (User.email.ilike(f"%{needle}%")))
    return [_patient(user) for user in query.order_by(User.full_name).limit(500).all()]


@router.get("/doctor/patients/{patient_id}")
def patient_detail(patient_id: str, db: Session = Depends(get_db), doctor: User = Depends(doctor_or_admin)):
    patient = db.get(User, patient_id)
    if not patient or patient.role != "patient":
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân.")
    sessions = db.query(ExerciseSession).filter(ExerciseSession.user_id == patient_id).order_by(ExerciseSession.start_time.desc()).all()
    items = []
    for item in sessions:
        rows = db.query(SessionRepetition).filter(SessionRepetition.session_uuid == item.session_uuid).order_by(SessionRepetition.repetition_number).all()
        repetition = (item.metrics or {}).get("rep_count", 0)
        items.append({
            "id": item.session_uuid,
            "exercise_id": item.exercise_id,
            "exercise": item.exercise_name,
            "start_time": item.start_time.isoformat(),
            "end_time": item.end_time.isoformat() if item.end_time else None,
            "status": completion_status(repetition, item.target_reps, item.status),
            "repetition": repetition,
            "target_reps": item.target_reps,
            "pain_before": item.pain_before,
            "pain_after": item.pain_after,
            "recommendation": item.recommendation,
            "matched_reps": sum(row.movement_quality == 1.0 for row in rows),
            "mismatched_reps": sum(row.movement_quality == 0.0 for row in rows),
            "unassessed_reps": sum(row.movement_quality is None for row in rows),
            "form_quality": (item.metrics or {}).get("form_quality"),
            "speed_assessment": (item.metrics or {}).get("speed_assessment"),
        })
    active = db.query(Prescription).filter(Prescription.patient_id == patient_id, Prescription.status == "ACTIVE").all()
    return {**_patient(patient), "sessions": items, "active_prescriptions": [prescription_payload(row) for row in active]}


def prescription_payload(row: Prescription) -> dict:
    return {"id": row.id, "exercise_id": row.exercise_id, "exercise": row.exercise_name,
            "target_reps": row.target_reps, "sessions_per_day": row.sessions_per_day,
            "note": row.note, "status": row.status, "doctor_id": row.doctor_id,
            "created_at": row.created_at.isoformat()}


class PrescribeIn(BaseModel):
    patient_id: str
    exercise_id: int
    target_reps: int = Field(default=5, ge=1, le=30, description="Số lượt mỗi lần tập")
    sessions_per_day: int = Field(default=1, ge=1, le=14, description="Số lần tập mỗi ngày")
    note: str | None = Field(default=None, max_length=500)


@router.post("/doctor/prescriptions", status_code=201)
def prescribe(payload: PrescribeIn, db: Session = Depends(get_db), doctor: User = Depends(doctor_or_admin)):
    patient = db.get(User, payload.patient_id)
    if not patient or patient.role != "patient" or not patient.is_active:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân hợp lệ.")
    if payload.exercise_id not in VALID_EXERCISE_IDS:
        raise HTTPException(status_code=400, detail="Bài tập không hợp lệ.")
    existing = db.query(Prescription).filter(
        Prescription.patient_id == payload.patient_id,
        Prescription.exercise_id == payload.exercise_id,
        Prescription.status == "ACTIVE",
    ).first()
    if existing:
        existing.target_reps = payload.target_reps
        existing.sessions_per_day = payload.sessions_per_day
        existing.note = payload.note
        existing.updated_at = datetime.utcnow()
        row = existing
    else:
        row = Prescription(doctor_id=doctor.id, patient_id=patient.id,
                           exercise_id=payload.exercise_id,
                           exercise_name=DISPLAY_EXERCISE_NAMES[payload.exercise_id],
                           target_reps=payload.target_reps, sessions_per_day=payload.sessions_per_day,
                           note=payload.note, status="ACTIVE")
        db.add(row)
        db.flush()
    notification = Notification(
        user_id=patient.id,
        type="prescription_assigned",
        title="Bác sĩ đã giao bài tập mới",
        body=f"{DISPLAY_EXERCISE_NAMES[payload.exercise_id]}: {payload.target_reps} lượt × {payload.sessions_per_day} lần/ngày." + (f" Ghi chú: {payload.note}" if payload.note else ""),
        payload={"prescription_id": row.id, "exercise_id": payload.exercise_id},
    )
    db.add(notification)
    db.add(AuditEvent(user_id=doctor.id, action="prescription.create", resource_type="prescription",
                      resource_id=row.id,
                      payload={"patient_id": patient.id, "exercise_id": payload.exercise_id,
                               "target_reps": payload.target_reps, "sessions_per_day": payload.sessions_per_day}))
    db.commit()
    return prescription_payload(row)


class PrescriptionAction(BaseModel):
    action: str = Field(pattern="^(complete|cancel)$")


@router.post("/doctor/prescriptions/{prescription_id}")
def act_on_prescription(prescription_id: str, payload: PrescriptionAction,
                        db: Session = Depends(get_db), doctor: User = Depends(doctor_or_admin)):
    row = db.get(Prescription, prescription_id)
    if not row or row.doctor_id != doctor.id and doctor.role != "admin":
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn tập được phép chỉnh sửa.")
    if row.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Đơn tập đã ở trạng thái cuối (hoàn thành hoặc huỷ), không thể thay đổi.")
    row.status = "COMPLETED" if payload.action == "complete" else "CANCELLED"
    row.updated_at = datetime.utcnow()
    db.add(Notification(
        user_id=row.patient_id,
        type="prescription_completed" if payload.action == "complete" else "prescription_cancelled",
        title="Trạng thái đơn tập đã cập nhật",
        body=f"Đơn '{row.exercise_name}' ({row.target_reps} lượt × {row.sessions_per_day} lần/ngày) đã {'hoàn thành' if payload.action == 'complete' else 'bỏ qua'} do bác sĩ.",
        payload={"prescription_id": row.id},
    ))
    db.add(AuditEvent(user_id=doctor.id, action=f"prescription.{payload.action}", resource_type="prescription", resource_id=row.id))
    db.commit()
    return prescription_payload(row)


@router.get("/doctor/prescriptions")
def my_prescriptions(status: str | None = Query(default=None, pattern="^(ACTIVE|COMPLETED|CANCELLED)$"),
                     db: Session = Depends(get_db), doctor: User = Depends(doctor_or_admin)):
    query = db.query(Prescription).filter(Prescription.doctor_id == doctor.id)
    if status:
        query = query.filter(Prescription.status == status)
    rows = query.order_by(Prescription.created_at.desc()).all()
    # Resolve patient names in one pass so the doctor can see who each rx is for.
    patient_ids = {row.patient_id for row in rows}
    patients = {u.id: u for u in db.query(User).filter(User.id.in_(patient_ids)).all()} if patient_ids else {}
    return [{**prescription_payload(row), "patient_id": row.patient_id,
             "patient": patients.get(row.patient_id).full_name if patients.get(row.patient_id) else None}
            for row in rows]


# 24-hour clock, validated to a real time of day: hours 00–23, minutes 00–59.
_TIME_RE = r"^([01]\d|2[0-3]):[0-5]\d$"


class ScheduleIn(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: str = Field(pattern=_TIME_RE)
    end_time: str = Field(pattern=_TIME_RE)
    note: str | None = Field(default=None, max_length=200)


@router.get("/doctor/schedule")
def my_schedule(db: Session = Depends(get_db), doctor: User = Depends(doctor_or_admin)):
    rows = db.query(DoctorSchedule).filter(DoctorSchedule.doctor_id == doctor.id).order_by(DoctorSchedule.day_of_week).all()
    return [{"day_of_week": row.day_of_week, "start_time": row.start_time, "end_time": row.end_time, "note": row.note} for row in rows]


@router.put("/doctor/schedule")
def set_my_schedule(payload: list[ScheduleIn], db: Session = Depends(get_db), doctor: User = Depends(doctor_or_admin)):
    db.query(DoctorSchedule).filter(DoctorSchedule.doctor_id == doctor.id).delete()
    for item in payload:
        db.add(DoctorSchedule(doctor_id=doctor.id, day_of_week=item.day_of_week,
                              start_time=item.start_time, end_time=item.end_time, note=item.note))
    db.add(AuditEvent(user_id=doctor.id, action="doctor_schedule.update", resource_type="doctor", resource_id=doctor.id))
    db.commit()
    return {"message": "Đã cập nhật lịch làm việc."}
