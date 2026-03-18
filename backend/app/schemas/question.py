"""Question schemas."""

from uuid import UUID

from pydantic import Field

from app.db.models.question import DifficultyLevel
from app.schemas.base import BaseSchema


class QuestionCreate(BaseSchema):
    """Schema for creating a question."""

    question_text: str
    options: list[str] = Field(..., min_length=2, max_length=6)
    correct_answer: str = Field(min_length=1, max_length=1)
    explanation: str | None = None
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    marks: int = Field(default=1, ge=1)
    order_index: int = Field(default=0, ge=0)


class QuestionUpdate(BaseSchema):
    """Schema for updating a question."""

    question_text: str | None = None
    options: list[str] | None = Field(default=None, min_length=2, max_length=6)
    correct_answer: str | None = Field(default=None, min_length=1, max_length=1)
    explanation: str | None = None
    difficulty: DifficultyLevel | None = None
    marks: int | None = Field(default=None, ge=1)
    order_index: int | None = Field(default=None, ge=0)


class QuestionResponse(BaseSchema):
    """Schema for reading a question."""

    id: UUID
    quiz_id: UUID
    question_text: str
    options: list
    correct_answer: str | None  # Hidden if not creator
    explanation: str | None
    difficulty: str
    marks: int
    order_index: int


class BulkQuestionCreate(BaseSchema):
    """Schema for bulk creating questions."""

    questions: list[QuestionCreate]
