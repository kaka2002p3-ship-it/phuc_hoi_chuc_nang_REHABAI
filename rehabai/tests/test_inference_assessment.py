from backend.api.websocket import MATCH_CONFIDENCE_THRESHOLD, classify_selected_exercise


def test_two_exercise_assessment_requires_confidence_and_quality():
    good = {"ready": True, "landmark_rate": 1.0}
    assert classify_selected_exercise(4, 4, MATCH_CONFIDENCE_THRESHOLD, good) == "matched"
    assert classify_selected_exercise(2, 4, MATCH_CONFIDENCE_THRESHOLD, good) == "mismatched"
    assert classify_selected_exercise(4, 4, MATCH_CONFIDENCE_THRESHOLD - 0.01, good) == "unassessed"
    assert classify_selected_exercise(4, 4, 0.99, {"ready": False, "landmark_rate": 1.0}) == "unassessed"
    assert classify_selected_exercise(4, 4, 0.99, {"ready": True, "landmark_rate": 0.59}) == "unassessed"
