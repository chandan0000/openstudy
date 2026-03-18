"""Note schemas."""

from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class NoteCreate(BaseSchema):
    """Schema for creating a note."""

    content: str
    tags: list[str] = Field(default_factory=list)


class NoteUpdate(BaseSchema):
    """Schema for updating a note."""

    content: str | None = None
    tags: list[str] | None = None


class NoteResponse(BaseSchema, TimestampSchema):
    """Schema for reading a note."""

    id: UUID
    content: str
    tags: list
    resource_id: UUID
    user_id: UUID
