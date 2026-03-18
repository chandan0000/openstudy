"""Subject repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.subject import Subject


async def get_by_user(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
) -> list[Subject]:
    """Get subjects by user ID."""
    result = await db.execute(
        select(Subject)
        .where(Subject.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, subject_id: UUID) -> Subject | None:
    """Get subject by ID."""
    return await db.get(Subject, subject_id)


async def create(
    db: AsyncSession,
    *,
    name: str,
    description: str | None,
    color: str | None,
    user_id: UUID,
) -> Subject:
    """Create a new subject."""
    subject = Subject(
        name=name,
        description=description,
        color=color,
        user_id=user_id,
    )
    db.add(subject)
    await db.flush()
    await db.refresh(subject)
    return subject


async def update(
    db: AsyncSession,
    *,
    db_subject: Subject,
    update_data: dict,
) -> Subject:
    """Update a subject."""
    for field, value in update_data.items():
        setattr(db_subject, field, value)

    db.add(db_subject)
    await db.flush()
    await db.refresh(db_subject)
    return db_subject


async def delete(db: AsyncSession, subject_id: UUID) -> Subject | None:
    """Delete a subject."""
    subject = await get_by_id(db, subject_id)
    if subject:
        await db.delete(subject)
        await db.flush()
    return subject
