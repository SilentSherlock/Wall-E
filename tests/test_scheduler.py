from datetime import datetime, timezone

from walle_bot.services.scheduler import _build_startup_message


def test_build_startup_message_contains_required_text_and_time() -> None:
    now = datetime(2026, 3, 2, 12, 30, 45, tzinfo=timezone.utc)
    msg = _build_startup_message(now)

    assert "Wall-E机器人已启动" in msg
    assert "2026-03-02 12:30:45 UTC" in msg
