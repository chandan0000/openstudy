"""Bookmark service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.db.models.bookmark import Bookmark
from app.repositories import bookmark_repo


class BookmarkService:
    """Service for bookmark-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_bookmark(self, user_id: UUID, resource_id: UUID) -> Bookmark:
        """Add a bookmark. Raises AlreadyExistsError if duplicate."""
        # Check if bookmark already exists
        existing = await bookmark_repo.get_by_user_and_resource(
            self.db, user_id, resource_id
        )
        if existing:
            raise AlreadyExistsError(
                message="Bookmark already exists",
                details={"resource_id": str(resource_id)},
            )

        return await bookmark_repo.create(
            self.db,
            user_id=user_id,
            resource_id=resource_id,
        )

    async def remove_bookmark(self, user_id: UUID, bookmark_id: UUID) -> Bookmark:
        """Remove a bookmark."""
        bookmark = await bookmark_repo.get_by_user_and_resource(
            self.db, user_id, bookmark_id
        )
        if not bookmark:
            raise NotFoundError(
                message="Bookmark not found",
                details={"bookmark_id": str(bookmark_id)},
            )

        return await bookmark_repo.delete(self.db, bookmark.id)

    async def get_user_bookmarks(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Bookmark]:
        """Get bookmarks for a user."""
        return await bookmark_repo.get_by_user(self.db, user_id, skip=skip, limit=limit)

    async def remove_bookmark_by_resource(
        self, user_id: UUID, resource_id: UUID
    ) -> Bookmark | None:
        """Remove a bookmark by resource ID."""
        bookmark = await bookmark_repo.get_by_user_and_resource(
            self.db, user_id, resource_id
        )
        if not bookmark:
            return None

        return await bookmark_repo.delete(self.db, bookmark.id)
