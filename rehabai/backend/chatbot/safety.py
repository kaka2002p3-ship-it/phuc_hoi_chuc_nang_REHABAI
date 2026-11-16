from __future__ import annotations

import re
import unicodedata


def _fold(value: str) -> str:
    """Case-fold and remove Vietnamese accents for robust safety matching."""
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


EMERGENCY_TERMS = (
    "meo mieng", "noi kho", "yeu liet dot ngot", "dau nguc", "kho tho nang",
    "ngat", "co giat", "khong tinh", "chay mau nhieu", "face drooping",
    "slurred speech", "chest pain", "severe difficulty breathing", "fainted",
)
CRISIS_TERMS = (
    "muon tu tu", "muon chet", "tu lam hai", "khong muon song", "kill myself",
    "suicide", "self-harm", "hurt myself",
)
RESTRICTION_TERMS = (
    "moi phau thuat", "sau phau thuat", "moi mo", "gay xuong", "bo bot",
    "dang nep", "bat dong", "bac si dan khong tap", "khong duoc van dong",
    "recent surgery", "fracture", "cast", "splint", "do not move",
)
PAIN_TERMS = ("dau", "te", "sung", "chong mat", "buot", "yeu hon", "pain", "numb", "swollen", "dizzy", "weaker")


def _contains(value: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", value) for term in terms)


def safety_reply(text: str, language: str = "vi") -> tuple[str, str] | None:
    value = _fold(text)
    english = language == "en"
    if _contains(value, CRISIS_TERMS):
        message = (
            "I’m sorry you’re going through this. Please stay with someone you trust, avoid being alone, and contact local emergency or crisis support now if you may hurt yourself."
            if english else
            "Mình rất tiếc vì bạn đang phải chịu cảm giác này. Hãy ở cạnh một người bạn tin tưởng, tránh ở một mình và gọi dịch vụ khẩn cấp tại nơi bạn đang ở ngay nếu bạn có thể làm hại bản thân."
        )
        return message, "SAFETY_SUPPORT"
    if _contains(value, EMERGENCY_TERMS):
        message = (
            "This may be an emergency warning sign. Stop exercising and contact local emergency services now, with help from someone nearby."
            if english else
            "Đây có thể là dấu hiệu khẩn cấp. Hãy dừng tập và gọi dịch vụ khẩn cấp tại nơi bạn đang ở, đồng thời nhờ người gần bạn hỗ trợ."
        )
        return message, "SAFETY_SUPPORT"
    if _contains(value, RESTRICTION_TERMS):
        message = (
            "Because you mentioned surgery, injury, or movement restrictions, I should not suggest an exercise. Please ask your treating clinician about permitted movement."
            if english else
            "Vì bạn đề cập phẫu thuật, chấn thương hoặc hạn chế vận động, mình không nên tự đưa bài tập. Bạn hãy hỏi chuyên viên đang điều trị về động tác được phép."
        )
        return message, "SAFETY_SUPPORT"
    if _contains(value, PAIN_TERMS):
        message = (
            "Please stop the exercise and rest. If the symptom is new, worsening, or does not improve, contact your clinician. I cannot diagnose through chat."
            if english else
            "Bạn hãy dừng bài tập và nghỉ. Nếu triệu chứng mới xuất hiện, tăng dần hoặc không giảm, hãy liên hệ chuyên viên phù hợp. Mình không thể chẩn đoán qua chat."
        )
        return message, "PAIN_REPORT"
    return None
