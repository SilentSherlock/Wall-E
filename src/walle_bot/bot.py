from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from .config import load_settings
from .handlers.commands import list_commands, release, start, whoami
from .logging_setup import configure_logging
from .services.moderation import ModerationService
from .services.scheduler import register_hourly_job, send_startup_notice
from .services.state import ModerationState

logger = logging.getLogger(__name__)


async def _moderation_entry(update, context) -> None:
    service: ModerationService = context.application.bot_data["moderation_service"]
    await service.process_message(update, context)


async def _on_shutdown(application: Application) -> None:
    service: ModerationService = application.bot_data["moderation_service"]
    service.state.close()


async def _on_startup(application: Application) -> None:
    await send_startup_notice(application)


def create_application(config_path: str = "config/settings.yaml") -> Application:
    settings = load_settings(config_path)
    state = ModerationState(db_path=settings.sqlite_db_path)

    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(_on_startup)
        .post_shutdown(_on_shutdown)
        .build()
    )
    application.bot_data["moderation_service"] = ModerationService(settings=settings, state=state)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("release", release))
    application.add_handler(CommandHandler("list", list_commands))
    application.add_handler(CommandHandler("whoami", whoami))
    application.add_handler(
        MessageHandler(
            (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
            _moderation_entry,
        )
    )

    logger.info(
        "Bot initialized with monitored chats=%s and whitelist count=%s",
        sorted(settings.monitored_chat_ids),
        len(settings.whitelist_user_ids),
    )
    register_hourly_job(application)
    return application


def run(config_path: str = "config/settings.yaml") -> None:
    configure_logging()
    application = create_application(config_path)
    application.run_polling(allowed_updates=["message"])
