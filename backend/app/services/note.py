"""Note service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.note import Note
from app.repositories import note_repo
from app.schemas.note import NoteCreate, NoteUpdate


class NoteService:
    """Service for note-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_note(
        self, user_id: UUID, resource_id: UUID, note_in: NoteCreate
    ) -> Note:
        """Create a new note."""
        return await note_repo.create(
            self.db,
            content=note_in.content,
            tags=note_in.tags,
            resource_id=resource_id,
            user_id=user_id,
        )

    async def get_resource_notes(
        self, resource_id: UUID, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Note]:
        """Get notes for a resource."""
        return await note_repo.get_by_resource(self.db, resource_id, skip=skip, limit=limit)

    async def get_note_by_id(self, note_id: UUID, user_id: UUID) -> Note:
        """Get a note by ID.

        Raises:
            NotFoundError: If note does not exist or user doesn't have access.
        """
        note = await note_repo.get_by_id(self.db, note_id)
        if not note or note.user_id != user_id:
            raise NotFoundError(
                message="Note not found",
                details={"note_id": str(note_id)},
            )
        return note

    async def update_note(
        self, note_id: UUID, user_id: UUID, note_in: NoteUpdate
    ) -> Note:
        """Update a note."""
        note = await self.get_note_by_id(note_id, user_id)

        update_data = note_in.model_dump(exclude_unset=True)
        return await note_repo.update(
            self.db,
            db_note=note,
            update_data=update_data,
        )

    async def delete_note(self, note_id: UUID, user_id: UUID) -> Note:
        """Delete a note."""
        note = await self.get_note_by_id(note_id, user_id)
        return await note_repo.delete(self.db, note_id)

    async def search_by_tag(
        self, user_id: UUID, tag: str, skip: int = 0, limit: int = 100
    ) -> list[Note]:
        """Search notes by tag."""
        return await note_repo.get_by_tag(self.db, user_id, tag, skip=skip, limit=limit)
