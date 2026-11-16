"""Canonical completion rules for exercise sessions."""


def completion_status(repetition: int | None, target_reps: int | None, stored_status: str) -> str:
    """Derive user-facing status from actual progress, including legacy rows."""
    if stored_status == "IN_PROGRESS":
        return "IN_PROGRESS"
    completed = max(0, int(repetition or 0))
    target = max(1, int(target_reps or 1))
    return "COMPLETED" if completed >= target else "INCOMPLETE"

