"""Resource routes (Resource Library)."""

import json
import logging
import os
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app.api.deps import DBSession, Redis, get_current_user, get_current_user_ws
from app.clients.redis import RedisClient
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.db.models.resource import ResourceType, SummaryStatus
from app.db.models.user import User
from app.db.session import get_db_context
from app.services.qa import QAService
from app.services.resource import ResourceService

from app.schemas.resource import ResourceCreate, ResourceResponse, ResourceSummaryResponse
from app.worker.celery_app import celery_app
from app.repositories import resource_repo, subject_repo

router = APIRouter()
logger = logging.getLogger(__name__)


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
    db: DBSession,
    redis: Redis,
    title: str = Form(...),
    type: ResourceType = Form(...),
    subject_id: UUID | None = Form(None),
    url: str | None = Form(None),
    content: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    """Create a new resource (multipart for PDF, form for link/note).
    
    - PDF type: requires file upload
    - LINK type: requires url
    - NOTE type: requires content
    """
    # Validate type-specific fields
    if type == ResourceType.PDF:
        if not file:
            raise ValidationError(message="PDF type requires a file upload")
        if file.content_type not in ["application/pdf", "application/octet-stream"]:
            # Allow octet-stream as some browsers send that for PDFs
            pass
    elif type == ResourceType.LINK:
        if not url:
            raise ValidationError(message="LINK type requires a URL")
    elif type == ResourceType.NOTE:
        if not content:
            raise ValidationError(message="NOTE type requires content")

    # Validate subject if provided
    if subject_id:
        subject = await subject_repo.get_by_id(db, subject_id)
        if not subject:
            raise NotFoundError(
                message="Subject not found",
                details={"subject_id": str(subject_id)},
            )
        if subject.user_id != current_user.id:
            raise ValidationError(message="Subject does not belong to current user")

    resource_in = ResourceCreate(
        title=title,
        type=type,
        url=url,
        subject_id=subject_id,
    )

    file_path = None
    file_size = None
    page_count = None
    
    if type == ResourceType.PDF and file:
        # Read file bytes
        file_bytes = await file.read()
        file_size = len(file_bytes)
        
        # Create resource first to get the ID
        resource_service = ResourceService(db, redis)
        resource = await resource_repo.create(
            db,
            title=title,
            type=type,
            file_path=None,  # Will be updated after processing
            url=None,
            content=None,
            subject_id=subject_id,
            user_id=current_user.id,
            file_size_bytes=file_size,
            page_count=page_count,
        )
        
        # Try to store file bytes in Redis, fallback to local storage
        file_stored = False
        if redis:
            try:
                await redis.raw.set(
                    f"resource:{resource.id}:upload_bytes",
                    file_bytes,
                    ex=3600,  # 1 hour TTL
                )
                file_stored = True
                logger.info(f"PDF stored in Redis for resource {resource.id}")
            except Exception as e:
                logger.warning(f"Redis unavailable, falling back to local storage: {e}")
        
        if not file_stored:
            # Fallback: save to local storage
            upload_dir = settings.LOCAL_UPLOAD_DIR
            os.makedirs(upload_dir, exist_ok=True)
            local_path = os.path.join(upload_dir, f"{resource.id}.pdf")
            with open(local_path, "wb") as f:
                f.write(file_bytes)
            
            # Update resource with file path
            resource.file_path = local_path
            await db.flush()
            logger.info(f"PDF saved locally at {local_path}")
        
        # Trigger Celery task for processing
        celery_app.send_task(
            "app.worker.tasks.resource_tasks.process_resource",
            args=[str(resource.id)],
        )
        
        await db.commit()
        return resource
    else:
        # For link and note types, create directly
        resource_service = ResourceService(db, redis)
        resource = await resource_repo.create(
            db,
            title=title,
            type=type,
            file_path=None,
            url=url,
            content=content,
            subject_id=subject_id,
            user_id=current_user.id,
            file_size_bytes=None,
            page_count=None,
        )
        
        # Trigger Celery task for summarization
        celery_app.send_task(
            "app.worker.tasks.resource_tasks.process_resource",
            args=[str(resource.id)],
        )
        
        await db.commit()
        return resource


@router.websocket("/{resource_id}/qa")
async def resource_qa_websocket(
    websocket: WebSocket,
    resource_id: UUID,
    token: str | None = Query(None),
):
    """WebSocket endpoint for Q&A about a resource.
    
    Connect with: ws://.../resources/{resource_id}/qa?token=<jwt>
    
    Send JSON: {"message": "your question here"}
    Receive JSON: {"type": "token", "content": "..."} or {"type": "done"}
    """
    # Authenticate user
    try:
        current_user = await get_current_user_ws(websocket, token=token)
    except Exception:
        # Connection will be closed by get_current_user_ws
        return
    
    await websocket.accept()
    
    try:
        async with get_db_context() as db:
            # Initialize services
            qa_service = QAService(db)
            redis_client = None
            
            # Try to get Redis from app state
            try:
                redis_client = websocket.app.state.redis
            except AttributeError:
                pass
            
            while True:
                # Receive message from client
                try:
                    data = await websocket.receive_text()
                    message_data = json.loads(data)
                    user_message = message_data.get("message", "").strip()
                    
                    if not user_message:
                        await websocket.send_json({
                            "type": "error",
                            "content": "Empty message received"
                        })
                        continue
                    
                    # Stream AI response
                    async for token in qa_service.ask_question(
                        resource_id=resource_id,
                        user_id=current_user.id,
                        user_message=user_message,
                        redis_client=redis_client,
                    ):
                        await websocket.send_json({
                            "type": "token",
                            "content": token
                        })
                    
                    # Send done message
                    await websocket.send_json({"type": "done"})
                    
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Invalid JSON format"
                    })
                    
    except WebSocketDisconnect:
        # Client disconnected normally
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": str(e)
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


import logging
logger = logging.getLogger(__name__)


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
