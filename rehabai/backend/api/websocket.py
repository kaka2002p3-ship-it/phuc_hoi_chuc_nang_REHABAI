import json
import base64
import numpy as np
import cv2
import os
import time
import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.core.db import SessionLocal, ExerciseSession, SessionRepetition
from backend.core.mediapipe_extractor import RealtimeExtractor
from backend.core.model_loader import model_loader
from backend.core.exercise_names import DISPLAY_EXERCISE_NAMES
from backend.core.rep_counter import RuleBasedRepCounter
from backend.core.form_quality import FormQualityTracker
from backend.core.neck_lateral_stretch import NeckLateralStretchCounter
from backend.core.security import user_id_from_token
from backend.core.logging_config import get_logger
from backend.ml.inference.smooth_predictions import EnsemblePredictor

# Initialize WebSocket logger
ws_logger = get_logger("rehabai.websocket")

router = APIRouter()
MATCH_CONFIDENCE_THRESHOLD = float(os.environ.get("MATCH_CONFIDENCE_THRESHOLD", "0.70"))
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10MB max message size
SESSION_TIMEOUT_SECONDS = 3600  # 1 hour session timeout

# Global prediction smoother for real-time inference
# Uses temporal smoothing + confidence voting + Kalman filtering
_prediction_smoother: EnsemblePredictor | None = None

def get_prediction_smoother() -> EnsemblePredictor:
    """Get or create the global prediction smoother."""
    global _prediction_smoother
    if _prediction_smoother is None:
        _prediction_smoother = EnsemblePredictor(
            window_size=5,
            confirmations_needed=2,
            min_confidence=0.5,
        )
    return _prediction_smoother

def reset_prediction_smoother():
    """Reset the prediction smoother (call when session ends)."""
    global _prediction_smoother
    if _prediction_smoother is not None:
        _prediction_smoother.reset()

def classify_selected_exercise(predicted_id: int, selected_id: int | None, confidence: float,
                               quality: dict) -> str:
    sufficient = bool(quality.get("ready")) and float(quality.get("landmark_rate", 0.0)) >= 0.60
    if selected_id is None or not sufficient or confidence < MATCH_CONFIDENCE_THRESHOLD:
        return "unassessed"
    return "matched" if predicted_id == selected_id else "mismatched"

