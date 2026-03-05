from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .models import BotSettings, ModerationRules


class ConfigError(ValueError):
    """Raised when configuration or environment values are invalid."""


def _parse_int_set(raw_value: str, variable_name: str) -> set[int]:
    if not raw_value.strip():
        return set()

    result: set[int] = set()
    for chunk in raw_value.split(","):
        value = chunk.strip()
        if not value:
            continue
        try:
            result.add(int(value))
        except ValueError as exc:
            raise ConfigError(
                f"Environment variable {variable_name} contains non-integer value: {value}"
            ) from exc
    return result


def _read_yaml(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ConfigError(f"Invalid YAML root in {config_path}")
    return data


def load_settings(config_path: str | Path = "config/settings.yaml") -> BotSettings:
    cfg_path = Path(config_path)
    data = _read_yaml(cfg_path)
    project_root = cfg_path.parent.parent

    env_cfg = data.get("env", {})
    if not isinstance(env_cfg, dict):
        raise ConfigError("env section must be a mapping")

    env_file_name = env_cfg.get("file", ".env")
    env_file = (project_root / env_file_name).resolve()
    load_dotenv(env_file)

    bot_token_key = str(env_cfg.get("bot_token_key", "BOT_TOKEN"))
    monitored_chats_key = str(env_cfg.get("monitored_chat_ids_key", "MONITORED_CHAT_IDS"))
    whitelist_users_key = str(env_cfg.get("whitelist_user_ids_key", "WHITELIST_USER_IDS"))

    bot_token = os.getenv(bot_token_key, "").strip()
    if not bot_token:
        raise ConfigError(f"Environment variable {bot_token_key} is required")

    monitored_chat_ids = _parse_int_set(os.getenv(monitored_chats_key, ""), monitored_chats_key)
    whitelist_user_ids = _parse_int_set(os.getenv(whitelist_users_key, ""), whitelist_users_key)

    moderation_cfg = data.get("moderation", {})
    if not isinstance(moderation_cfg, dict):
        raise ConfigError("moderation section must be a mapping")

    storage_cfg = data.get("storage", {})
    if not isinstance(storage_cfg, dict):
        raise ConfigError("storage section must be a mapping")

    sqlite_db_path = (project_root / str(storage_cfg.get("sqlite_db_path", "data/walle.db"))).resolve()

    rules = ModerationRules(
        duplicate_window_seconds=int(moderation_cfg.get("duplicate_window_seconds", 600)),
        duplicate_trigger_count=int(moderation_cfg.get("duplicate_trigger_count", 2)),
        mute_duration_seconds=int(moderation_cfg.get("mute_duration_seconds", 3600)),
        mute_on_violations=int(moderation_cfg.get("mute_on_violations", 2)),
        max_violations=int(moderation_cfg.get("max_violations", 3)),
    )

    if rules.duplicate_window_seconds <= 0:
        raise ConfigError("duplicate_window_seconds must be > 0")
    if rules.duplicate_trigger_count < 2:
        raise ConfigError("duplicate_trigger_count must be >= 2")
    if rules.mute_duration_seconds <= 0:
        raise ConfigError("mute_duration_seconds must be > 0")
    if rules.mute_on_violations <= 0:
        raise ConfigError("mute_on_violations must be > 0")
    if rules.max_violations <= 0:
        raise ConfigError("max_violations must be > 0")
    if rules.max_violations < rules.mute_on_violations:
        raise ConfigError("max_violations must be >= mute_on_violations")

    return BotSettings(
        bot_token=bot_token,
        monitored_chat_ids=monitored_chat_ids,
        whitelist_user_ids=whitelist_user_ids,
        rules=rules,
        env_file=env_file,
        sqlite_db_path=sqlite_db_path,
    )
