"""Resource routes (Resource Library)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.api.deps import DBSession, Redis, get_current_user
from app.clients.redis import RedisClient
from app.db.models.resource import ResourceType, SummaryStatus
from app.db.models.user import User
from app.services.resource import ResourceService
from app.schemas.resource import ResourceCreate, ResourceResponse, ResourceSummaryResponse

router = APIRouter()


def get_resource_service(
    db: DBSession, redis: Redis = None
) -> ResourceService:
    """Dependency for ResourceService."""
    return ResourceService(db, redis)


ResourceSvc = Annotated[ResourceService, Depends(get_resource_service)]


@router.get("", response_model=list[ResourceResponse])
async def list_resources(
    current_user: Annotated[User, Depends(get_current_user)],
    resource_service: ResourceSvc,
    subject_id: UUID | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List user's resources with optional filters."""
    resources = await resource_service.get_user_resources(
        current_user.id,
        subject_id=subject_id,
        search=search,
        skip=skip,
        limit=limit,
    )
    return resources


@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    current_user: Annotated[User, Depends(get_current_user)],
    resource_service: ResourceSvc,
    title: str = Form(...),
    type: ResourceType = Form(...),
    url: str | None = Form(None),
    subject_id: UUID | None = Form(None),
    file: UploadFile | None = File(None),
):
    """Create a new resource (multipart for PDF, form for link/note)."""
    resource_in = ResourceCreate(
        title=title,
        type=type,
        url=url,
        subject_id=subject_id,
    )

    file_path = None
    file_size = None
    if file and type == ResourceType.PDF:
        # Note: In production, upload to S3 here
        file_path = f"uploads/{current_user.id}/{file.filename}"
        file_size = file.size if hasattr(file, 'size') else None

    resource = await resource_service.create_resource(
        current_user.id,
        resource_in,
        file_path=file_path,
        file_size_bytes=file_size,
    )
    return resource


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    resource_service: ResourceSvc,
):
    """Get a specific resource with summary."""
    resource = await resource_service.get_resource_by_id(resource_id, current_user.id)
    return resource


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    resource_service: ResourceSvc,
):
    """Delete a resource."""
    await resource_service.delete_resource(resource_id, current_user.id)


@router.post("/{resource_id}/regenerate-summary", response_model=ResourceSummaryResponse)
async def regenerate_summary(
    resource_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    resource_service: ResourceSvc,
):
    """Re-trigger summarization for a resource."""
    await resource_service.trigger_summarization(resource_id, current_user.id)
    return ResourceSummaryResponse(
        id=resource_id,
        title="",  # Will be fetched by caller
        summary=None,
        summary_status=SummaryStatus.PENDING.value,
    )
