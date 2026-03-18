"""Note repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.note import Note


async def get_by_resource(
    db: AsyncSession, resource_id: UUID, skip: int = 0, limit: int = 100
) -> list[Note]:
    """Get notes by resource ID."""
    result = await db.execute(
        select(Note)
        .where(Note.resource_id == resource_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_user(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
) -> list[Note]:
    """Get notes by user ID."""
    result = await db.execute(
        select(Note)
        .where(Note.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_tag(
    db: AsyncSession, user_id: UUID, tag: str, skip: int = 0, limit: int = 100
) -> list[Note]:
    """Get notes by tag (JSON contains)."""
    result = await db.execute(
        select(Note)
        .where(
            Note.user_id == user_id,
            Note.tags.contains([tag]),  # type: ignore
        )
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, note_id: UUID) -> Note | None:
    """Get note by ID."""
    return await db.get(Note, note_id)


async def create(
    db: AsyncSession,
    *,
    content: str,
    tags: list[str],
    resource_id: UUID,
    user_id: UUID,
) -> Note:
    """Create a new note."""
    note = Note(
        content=content,
        tags=tags or [],
        resource_id=resource_id,
        user_id=user_id,
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note


async def update(
    db: AsyncSession,
    *,
    db_note: Note,
    update_data: dict,
) -> Note:
    """Update a note."""
    for field, value in update_data.items():
        setattr(db_note, field, value)

    db.add(db_note)
    await db.flush()
    await db.refresh(db_note)
    return db_note


async def delete(db: AsyncSession, note_id: UUID) -> Note | None:
    """Delete a note."""
    note = await get_by_id(db, note_id)
    if note:
        await db.delete(note)
        await db.flush()
    return note
