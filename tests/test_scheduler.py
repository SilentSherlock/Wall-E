from datetime import datetime, timedelta, timezone

from walle_bot.services.scheduler import (
    _build_startup_message,
    _build_time_message,
    _seconds_until_next_eight_hour_mark,
)


def test_build_startup_message_contains_required_text_and_time() -> None:
    now = datetime(2026, 3, 2, 12, 30, 45, tzinfo=timezone(timedelta(hours=8)))
    msg = _build_startup_message(now)

    assert "Wall-E机器人已重启" in msg
    assert "2026-03-02 12:30:45" in msg


def test_build_time_message_uses_beijing_label() -> None:
    now = datetime(2026, 3, 2, 13, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    msg = _build_time_message(now)

    assert "每8小时播报" in msg
    assert "北京时间" in msg
    assert "2026-03-02 13:00:00" in msg


def test_seconds_until_next_eight_hour_mark() -> None:
    now = datetime(2026, 3, 2, 10, 20, 15, tzinfo=timezone(timedelta(hours=8)))
    assert _seconds_until_next_eight_hour_mark(now) == 20385
