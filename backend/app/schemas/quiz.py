"""Quiz schemas."""

from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class QuizCreate(BaseSchema):
    """Schema for creating a quiz."""

    title: str = Field(max_length=200)
    subject: str | None = Field(default=None, max_length=100)
    description: str | None = None
    time_limit_minutes: int | None = Field(default=None, ge=1)


class QuizUpdate(BaseSchema):
    """Schema for updating a quiz."""

    title: str | None = Field(default=None, max_length=200)
    subject: str | None = Field(default=None, max_length=100)
    description: str | None = None
    time_limit_minutes: int | None = Field(default=None, ge=1)
    is_published: bool | None = None


class QuizResponse(BaseSchema, TimestampSchema):
    """Schema for reading a quiz."""

    id: UUID
    title: str
    subject: str | None
    description: str | None
    time_limit_minutes: int | None
    is_published: bool
    is_ai_generated: bool
    created_by: UUID


# Forward import to avoid circular dependency
from app.schemas.question import QuestionResponse


class QuizWithQuestions(QuizResponse):
    """Schema for reading a quiz with questions."""

    questions: list[QuestionResponse] = []


# Rebuild model to resolve forward references
QuizWithQuestions.model_rebuild()
