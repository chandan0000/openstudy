"""Note routes (Resource Library)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession, get_current_user
from app.db.models.user import User
from app.services.note import NoteService
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate

router = APIRouter()


def get_note_service(db: DBSession) -> NoteService:
    """Dependency for NoteService."""
    return NoteService(db)


NoteSvc = Annotated[NoteService, Depends(get_note_service)]


@router.get("", response_model=list[NoteResponse])
async def list_notes(
    current_user: Annotated[User, Depends(get_current_user)],
    note_service: NoteSvc,
    resource_id: UUID | None = Query(None),
    tag: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List notes with optional filters."""
    if tag:
        notes = await note_service.search_by_tag(
            current_user.id, tag, skip=skip, limit=limit
        )
    elif resource_id:
        notes = await note_service.get_resource_notes(
            resource_id, current_user.id, skip=skip, limit=limit
        )
    else:
        notes = await note_service.get_resource_notes(
            current_user.id, current_user.id, skip=skip, limit=limit
        )
    return notes


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_in: NoteCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    note_service: NoteSvc,
    resource_id: UUID,
):
    """Create a new note for a resource."""
    note = await note_service.create_note(current_user.id, resource_id, note_in)
    return note


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    note_service: NoteSvc,
):
    """Get a specific note."""
    note = await note_service.get_note_by_id(note_id, current_user.id)
    return note


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: UUID,
    note_in: NoteUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    note_service: NoteSvc,
):
    """Update a note."""
    note = await note_service.update_note(note_id, current_user.id, note_in)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    note_service: NoteSvc,
):
    """Delete a note."""
    await note_service.delete_note(note_id, current_user.id)
