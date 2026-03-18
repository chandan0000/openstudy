"""Daily Goal service (PostgreSQL async)."""

from uuid import UUID
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.daily_goal import DailyGoal
from app.repositories import daily_goal_repo, study_session_repo


class GoalService:
    """Service for daily goal-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def set_daily_goal(self, user_id: UUID, target_minutes: int) -> DailyGoal:
        """Set or update daily goal for today."""
        existing = await daily_goal_repo.get_by_user_and_date(self.db, user_id)

        if existing:
            # Update existing
            return await daily_goal_repo.update_achieved(
                self.db,
                db_daily_goal=existing,
                achieved=existing.achieved,  # Keep same achieved status
            )

        return await daily_goal_repo.create(
            self.db,
            user_id=user_id,
            target_minutes=target_minutes,
        )

    async def check_and_update_goal(self, user_id: UUID) -> DailyGoal | None:
        """Check if daily goal is achieved and update."""
        goal = await daily_goal_repo.get_by_user_and_date(self.db, user_id)
        if not goal:
            return None

        # Get today's study minutes
        achieved_minutes = await study_session_repo.get_today_total_minutes(self.db, user_id)

        # Update achieved status
        is_achieved = achieved_minutes >= goal.target_minutes
        if is_achieved != goal.achieved:
            return await daily_goal_repo.update_achieved(
                self.db,
                db_daily_goal=goal,
                achieved=is_achieved,
            )

        return goal

    async def get_today_progress(self, user_id: UUID) -> dict:
        """Get today's goal progress."""
        goal = await daily_goal_repo.get_by_user_and_date(self.db, user_id)

        if not goal:
            return {
                "target_minutes": 0,
                "achieved_minutes": 0,
                "percentage": 0,
                "achieved": False,
            }

        achieved_minutes = await study_session_repo.get_today_total_minutes(self.db, user_id)
        percentage = min(100, int((achieved_minutes / goal.target_minutes) * 100))

        return {
            "target_minutes": goal.target_minutes,
            "achieved_minutes": achieved_minutes,
            "percentage": percentage,
            "achieved": goal.achieved,
        }

    async def get_today_goal(self, user_id: UUID) -> DailyGoal | None:
        """Get today's goal for a user."""
        return await daily_goal_repo.get_by_user_and_date(self.db, user_id)
