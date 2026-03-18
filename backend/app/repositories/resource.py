"""Resource repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.resource import Resource, ResourceType, SummaryStatus


async def get_by_user(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
) -> list[Resource]:
    """Get resources by user ID."""
    result = await db.execute(
        select(Resource)
        .where(Resource.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, resource_id: UUID) -> Resource | None:
    """Get resource by ID."""
    return await db.get(Resource, resource_id)


async def get_by_subject(
    db: AsyncSession, subject_id: UUID, skip: int = 0, limit: int = 100
) -> list[Resource]:
    """Get resources by subject ID."""
    result = await db.execute(
        select(Resource)
        .where(Resource.subject_id == subject_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_summary_status(
    db: AsyncSession,
    status: SummaryStatus,
    skip: int = 0,
    limit: int = 100,
) -> list[Resource]:
    """Get resources by summary status."""
    result = await db.execute(
        select(Resource)
        .where(Resource.summary_status == status.value)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    title: str,
    type: ResourceType,
    file_path: str | None,
    url: str | None,
    content: str | None,
    subject_id: UUID | None,
    user_id: UUID,
    file_size_bytes: int | None = None,
    page_count: int | None = None,
) -> Resource:
    """Create a new resource."""
    resource = Resource(
        title=title,
        type=type.value,
        file_path=file_path,
        url=url,
        content=content,
        subject_id=subject_id,
        user_id=user_id,
        file_size_bytes=file_size_bytes,
        page_count=page_count,
        summary_status=SummaryStatus.PENDING.value,
    )
    db.add(resource)
    await db.flush()
    await db.refresh(resource)
    return resource


async def update(
    db: AsyncSession,
    *,
    db_resource: Resource,
    update_data: dict,
) -> Resource:
    """Update a resource."""
    for field, value in update_data.items():
        setattr(db_resource, field, value)

    db.add(db_resource)
    await db.flush()
    await db.refresh(db_resource)
    return db_resource


async def delete(db: AsyncSession, resource_id: UUID) -> Resource | None:
    """Delete a resource."""
    resource = await get_by_id(db, resource_id)
    if resource:
        await db.delete(resource)
        await db.flush()
    return resource


async def search(
    db: AsyncSession,
    user_id: UUID,
    query: str,
    skip: int = 0,
    limit: int = 100,
) -> list[Resource]:
    """Search resources by title and summary (ILIKE)."""
    search_pattern = f"%{query}%"
    result = await db.execute(
        select(Resource)
        .where(
            Resource.user_id == user_id,
            or_(
                func.lower(Resource.title).like(func.lower(search_pattern)),
                func.lower(Resource.summary).like(func.lower(search_pattern)),
            ),
        )
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())
