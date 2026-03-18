"""Room schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class RoomMemberResponse(BaseSchema):
    """Schema for reading a room member."""

    user_id: UUID
    full_name: str | None
    role: str
    joined_at: datetime | None


class RoomCreate(BaseSchema):
    """Schema for creating a room."""

    name: str = Field(max_length=100)
    subject: str | None = Field(default=None, max_length=100)
    is_public: bool = True
    max_members: int = Field(default=10, ge=2, le=100)


class RoomResponse(BaseSchema, TimestampSchema):
    """Schema for reading a room (list view)."""

    id: UUID
    name: str
    subject: str | None
    owner_id: UUID
    is_public: bool
    max_members: int
    invite_code: str | None
    is_active: bool
    member_count: int = 0


class RoomDetailResponse(RoomResponse):
    """Schema for reading a room (detail view with members)."""

    members: list[RoomMemberResponse] = []
