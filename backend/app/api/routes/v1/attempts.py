"""Attempt routes (Quiz Engine)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, Redis, get_current_user
from app.clients.redis import RedisClient
from app.db.models.user import User
from app.services.attempt import AttemptService
from app.schemas.attempt import (
    AttemptResponse,
    AttemptStart,
    AttemptSubmit,
    AttemptUpdate,
    QuestionResult,
)

router = APIRouter()


def get_attempt_service(
    db: DBSession, redis: Redis = None
) -> AttemptService:
    """Dependency for AttemptService."""
    return AttemptService(db, redis)


AttemptSvc = Annotated[AttemptService, Depends(get_attempt_service)]


@router.post("", response_model=AttemptResponse, status_code=status.HTTP_201_CREATED)
async def start_attempt(
    attempt_in: AttemptStart,
    current_user: Annotated[User, Depends(get_current_user)],
    attempt_service: AttemptSvc,
):
    """Start a new quiz attempt."""
    attempt = await attempt_service.start_attempt(
        current_user.id, attempt_in.quiz_id
    )
    return AttemptResponse(
        id=attempt.id,
        user_id=attempt.user_id,
        quiz_id=attempt.quiz_id,
        score=attempt.score,
        total_marks=attempt.total_marks,
        time_taken_seconds=attempt.time_taken_seconds,
        answers=attempt.answers,
        is_completed=attempt.is_completed,
        questions=[],
        leaderboard_rank=None,
    )


@router.patch("/{attempt_id}", response_model=AttemptResponse)
async def save_progress(
    attempt_id: UUID,
    progress: AttemptUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    attempt_service: AttemptSvc,
):
    """Save attempt progress (auto-save partial answers)."""
    attempt = await attempt_service.save_progress(
        attempt_id, current_user.id, progress
    )
    return AttemptResponse(
        id=attempt.id,
        user_id=attempt.user_id,
        quiz_id=attempt.quiz_id,
        score=attempt.score,
        total_marks=attempt.total_marks,
        time_taken_seconds=attempt.time_taken_seconds,
        answers=attempt.answers,
        is_completed=attempt.is_completed,
        questions=[],
        leaderboard_rank=None,
    )


@router.post("/{attempt_id}/submit", response_model=AttemptResponse)
async def submit_attempt(
    attempt_id: UUID,
    submit_data: AttemptSubmit,
    current_user: Annotated[User, Depends(get_current_user)],
    attempt_service: AttemptSvc,
):
    """Submit an attempt and get results."""
    attempt, question_results, rank = await attempt_service.submit_attempt(
        attempt_id, current_user.id, submit_data
    )
    return AttemptResponse(
        id=attempt.id,
        user_id=attempt.user_id,
        quiz_id=attempt.quiz_id,
        score=attempt.score,
        total_marks=attempt.total_marks,
        time_taken_seconds=attempt.time_taken_seconds,
        answers=attempt.answers,
        is_completed=attempt.is_completed,
        questions=question_results,
        leaderboard_rank=rank,
    )


@router.get("/{attempt_id}", response_model=AttemptResponse)
async def get_attempt_result(
    attempt_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    attempt_service: AttemptSvc,
):
    """Get attempt result with correct answers."""
    attempt, question_results = await attempt_service.get_attempt_result(
        attempt_id, current_user.id
    )
    return AttemptResponse(
        id=attempt.id,
        user_id=attempt.user_id,
        quiz_id=attempt.quiz_id,
        score=attempt.score,
        total_marks=attempt.total_marks,
        time_taken_seconds=attempt.time_taken_seconds,
        answers=attempt.answers,
        is_completed=attempt.is_completed,
        questions=question_results,
        leaderboard_rank=None,
    )
