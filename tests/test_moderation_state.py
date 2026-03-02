from datetime import datetime, timedelta, timezone
from pathlib import Path

from walle_bot.services.state import ModerationState


def test_duplicate_content_detected_within_window(tmp_path: Path) -> None:
    state = ModerationState(tmp_path / "state.db")
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
    state.close()


def test_duplicate_link_detected_even_with_different_text(tmp_path: Path) -> None:
    state = ModerationState(tmp_path / "state.db")
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
    state.close()


def test_message_outside_window_not_detected(tmp_path: Path) -> None:
    state = ModerationState(tmp_path / "state.db")
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
    state.close()


def test_state_persists_history_and_violations(tmp_path: Path) -> None:
    db_path = tmp_path / "persistent.db"
    now = datetime.now(tz=timezone.utc)

    first_state = ModerationState(db_path)
    first_state.check_and_store(
        chat_id=5,
        user_id=9,
        message_id=900,
        text="spam link https://example.com/x",
        now=now,
        window_seconds=10,
    )
    assert first_state.add_violation(chat_id=5, user_id=9) == 1
    first_state.close()

    second_state = ModerationState(db_path)
    match = second_state.check_and_store(
        chat_id=5,
        user_id=9,
        message_id=901,
        text="new text https://example.com/x",
        now=now + timedelta(seconds=5),
        window_seconds=10,
    )
    assert match is not None
    assert match.reason == "duplicate_link"
    assert second_state.get_violation_count(chat_id=5, user_id=9) == 1
    second_state.close()


def test_state_persists_managed_chats(tmp_path: Path) -> None:
    db_path = tmp_path / "managed.db"

    first_state = ModerationState(db_path)
    assert first_state.add_managed_chat(chat_id=-1001, title="Group A")
    assert first_state.add_managed_chat(chat_id=-1002, title="Group B")
    assert not first_state.add_managed_chat(chat_id=-1001, title="Group A Updated")
    first_state.close()

    second_state = ModerationState(db_path)
    assert second_state.get_managed_chat_ids() == [-1002, -1001]
    second_state.close()
