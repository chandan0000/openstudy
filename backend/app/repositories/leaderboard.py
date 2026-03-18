"""Leaderboard repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.leaderboard import Leaderboard


async def get_by_quiz(
    db: AsyncSession, quiz_id: UUID, limit: int = 100
) -> list[Leaderboard]:
    """Get leaderboard entries by quiz ID ordered by rank."""
    result = await db.execute(
        select(Leaderboard)
        .where(Leaderboard.quiz_id == quiz_id)
        .order_by(Leaderboard.rank)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_user_and_quiz(
    db: AsyncSession, user_id: UUID, quiz_id: UUID
) -> Leaderboard | None:
    """Get leaderboard entry by user ID and quiz ID."""
    result = await db.execute(
        select(Leaderboard).where(
            Leaderboard.user_id == user_id,
            Leaderboard.quiz_id == quiz_id,
        )
    )
    return result.scalar_one_or_none()


async def upsert(
    db: AsyncSession,
    *,
    quiz_id: UUID,
    user_id: UUID,
    score: int,
    time_seconds: int,
) -> Leaderboard:
    """Upsert leaderboard entry (update if exists and better, else create)."""
    entry = await get_by_user_and_quiz(db, user_id, quiz_id)

    if entry:
        # Update only if new score is better, or same score but faster time
        if score > entry.best_score or (score == entry.best_score and (entry.best_time is None or time_seconds < entry.best_time)):
            entry.best_score = score
            entry.best_time = time_seconds
        entry.attempt_count += 1
    else:
        entry = Leaderboard(
            quiz_id=quiz_id,
            user_id=user_id,
            best_score=score,
            best_time=time_seconds,
            attempt_count=1,
        )
        db.add(entry)

    await db.flush()
    await db.refresh(entry)
    return entry


async def update_ranks(db: AsyncSession, quiz_id: UUID) -> None:
    """Recalculate and update ranks for a quiz leaderboard."""
    # Get all entries ordered by score desc, time asc
    result = await db.execute(
        select(Leaderboard)
        .where(Leaderboard.quiz_id == quiz_id)
        .order_by(Leaderboard.best_score.desc(), Leaderboard.best_time.asc())
    )
    entries = result.scalars().all()

    # Update ranks
    for rank, entry in enumerate(entries, start=1):
        entry.rank = rank
        db.add(entry)

    await db.flush()
