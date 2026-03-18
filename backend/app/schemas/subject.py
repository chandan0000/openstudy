"""Subject schemas."""

from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class SubjectCreate(BaseSchema):
    """Schema for creating a subject."""

    name: str = Field(max_length=100)
    description: str | None = None
    color: str | None = Field(default=None, max_length=7)  # hex color like "#5DCAA5"


class SubjectUpdate(BaseSchema):
    """Schema for updating a subject."""

    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    color: str | None = Field(default=None, max_length=7)


class SubjectResponse(BaseSchema, TimestampSchema):
    """Schema for reading a subject."""

    id: UUID
    name: str
    description: str | None
    color: str | None
    user_id: UUID
