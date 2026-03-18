"""Daily Goal routes (Study Room / Pomodoro)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user
from app.db.models.user import User
from app.services.goal import GoalService
from app.schemas.daily_goal import (
    DailyGoalCreate,
    DailyGoalProgressResponse,
    DailyGoalResponse,
)

router = APIRouter()


def get_goal_service(db: DBSession) -> GoalService:
    """Dependency for GoalService."""
    return GoalService(db)


GoalSvc = Annotated[GoalService, Depends(get_goal_service)]


@router.post("", response_model=DailyGoalResponse, status_code=status.HTTP_201_CREATED)
async def set_daily_goal(
    goal_in: DailyGoalCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: GoalSvc,
):
    """Set daily goal."""
    goal = await goal_service.set_daily_goal(current_user.id, goal_in.target_minutes)
    return goal


@router.get("/me/today", response_model=DailyGoalProgressResponse)
async def get_today_progress(
    current_user: Annotated[User, Depends(get_current_user)],
    goal_service: GoalSvc,
):
    """Get today's goal progress."""
    progress = await goal_service.get_today_progress(current_user.id)
    return DailyGoalProgressResponse(**progress)
