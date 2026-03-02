from __future__ import annotations

from datetime import datetime, timezone
import logging

from telegram.error import BadRequest, Forbidden
from telegram.ext import Application, ContextTypes

from .moderation import ModerationService

logger = logging.getLogger(__name__)


def _build_time_message(now: datetime) -> str:
    return f"Hourly report: current UTC time is {now.strftime('%Y-%m-%d %H:%M:%S')}."


def _build_startup_message(now: datetime) -> str:
    return f"Wall-E机器人已重启，当前时间：{now.strftime('%Y-%m-%d %H:%M:%S UTC')}"


async def hourly_time_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    service: ModerationService = context.application.bot_data["moderation_service"]
    managed_chat_ids = service.state.get_managed_chat_ids()
    if not managed_chat_ids:
        logger.debug("No managed chats registered, skip hourly report.")
        return

    text = _build_time_message(datetime.now(tz=timezone.utc))
    for chat_id in managed_chat_ids:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except (BadRequest, Forbidden):
            logger.warning("Failed to send hourly report to chat %s", chat_id)


async def send_startup_notice(application: Application) -> None:
    service: ModerationService = application.bot_data["moderation_service"]
    managed_chat_ids = service.state.get_managed_chat_ids()
    if not managed_chat_ids:
        logger.debug("No managed chats registered, skip startup notice.")
        return

    text = _build_startup_message(datetime.now(tz=timezone.utc))
    for chat_id in managed_chat_ids:
        try:
            await application.bot.send_message(chat_id=chat_id, text=text)
        except (BadRequest, Forbidden):
            logger.warning("Failed to send startup notice to chat %s", chat_id)


def register_hourly_job(application: Application) -> None:
    if application.job_queue is None:
        logger.warning("Job queue unavailable. Install job-queue dependencies to enable reports.")
        return
    application.job_queue.run_repeating(
        hourly_time_report,
        interval=3600,
        first=5,
        name="hourly_time_report",
    )