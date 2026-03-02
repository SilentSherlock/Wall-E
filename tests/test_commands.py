from walle_bot.handlers.commands import _build_list_text


def test_build_list_text_contains_commands_and_permissions() -> None:
    text = _build_list_text()

    assert "/start" in text
    assert "owner/admin only" in text
    assert "/list" in text
    assert "/whoami" in text
