"""Subject service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.subject import Subject
from app.repositories import subject_repo
from app.schemas.subject import SubjectCreate, SubjectUpdate


class SubjectService:
    """Service for subject-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subject(self, user_id: UUID, subject_in: SubjectCreate) -> Subject:
        """Create a new subject."""
        return await subject_repo.create(
            self.db,
            name=subject_in.name,
            description=subject_in.description,
            color=subject_in.color,
            user_id=user_id,
        )

    async def get_user_subjects(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Subject]:
        """Get subjects for a user."""
        return await subject_repo.get_by_user(self.db, user_id, skip=skip, limit=limit)

    async def get_subject_by_id(self, subject_id: UUID) -> Subject:
        """Get a subject by ID.

        Raises:
            NotFoundError: If subject does not exist.
        """
        subject = await subject_repo.get_by_id(self.db, subject_id)
        if not subject:
            raise NotFoundError(
                message="Subject not found",
                details={"subject_id": str(subject_id)},
            )
        return subject

    async def update_subject(
        self, subject_id: UUID, user_id: UUID, subject_in: SubjectUpdate
    ) -> Subject:
        """Update a subject."""
        subject = await self.get_subject_by_id(subject_id)

        # Verify ownership
        if subject.user_id != user_id:
            raise NotFoundError(
                message="Subject not found",
                details={"subject_id": str(subject_id)},
            )

        update_data = subject_in.model_dump(exclude_unset=True)
        return await subject_repo.update(
            self.db,
            db_subject=subject,
            update_data=update_data,
        )

    async def delete_subject(self, subject_id: UUID, user_id: UUID) -> Subject:
        """Delete a subject."""
        subject = await self.get_subject_by_id(subject_id)

        # Verify ownership
        if subject.user_id != user_id:
            raise NotFoundError(
                message="Subject not found",
                details={"subject_id": str(subject_id)},
            )

        return await subject_repo.delete(self.db, subject_id)
