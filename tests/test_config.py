from pathlib import Path

import pytest

from walle_bot.config import ConfigError, load_settings


def test_load_settings_reads_env_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (tmp_path / ".env.test").write_text(
        "BOT_TOKEN=abc\nMONITORED_CHAT_IDS=1,2\nWHITELIST_USER_IDS=3,4\n",
        encoding="utf-8",
    )

    (config_dir / "settings.yaml").write_text(
        """
        env:
          file: ".env.test"
        moderation:
          duplicate_window_seconds: 10
          mute_duration_seconds: 3600
          max_violations: 3
        """,
        encoding="utf-8",
    )

    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("MONITORED_CHAT_IDS", raising=False)
    monkeypatch.delenv("WHITELIST_USER_IDS", raising=False)

    settings = load_settings(config_dir / "settings.yaml")

    assert settings.bot_token == "abc"
    assert settings.monitored_chat_ids == {1, 2}
    assert settings.whitelist_user_ids == {3, 4}
    assert settings.sqlite_db_path == (tmp_path / "data" / "walle.db").resolve()


def test_load_settings_requires_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (tmp_path / ".env.test").write_text("MONITORED_CHAT_IDS=1\n", encoding="utf-8")

    (config_dir / "settings.yaml").write_text(
        """
        env:
          file: ".env.test"
        moderation: {}
        """,
        encoding="utf-8",
    )

    monkeypatch.delenv("BOT_TOKEN", raising=False)

    with pytest.raises(ConfigError):
        load_settings(config_dir / "settings.yaml")
