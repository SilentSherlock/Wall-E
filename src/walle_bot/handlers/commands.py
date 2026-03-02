from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return

    username = f"@{user.username}" if user.username else "(none)"
    text = (
        "User info\n"
        f"ID: {user.id}\n"
        f"Name: {user.full_name}\n"
        f"Username: {username}\n"
        f"Chat ID: {chat.id}"
    )
    await update.effective_message.reply_text(text)
