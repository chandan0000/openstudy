"""Attempt schemas."""

from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class AttemptStart(BaseSchema):
    """Schema for starting an attempt."""

    quiz_id: UUID


class AttemptUpdate(BaseSchema):
    """Schema for updating attempt progress (auto-save)."""

    answers: dict[str, str] = Field(default_factory=dict)  # {question_id: "A"}


class AttemptSubmit(BaseSchema):
    """Schema for submitting an attempt."""

    answers: dict[str, str] = Field(default_factory=dict)
    time_taken_seconds: int | None = Field(default=None, ge=1)


class QuestionResult(BaseSchema):
    """Schema for question result in attempt response."""

    question_id: UUID
    user_answer: str | None
    correct_answer: str
    is_correct: bool
    marks: int
    earned_marks: int


class AttemptResponse(BaseSchema):
    """Schema for reading an attempt."""

    id: UUID
    user_id: UUID
    quiz_id: UUID
    score: int | None
    total_marks: int | None
    time_taken_seconds: int | None
    answers: dict
    is_completed: bool
    questions: list[QuestionResult] = []
    leaderboard_rank: int | None = None