def decode_image(b64_string: str) -> np.ndarray:
    """ Decode base64 image (JPEG/WebP) to numpy array (RGB) """
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_data = base64.b64decode(b64_string)
    np_arr = np.frombuffer(img_data, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Cannot decode image")
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return img_rgb

@router.websocket("/ws/inference")
@router.websocket("/ws/exercise/{path_session_id}")
async def websocket_inference(websocket: WebSocket, path_session_id: str | None = None):
    token = websocket.query_params.get("token", "")
    session_id = path_session_id
    client_id = None

    try:
        user_id = user_id_from_token(token)
        client_id = f"{user_id[:8]}@{session_id[:8] if session_id else 'preview'}"
    except Exception as e:
        ws_logger.warning(f"WebSocket auth failed", extra={"error": str(e)})
        await websocket.close(code=1008, reason="Authentication required")
        return

    await websocket.accept()
    ws_logger.info(f"WebSocket connected", extra={"client_id": client_id, "session_id": session_id})

    # Initialize MediaPipe only after the first valid frame request.
    extractor = None
    selected_exercise_id = None
    rep_counter = None
    neck_counter = None
    form_tracker = None
    persisted_rep_count = 0
    last_prediction_match: bool | None = None
    frame_count = 0
    error_count = 0
    max_errors = 10
    session_start = time.time()

    try:
        while True:
            # Check session timeout
            if time.time() - session_start > SESSION_TIMEOUT_SECONDS:
                ws_logger.info("Session timeout", extra={"session_id": session_id, "client_id": client_id})
                await websocket.send_json({"error": "Session timeout", "code": "SESSION_TIMEOUT"})
                break

            try:
                data_text = await websocket.receive_text()
            except Exception as e:
                ws_logger.error(f"Receive error", extra={"client_id": client_id, "error": str(e)})
                break

            # Rate limit message size
            if len(data_text) > MAX_MESSAGE_SIZE:
                ws_logger.warning(f"Message too large", extra={"client_id": client_id, "size": len(data_text)})
                await websocket.send_json({"error": "Message too large"})
                continue

            try:
                data = json.loads(data_text)
            except json.JSONDecodeError as e:
                ws_logger.debug(f"Invalid JSON", extra={"client_id": client_id, "error": str(e)})
                await websocket.send_json({"error": "Invalid JSON format"})
                continue

            frame_b64 = data.get("frame")
            timestamp = data.get("timestamp")
            current_session_id = data.get("session_id") or path_session_id

            # Handle session initialization
            if current_session_id and selected_exercise_id is None:
                try:
                    db = SessionLocal()
                    selected = db.query(ExerciseSession).filter(
                        ExerciseSession.session_uuid == current_session_id,
                        ExerciseSession.user_id == user_id,
                    ).first()
                    if selected:
                        selected_exercise_id = selected.exercise_id
                        if selected_exercise_id == 6:
                            neck_counter = NeckLateralStretchCounter()
                            ws_logger.info("Initialized neck counter", extra={"session_id": current_session_id})
                        else:
                            rep_counter = RuleBasedRepCounter(selected_exercise_id)
                            form_tracker = FormQualityTracker(selected_exercise_id)
                            ws_logger.info("Initialized rep counter", extra={"exercise_id": selected_exercise_id})
                        persisted_rep_count = db.query(SessionRepetition).filter(
                            SessionRepetition.session_uuid == current_session_id
                        ).count()
                        if rep_counter is not None:
                            rep_counter.rep_count = persisted_rep_count
                    db.close()

                    if selected is None:
                        ws_logger.warning("Session not found", extra={"session_id": current_session_id})
                        await websocket.send_json({"error": "Session not found"})
                        await websocket.close(code=1008)
                        return

                    reset_prediction_smoother()
                    ws_logger.info("Session initialized", extra={"session_id": current_session_id, "exercise_id": selected_exercise_id})
                except Exception as e:
                    ws_logger.error(f"Session init error", extra={"error": str(e)}, exc_info=True)
                    await websocket.send_json({"error": "Failed to initialize session"})
                    continue

            if not frame_b64:
                await websocket.send_json({"error": "Missing frame data"})
                continue

            if extractor is None:
                extractor = RealtimeExtractor(window_size=96, stride=5)
                ws_logger.info("MediaPipe extractor initialized")

            # Process frame with error tracking
            try:
                img_rgb = decode_image(frame_b64)
            except Exception as e:
                error_count += 1
                ws_logger.debug(f"Image decode failed", extra={"client_id": client_id, "error": str(e)})
                if error_count >= max_errors:
                    await websocket.send_json({"error": f"Too many decode errors ({error_count})"})
                    break
                await websocket.send_json({"error": f"Image decode failed: {str(e)}"})
                continue

            features = extractor.process_frame(img_rgb)
            frame_count += 1

            response = {
                "timestamp": timestamp,
                "skeleton": extractor.get_skeleton()
            }
            preview_mode = bool(data.get("preview")) and not current_session_id
            requested_exercise_id = data.get("exercise_id") if preview_mode else selected_exercise_id
            response["quality"] = extractor.quality_status(requested_exercise_id, min_frames=24 if preview_mode else None)

            if neck_counter is not None:
                skeleton = extractor.get_skeleton()
                pose = np.asarray(skeleton["pose"], dtype=np.float32) if skeleton else np.zeros((33, 3), dtype=np.float32)
                response["rep"] = neck_counter.update(pose, float(timestamp or 0) / 1000.0, bool(response["quality"].get("ready")))
            elif rep_counter is not None:
                skeleton = extractor.get_skeleton()
                pose = np.asarray(skeleton["pose"], dtype=np.float32) if skeleton else np.zeros((33, 3), dtype=np.float32)
                left = np.asarray(skeleton["left_hand"], dtype=np.float32) if skeleton else None
                right = np.asarray(skeleton["right_hand"], dtype=np.float32) if skeleton else None
                response["rep"] = rep_counter.update(pose, left, right, bool(response["quality"].get("ready")))

            # Rule-based form/pace check: angle span + speed of each completed
            # repetition cycle. Surfaced live and persisted into session metrics.
            if form_tracker is not None and current_session_id:
                active_count = neck_counter.rep_count if neck_counter else rep_counter.rep_count
                new_reps = form_tracker.observe(float(timestamp or 0) / 1000.0, active_count,
                                                response.get("rep", {}).get("signal"))
                if new_reps:
                    response["form_quality"] = [FormQualityTracker._record_payload(item) for item in new_reps]

            # Inference
            if features is not None and selected_exercise_id != 6:
                try:
                    if not response["quality"].get("ready"):
                        await websocket.send_json(response)
                        continue

                    pred = model_loader.predict(features)

                    smoother = get_prediction_smoother()
                    smoothed = smoother.predict(
                        exercise_id=pred["exercise_id"],
                        confidence=float(pred["confidence"]),
                        probabilities=pred.get("probabilities"),
                    )

                    smoothed_exercise_id = smoothed["exercise_id"]
                    smoothed_confidence = smoothed["confidence"]
                    smoothed_ready = smoothed.get("ready_for_use", False)

                    ex_info = model_loader.id_to_exercise.get(smoothed_exercise_id, {})
                    quality = response["quality"]
                    assessment_confidence = smoothed_confidence if smoothed_ready else float(pred["confidence"])
                    assessment = classify_selected_exercise(
                        smoothed_exercise_id, selected_exercise_id if current_session_id else None, assessment_confidence, quality
                    )

                    response["inference"] = {
                        "exercise_id": smoothed_exercise_id,
                        "exercise_name_vi": DISPLAY_EXERCISE_NAMES.get(smoothed_exercise_id, ex_info.get("exercise_vi", "Unknown")),
                        "region_vi": ex_info.get("region_vi", "Unknown"),
                        "confidence": assessment_confidence,
                        "confidence_threshold": MATCH_CONFIDENCE_THRESHOLD,
                        "assessment": assessment,
                        "smoothed": smoothed.get("temporal_smoothed", False),
                        "vote_confirmations": smoothed.get("vote_confirmations", 0),
                        "raw_confidence": float(pred["confidence"]),
                        "completion_status": None,
                        "rep_count": neck_counter.rep_count if neck_counter else (rep_counter.rep_count if rep_counter else 0),
                        "rep_count_estimated": True,
                        "phase": None,
                        "quality_score": None,
                        "feedback_vi": "Chưa có đánh giá lỗi chi tiết"
                    }

                    if current_session_id:
                        db = SessionLocal()
                        db_session = db.query(ExerciseSession).filter(
                            ExerciseSession.session_uuid == current_session_id,
                            ExerciseSession.user_id == user_id,
                        ).first()
                        if db_session:
                            response["inference"]["selected_exercise_id"] = db_session.exercise_id
                            response["inference"]["selected_exercise_name_vi"] = db_session.exercise_name
                            response["inference"]["matches_selected"] = assessment == "matched"
                            response["inference"]["assessment"] = assessment
                            if assessment == "matched":
                                last_prediction_match = True
                            elif assessment == "mismatched":
                                last_prediction_match = False
                            db.commit()
                        db.close()

                except Exception as e:
                    error_count += 1
                    ws_logger.error(f"Inference error", extra={"error": str(e), "frame": frame_count})
                    response["inference_error"] = str(e)
                    if error_count >= max_errors:
                        await websocket.send_json(response)
                        ws_logger.error("Too many inference errors, closing connection")
                        break

            # Persist repetitions
            active_count = neck_counter.rep_count if neck_counter else (rep_counter.rep_count if rep_counter else 0)
            if current_session_id and (rep_counter is not None or neck_counter is not None) and active_count > persisted_rep_count:
                db = SessionLocal()
                try:
                    owned_session = db.query(ExerciseSession).filter(
                        ExerciseSession.session_uuid == current_session_id,
                        ExerciseSession.user_id == user_id,
                    ).first()
                    if owned_session:
                        while persisted_rep_count < active_count:
                            persisted_rep_count += 1
                            db.add(SessionRepetition(
                                session_uuid=current_session_id,
                                repetition_number=persisted_rep_count,
                                movement_quality=(None if last_prediction_match is None else float(last_prediction_match)),
                            ))
                        # Persist the rule-based form/pace summary so reports and
                        # the doctor view can show "tập đúng/sai + tốc độ".
                        if form_tracker is not None and form_tracker.records:
                            owned_session.metrics = {**(owned_session.metrics or {}),
                                                     "form_quality": form_tracker.session_summary(),
                                                     "speed_assessment": form_tracker.session_summary()["pace"]}
                        db.commit()
                        last_prediction_match = None
                finally:
                    db.close()

            await websocket.send_json(response)

    except WebSocketDisconnect:
        duration = time.time() - session_start
        ws_logger.info("Client disconnected", extra={
            "client_id": client_id,
            "frames_processed": frame_count,
            "errors": error_count,
            "duration_seconds": round(duration, 1)
        })
    except Exception as e:
        ws_logger.error(f"WebSocket error", extra={"client_id": client_id, "error": str(e)}, exc_info=True)
        try:
            await websocket.send_json({"error": f"Connection error: {str(e)}"})
            await websocket.close(code=1011)
        except:
            pass
    finally:
        reset_prediction_smoother()
