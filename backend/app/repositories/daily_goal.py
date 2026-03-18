"""Daily Goal repository (PostgreSQL async)."""

from uuid import UUID
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.daily_goal import DailyGoal


async def get_by_user_and_date(
    db: AsyncSession, user_id: UUID, target_date: date | None = None
) -> DailyGoal | None:
    """Get daily goal by user ID and date."""
    if target_date is None:
        target_date = date.today()

    result = await db.execute(
        select(DailyGoal).where(
            DailyGoal.user_id == user_id,
            DailyGoal.date == target_date,
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    user_id: UUID,
    target_minutes: int,
    target_date: date | None = None,
) -> DailyGoal:
    """Create a new daily goal."""
    if target_date is None:
        target_date = date.today()

    daily_goal = DailyGoal(
        user_id=user_id,
        target_minutes=target_minutes,
        date=target_date,
        achieved=False,
    )
    db.add(daily_goal)
    await db.flush()
    await db.refresh(daily_goal)
    return daily_goal


async def update_achieved(
    db: AsyncSession,
    *,
    db_daily_goal: DailyGoal,
    achieved: bool,
) -> DailyGoal:
    """Update daily goal achieved status."""
    db_daily_goal.achieved = achieved

    db.add(db_daily_goal)
    await db.flush()
    await db.refresh(db_daily_goal)
    return db_daily_goal
