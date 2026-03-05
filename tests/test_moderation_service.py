from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from walle_bot.models import BotSettings, ModerationRules
from walle_bot.services.moderation import ModerationService
from walle_bot.services.state import ModerationState


class FakeBot:
    def __init__(self) -> None:
        self.deleted: list[tuple[int, int]] = []
        self.restricted: list[tuple[int, int]] = []
        self.messages: list[tuple[int, str]] = []
        self.banned: list[tuple[int, int]] = []

    async def delete_message(self, chat_id: int, message_id: int) -> None:
        self.deleted.append((chat_id, message_id))

    async def restrict_chat_member(self, chat_id: int, user_id: int, **kwargs) -> None:
        self.restricted.append((chat_id, user_id))

    async def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))

    async def ban_chat_member(self, chat_id: int, user_id: int) -> None:
        self.banned.append((chat_id, user_id))


def test_mute_happens_on_second_violation(tmp_path: Path) -> None:
    state = ModerationState(tmp_path / "state.db")
    settings = BotSettings(
        bot_token="x",
        monitored_chat_ids=set(),
        whitelist_user_ids=set(),
        rules=ModerationRules(
            duplicate_window_seconds=600,
            duplicate_trigger_count=2,
            mute_duration_seconds=3600,
            mute_on_violations=2,
            max_violations=3,
        ),
        env_file=tmp_path / ".env",
        sqlite_db_path=tmp_path / "state.db",
    )
    service = ModerationService(settings=settings, state=state)
    bot = FakeBot()
    context = SimpleNamespace(bot=bot)
    message = SimpleNamespace(chat_id=-100, message_id=10)

    asyncio.run(
        service._handle_violation(
            message=message,
            context=context,
            user_id=123,
            full_name="tester",
            matched_ids=(),
            reason="duplicate_content",
        )
    )

    assert len(bot.restricted) == 0
    assert len(bot.messages) == 1
    assert "Violation 1/3" in bot.messages[0][1]

    asyncio.run(
        service._handle_violation(
            message=message,
            context=context,
            user_id=123,
            full_name="tester",
            matched_ids=(),
            reason="duplicate_content",
        )
    )

    assert len(bot.restricted) == 1
    assert len(bot.messages) == 2
    assert "Muted for 60 minutes" in bot.messages[1][1]
    state.close()
