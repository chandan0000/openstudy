"""Attempt repository (PostgreSQL async)."""

from uuid import UUID
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.attempt import Attempt


async def get_by_user_and_quiz(
    db: AsyncSession, user_id: UUID, quiz_id: UUID
) -> list[Attempt]:
    """Get attempts by user ID and quiz ID."""
    result = await db.execute(
        select(Attempt).where(
            Attempt.user_id == user_id,
            Attempt.quiz_id == quiz_id,
        )
    )
    return list(result.scalars().all())


async def get_incomplete_attempt(
    db: AsyncSession, user_id: UUID, quiz_id: UUID
) -> Attempt | None:
    """Get incomplete attempt by user ID and quiz ID."""
    result = await db.execute(
        select(Attempt).where(
            Attempt.user_id == user_id,
            Attempt.quiz_id == quiz_id,
            Attempt.is_completed == False,
        )
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, attempt_id: UUID) -> Attempt | None:
    """Get attempt by ID."""
    return await db.get(Attempt, attempt_id)


async def create(
    db: AsyncSession,
    *,
    user_id: UUID,
    quiz_id: UUID,
) -> Attempt:
    """Create a new attempt."""
    attempt = Attempt(
        user_id=user_id,
        quiz_id=quiz_id,
        answers={},
        is_completed=False,
    )
    db.add(attempt)
    await db.flush()
    await db.refresh(attempt)
    return attempt


async def update(
    db: AsyncSession,
    *,
    db_attempt: Attempt,
    update_data: dict,
) -> Attempt:
    """Update an attempt."""
    for field, value in update_data.items():
        setattr(db_attempt, field, value)

    db.add(db_attempt)
    await db.flush()
    await db.refresh(db_attempt)
    return db_attempt


async def complete_attempt(
    db: AsyncSession,
    *,
    db_attempt: Attempt,
    score: int,
    total_marks: int,
    time_taken_seconds: int,
) -> Attempt:
    """Mark attempt as completed with score."""
    db_attempt.score = score
    db_attempt.total_marks = total_marks
    db_attempt.time_taken_seconds = time_taken_seconds
    db_attempt.is_completed = True
    db_attempt.completed_at = datetime.utcnow()

    db.add(db_attempt)
    await db.flush()
    await db.refresh(db_attempt)
    return db_attempt
