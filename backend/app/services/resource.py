"""Resource service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.redis import RedisClient
from app.core.exceptions import NotFoundError
from app.db.models.resource import Resource, SummaryStatus
from app.repositories import resource_repo
from app.schemas.resource import ResourceCreate
from app.worker.celery_app import celery_app


class ResourceService:
    """Service for resource-related business logic."""

    def __init__(self, db: AsyncSession, redis: RedisClient | None = None):
        self.db = db
        self.redis = redis

    async def create_resource(
        self,
        user_id: UUID,
        resource_in: ResourceCreate,
        file_path: str | None = None,
        file_size_bytes: int | None = None,
    ) -> Resource:
        """Create a new resource and trigger summarization."""
        resource = await resource_repo.create(
            self.db,
            title=resource_in.title,
            type=resource_in.type,
            file_path=file_path,
            url=resource_in.url,
            content=None,
            subject_id=resource_in.subject_id,
            user_id=user_id,
            file_size_bytes=file_size_bytes,
        )

        # Trigger Celery task for summarization
        celery_app.send_task(
            "app.worker.tasks.resource_tasks.process_resource",
            args=[str(resource.id)],
        )

        return resource

    async def get_user_resources(
        self,
        user_id: UUID,
        subject_id: UUID | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Resource]:
        """Get resources for a user with optional filters."""
        if search:
            return await resource_repo.search(self.db, user_id, search, skip=skip, limit=limit)
        elif subject_id:
            return await resource_repo.get_by_subject(self.db, subject_id, skip=skip, limit=limit)
        else:
            return await resource_repo.get_by_user(self.db, user_id, skip=skip, limit=limit)

    async def get_resource_by_id(self, resource_id: UUID, user_id: UUID) -> Resource:
        """Get a resource by ID.

        Raises:
            NotFoundError: If resource does not exist or user doesn't have access.
        """
        resource = await resource_repo.get_by_id(self.db, resource_id)
        if not resource or resource.user_id != user_id:
            raise NotFoundError(
                message="Resource not found",
                details={"resource_id": str(resource_id)},
            )
        return resource

    async def delete_resource(self, resource_id: UUID, user_id: UUID) -> Resource:
        """Delete a resource."""
        resource = await self.get_resource_by_id(resource_id, user_id)
        return await resource_repo.delete(self.db, resource_id)

    async def get_summary(self, resource_id: UUID, user_id: UUID) -> str | None:
        """Get resource summary. Check Redis cache first, fallback to DB."""
        # Check Redis cache first
        if self.redis:
            cached = await self.redis.get(f"resource:{resource_id}:summary")
            if cached:
                return cached

        # Fallback to database
        resource = await self.get_resource_by_id(resource_id, user_id)
        return resource.summary

    async def trigger_summarization(self, resource_id: UUID, user_id: UUID) -> None:
        """Re-trigger summarization for a resource."""
        resource = await self.get_resource_by_id(resource_id, user_id)

        # Update status to pending
        await resource_repo.update(
            self.db,
            db_resource=resource,
            update_data={"summary_status": SummaryStatus.PENDING.value},
        )

        # Trigger Celery task
        celery_app.send_task(
            "app.worker.tasks.resource_tasks.process_resource",
            args=[str(resource_id)],
        )
