"""Daily Goal schemas."""

from datetime import date
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class DailyGoalCreate(BaseSchema):
    """Schema for creating a daily goal."""

    target_minutes: int = Field(ge=1, le=1440)


class DailyGoalResponse(BaseSchema, TimestampSchema):
    """Schema for reading a daily goal."""

    id: UUID
    user_id: UUID
    target_minutes: int
    date: date
    achieved: bool


class DailyGoalProgressResponse(BaseSchema):
    """Schema for daily goal progress."""

    target_minutes: int
    achieved_minutes: int
    percentage: int  # 0-100
    achieved: bool
