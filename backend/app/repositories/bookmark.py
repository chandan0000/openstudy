"""Bookmark repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.bookmark import Bookmark


async def get_by_user(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
) -> list[Bookmark]:
    """Get bookmarks by user ID."""
    result = await db.execute(
        select(Bookmark)
        .where(Bookmark.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_user_and_resource(
    db: AsyncSession, user_id: UUID, resource_id: UUID
) -> Bookmark | None:
    """Get bookmark by user ID and resource ID."""
    result = await db.execute(
        select(Bookmark).where(
            Bookmark.user_id == user_id,
            Bookmark.resource_id == resource_id,
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    user_id: UUID,
    resource_id: UUID,
) -> Bookmark:
    """Create a new bookmark."""
    bookmark = Bookmark(
        user_id=user_id,
        resource_id=resource_id,
    )
    db.add(bookmark)
    await db.flush()
    await db.refresh(bookmark)
    return bookmark


async def delete(db: AsyncSession, bookmark_id: UUID) -> Bookmark | None:
    """Delete a bookmark."""
    bookmark = await db.get(Bookmark, bookmark_id)
    if bookmark:
        await db.delete(bookmark)
        await db.flush()
    return bookmark
