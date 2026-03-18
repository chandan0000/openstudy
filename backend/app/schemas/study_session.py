"""Study Session schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class StudySessionCreate(BaseSchema):
    """Schema for creating a study session."""

    room_id: UUID | None = None
    session_type: str = "pomodoro"  # "pomodoro" | "free"


class StudySessionEnd(BaseSchema):
    """Schema for ending a study session."""

    pomodoro_count: int = Field(default=0, ge=0)


class StudySessionResponse(BaseSchema, TimestampSchema):
    """Schema for reading a study session."""

    id: UUID
    user_id: UUID
    room_id: UUID | None
    started_at: datetime
    ended_at: datetime | None
    duration_minutes: int | None
    session_type: str
    pomodoro_count: int


class StudyStatsResponse(BaseSchema):
    """Schema for study statistics."""

    today_minutes: int
    week_minutes: int
    total_pomodoros: int
    total_sessions: int
