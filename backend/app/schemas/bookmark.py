"""Bookmark schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class BookmarkCreate(BaseSchema):
    """Schema for creating a bookmark."""

    resource_id: UUID


class BookmarkResponse(BaseSchema):
    """Schema for reading a bookmark."""

    id: UUID
    user_id: UUID
    resource_id: UUID
    created_at: datetime
