"""Quiz repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.quiz import Quiz


async def get_by_id(db: AsyncSession, quiz_id: UUID) -> Quiz | None:
    """Get quiz by ID."""
    return await db.get(Quiz, quiz_id)


async def get_published(
    db: AsyncSession,
    subject: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Quiz]:
    """Get published quizzes with optional subject filter."""
    query = select(Quiz).where(Quiz.is_published == True)

    if subject:
        query = query.where(Quiz.subject == subject)

    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_by_creator(
    db: AsyncSession, created_by: UUID, skip: int = 0, limit: int = 100
) -> list[Quiz]:
    """Get quizzes by creator ID."""
    result = await db.execute(
        select(Quiz)
        .where(Quiz.created_by == created_by)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    title: str,
    subject: str | None,
    description: str | None,
    time_limit_minutes: int | None,
    created_by: UUID,
) -> Quiz:
    """Create a new quiz."""
    quiz = Quiz(
        title=title,
        subject=subject,
        description=description,
        time_limit_minutes=time_limit_minutes,
        created_by=created_by,
        is_published=False,
        is_ai_generated=False,
    )
    db.add(quiz)
    await db.flush()
    await db.refresh(quiz)
    return quiz


async def update(
    db: AsyncSession,
    *,
    db_quiz: Quiz,
    update_data: dict,
) -> Quiz:
    """Update a quiz."""
    for field, value in update_data.items():
        setattr(db_quiz, field, value)

    db.add(db_quiz)
    await db.flush()
    await db.refresh(db_quiz)
    return db_quiz


async def delete(db: AsyncSession, quiz_id: UUID) -> Quiz | None:
    """Delete a quiz."""
    quiz = await get_by_id(db, quiz_id)
    if quiz:
        await db.delete(quiz)
        await db.flush()
    return quiz
