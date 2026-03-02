from datetime import datetime, timedelta, timezone

from walle_bot.services.state import ModerationState


def test_duplicate_content_detected_within_window() -> None:
    state = ModerationState()
    now = datetime.now(tz=timezone.utc)

    first = state.check_and_store(
        chat_id=1,
        user_id=10,
        message_id=100,
        text="Buy now!!!",
        now=now,
        window_seconds=10,
    )
    second = state.check_and_store(
        chat_id=1,
        user_id=10,
        message_id=101,
        text="Buy now!!!",
        now=now + timedelta(seconds=5),
        window_seconds=10,
    )

    assert first is None
    assert second is not None
    assert second.reason == "duplicate_content"
    assert second.matched_message_ids == (100,)


def test_duplicate_link_detected_even_with_different_text() -> None:
    state = ModerationState()
    now = datetime.now(tz=timezone.utc)

    state.check_and_store(
        chat_id=1,
        user_id=10,
        message_id=200,
        text="check this https://example.com/a",
        now=now,
        window_seconds=10,
    )
    second = state.check_and_store(
        chat_id=1,
        user_id=10,
        message_id=201,
        text="another title https://example.com/a",
        now=now + timedelta(seconds=8),
        window_seconds=10,
    )

    assert second is not None
    assert second.reason == "duplicate_link"


def test_message_outside_window_not_detected() -> None:
    state = ModerationState()
    now = datetime.now(tz=timezone.utc)

    state.check_and_store(
        chat_id=1,
        user_id=10,
        message_id=300,
        text="hello",
        now=now,
        window_seconds=10,
    )
    second = state.check_and_store(
        chat_id=1,
        user_id=10,
        message_id=301,
        text="hello",
        now=now + timedelta(seconds=11),
        window_seconds=10,
    )

    assert second is None
