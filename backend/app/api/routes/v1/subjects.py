"""Subject routes (Resource Library)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession, get_current_user
from app.db.models.user import User
from app.services.subject import SubjectService
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate

router = APIRouter()


def get_subject_service(db: DBSession) -> SubjectService:
    """Dependency for SubjectService."""
    return SubjectService(db)


SubjectSvc = Annotated[SubjectService, Depends(get_subject_service)]


@router.get("", response_model=list[SubjectResponse])
async def list_subjects(
    current_user: Annotated[User, Depends(get_current_user)],
    subject_service: SubjectSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List user's subjects."""
    subjects = await subject_service.get_user_subjects(
        current_user.id, skip=skip, limit=limit
    )
    return subjects


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    subject_in: SubjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    subject_service: SubjectSvc,
):
    """Create a new subject."""
    subject = await subject_service.create_subject(current_user.id, subject_in)
    return subject


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    subject_service: SubjectSvc,
):
    """Get a specific subject."""
    subject = await subject_service.get_subject_by_id(subject_id)
    # Verify ownership
    if subject.user_id != current_user.id:
        return None
    return subject


@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: UUID,
    subject_in: SubjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    subject_service: SubjectSvc,
):
    """Update a subject."""
    subject = await subject_service.update_subject(
        subject_id, current_user.id, subject_in
    )
    return subject


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    subject_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    subject_service: SubjectSvc,
):
    """Delete a subject."""
    await subject_service.delete_subject(subject_id, current_user.id)
