from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModerationRules:
    duplicate_window_seconds: int
    mute_duration_seconds: int
    max_violations: int


@dataclass(frozen=True)
class BotSettings:
    bot_token: str
    monitored_chat_ids: set[int]
    whitelist_user_ids: set[int]
    rules: ModerationRules
    env_file: Path
