"""QA Session schemas."""

from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class QAMessageIn(BaseSchema):
    """Schema for a single Q&A message input."""

    content: str = Field(min_length=1)


class QASessionResponse(BaseSchema, TimestampSchema):
    """Schema for reading a QA session."""

    id: UUID
    resource_id: UUID
    user_id: UUID
    messages: list
