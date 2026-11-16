from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.core.db import ExerciseSession, SessionRepetition, User
from backend.knowledge.retriever import retrieve

SUPPORTED_EXERCISE_IDS = {2, 4}
HISTORY_LIMIT = 30
KNOWLEDGE_SCOPES = {"SAFETY", "PRODUCT_HELP", "HAND_OPENING", "ELBOW_EXTENSION", "NUTRITION_GENERAL", "CLINIC_INFO"}


def _knowledge_evidence(items: list[dict]) -> list[dict]:
    return [{"evidence_id": item["evidence_id"], "kind": "approved_knowledge", "review_status": "approved"} for item in items]


def _tracking_status(item: ExerciseSession, metrics: dict) -> str:
    value = metrics.get("tracking_status")
    if value in {"available", "lost", "in_progress", "unknown"}:
        return value
    # Existing sessions do not persist frame-level tracking evidence. Do not
    # claim that tracking was available merely because the row exists.
    return "unknown"


def _session_snapshot(db: Session, item: ExerciseSession) -> tuple[dict, str]:
    observed = item.end_time or item.start_time
    age = (datetime.now(timezone.utc).replace(tzinfo=None) - observed).total_seconds()
    data_status = "stale" if age > 86400 else "available"
    evidence_id = f"session_{item.session_uuid}"
    metrics = item.metrics if isinstance(item.metrics, dict) else {}
    repetition_rows = db.query(SessionRepetition).filter(
        SessionRepetition.session_uuid == item.session_uuid
    ).order_by(SessionRepetition.repetition_number).all()
    correct_reps = sum(row.movement_quality == 1.0 for row in repetition_rows)
    incorrect_reps = sum(row.movement_quality == 0.0 for row in repetition_rows)
    unassessed_reps = sum(row.movement_quality is None for row in repetition_rows)
    snapshot = {
            "session_id": item.session_uuid,
            "exercise_id": item.exercise_id,
            "exercise_name": item.exercise_name,
            "observed_at": observed.isoformat(),
            "data_status": data_status,
            "tracking_status": _tracking_status(item, metrics),
            "model_version": metrics.get("model_version", "artifact-owned"),
            "repetition_count": metrics.get("rep_count"),
            "target_reps": item.target_reps,
            "matched_reps": correct_reps,
            "mismatched_reps": incorrect_reps,
            "complete_reps": correct_reps,
            "incomplete_reps": incorrect_reps,
            "unassessed_reps": unassessed_reps,
            "repetition_result_semantics": {
                "matched": "classifier confidence passed threshold and predicted the selected exercise; not a technique-quality judgment",
                "mismatched": "classifier confidence passed threshold and predicted the other supported exercise; not a technique-quality judgment",
                "unassessed": "confidence, tracking, or evidence was insufficient",
            },
            "repetitions": [{
                "repetition_number": row.repetition_number,
                "result": "matched" if row.movement_quality == 1.0 else "mismatched" if row.movement_quality == 0.0 else "unassessed",
                "recorded_at": row.created_at.isoformat(),
            } for row in repetition_rows],
            "validated_feedback_events": metrics.get("validated_feedback_events", []),
            "pain_before": item.pain_before,
            "pain_after": item.pain_after,
            "pain_scale": "0-10",
        }
    return snapshot, evidence_id


def build_context(db: Session, user: User, session_id: str | None, query: str | None = None) -> tuple[dict, set[str], str | None]:
    owned = db.query(ExerciseSession).filter(ExerciseSession.user_id == user.id)
    if session_id:
        item = owned.filter(ExerciseSession.session_uuid == session_id).first()
        if not item:
            return {"context_version": "1.1", "data_status": "unavailable", "approved_memory": []}, set(), "ACCESS_DENIED"
        if item.exercise_id not in SUPPORTED_EXERCISE_IDS:
            return {"context_version": "1.1", "data_status": "unavailable", "approved_memory": []}, set(), "UNSUPPORTED_EXERCISE"
        snapshot, evidence_id = _session_snapshot(db, item)
        knowledge, knowledge_ids, knowledge_version = retrieve(query or "", scopes=KNOWLEDGE_SCOPES)
        context = {
            "context_version": "1.1",
            "scope": "selected_session_owned_by_authenticated_user",
            "session": snapshot,
            "exercise_history": [snapshot],
            "data_status": snapshot["data_status"],
            "evidence": [{"evidence_id": evidence_id, "kind": "session_snapshot", "review_status": "backend_verified"}, *_knowledge_evidence(knowledge)],
            "approved_knowledge": knowledge,
            "knowledge_version": knowledge_version,
            "approved_memory": [],
        }
        return context, {evidence_id} | knowledge_ids, None

    items = owned.filter(ExerciseSession.exercise_id.in_(SUPPORTED_EXERCISE_IDS)).order_by(
        ExerciseSession.start_time.desc()
    ).limit(HISTORY_LIMIT).all()
    snapshots, evidence_ids = [], set()
    for item in items:
        snapshot, evidence_id = _session_snapshot(db, item)
        snapshots.append(snapshot)
        evidence_ids.add(evidence_id)
    knowledge, knowledge_ids, knowledge_version = retrieve(query or "", scopes=KNOWLEDGE_SCOPES)
    context = {
        "context_version": "1.1",
        "scope": "recent_history_owned_by_authenticated_user",
        "data_status": "available" if snapshots else "unavailable",
        "history_limit": HISTORY_LIMIT,
        "exercise_history": snapshots,
        "evidence": [],
        "approved_knowledge": knowledge,
        "knowledge_version": knowledge_version,
        "approved_memory": [],
    }
    context["evidence"] = [{"evidence_id": value, "kind": "session_snapshot", "review_status": "backend_verified"} for value in sorted(evidence_ids)] + _knowledge_evidence(knowledge)
    return context, evidence_ids | knowledge_ids, None
