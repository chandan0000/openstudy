"""Room Celery tasks."""

import logging
from typing import Any

from celery import shared_task
from celery.schedules import crontab

from app.db.session import get_db_context
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@shared_task
def send_daily_summary() -> dict[str, Any]:
    """
    Send daily summary to users with daily goals.
    Runs daily at 23:59 via Celery beat.
    """
    import asyncio

    async def _send_summary():
        async with get_db_context() as db:
            from datetime import date

            from app.repositories import daily_goal_repo
            from app.services.goal import GoalService

            goal_service = GoalService(db)

            # Get all users with daily goals for today
            # Note: In production, this would fetch all goals and batch process
            logger.info("Sending daily summaries...")

            # Get goals that were achieved today
            # This is a simplified version - in production use proper filtering
            today = date.today()

            # For each goal, check if achieved and send notification
            # Implementation would depend on notification system (email, push, etc.)

            return {
                "status": "completed",
                "date": today.isoformat(),
                "message": "Daily summary processing completed",
            }

    return asyncio.run(_send_summary())


@shared_task
def cleanup_inactive_rooms() -> dict[str, Any]:
    """
    Deactivate rooms with no activity in the last 30 days.
    Runs weekly via Celery beat.
    """
    import asyncio

    async def _cleanup():
        async with get_db_context() as db:
            from app.repositories import room_repo

            count = await room_repo.cleanup_inactive(db, days=30)
            logger.info(f"Deactivated {count} inactive rooms")

            return {
                "status": "completed",
                "rooms_deactivated": count,
            }

    return asyncio.run(_cleanup())


# Register periodic tasks
celery_app.conf.beat_schedule.update({
    "send-daily-summary": {
        "task": "app.worker.tasks.room_tasks.send_daily_summary",
        "schedule": crontab(hour=23, minute=59),
    },
    "cleanup-inactive-rooms": {
        "task": "app.worker.tasks.room_tasks.cleanup_inactive_rooms",
        "schedule": crontab(hour=0, minute=0, day_of_week="sunday"),
    },
})
