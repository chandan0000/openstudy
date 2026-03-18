"""Leaderboard schemas."""

from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class LeaderboardUserInfo(BaseSchema):
    """Schema for user info in leaderboard."""

    id: UUID
    full_name: str | None


class LeaderboardEntryResponse(BaseSchema):
    """Schema for reading a leaderboard entry."""

    id: UUID
    quiz_id: UUID
    user: LeaderboardUserInfo
    rank: int | None
    best_score: int
    best_time: int | None
    attempt_count: int


class LeaderboardResponse(BaseSchema):
    """Schema for reading a quiz leaderboard."""

    quiz_id: UUID
    quiz_title: str
    entries: list[LeaderboardEntryResponse]
