"""Bookmark routes (Resource Library)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, get_current_user
from app.db.models.user import User
from app.services.bookmark import BookmarkService
from app.schemas.bookmark import BookmarkCreate, BookmarkResponse

router = APIRouter()


def get_bookmark_service(db: DBSession) -> BookmarkService:
    """Dependency for BookmarkService."""
    return BookmarkService(db)


BookmarkSvc = Annotated[BookmarkService, Depends(get_bookmark_service)]


@router.get("", response_model=list[BookmarkResponse])
async def list_bookmarks(
    current_user: Annotated[User, Depends(get_current_user)],
    bookmark_service: BookmarkSvc,
):
    """List user's bookmarks."""
    bookmarks = await bookmark_service.get_user_bookmarks(current_user.id)
    return bookmarks


@router.post("/add", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def add_bookmark(
    bookmark_in: BookmarkCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    bookmark_service: BookmarkSvc,
):
    """Add a bookmark."""
    bookmark = await bookmark_service.add_bookmark(
        current_user.id, bookmark_in.resource_id
    )
    return bookmark


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark(
    bookmark_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    bookmark_service: BookmarkSvc,
):
    """Remove a bookmark by resource ID."""
    await bookmark_service.remove_bookmark_by_resource(
        current_user.id, bookmark_id
    )
