from backend.chatbot.context import SUPPORTED_EXERCISE_IDS


def test_chatbot_scope_is_limited_to_master_exercises():
    assert SUPPORTED_EXERCISE_IDS == {2, 4}
