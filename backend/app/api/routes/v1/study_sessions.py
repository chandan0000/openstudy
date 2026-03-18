"""Study Session routes (Study Room / Pomodoro)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession, get_current_user
from app.db.models.user import User
from app.services.study_session import SessionService
from app.schemas.study_session import (
    StudySessionCreate,
    StudySessionEnd,
    StudySessionResponse,
    StudyStatsResponse,
)

router = APIRouter()


def get_study_session_service(db: DBSession) -> SessionService:
    """Dependency for SessionService."""
    return SessionService(db)


StudySessionSvc = Annotated[SessionService, Depends(get_study_session_service)]


@router.post("", response_model=StudySessionResponse, status_code=status.HTTP_201_CREATED)
async def start_study_session(
    session_in: StudySessionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session_service: StudySessionSvc,
):
    """Start a solo study session."""
    session = await session_service.start_session(
        current_user.id,
        session_in.room_id,
        session_type=session_in.session_type,
    )
    return session


@router.patch("/{session_id}/end", response_model=StudySessionResponse)
async def end_study_session(
    session_id: UUID,
    end_data: StudySessionEnd,
    current_user: Annotated[User, Depends(get_current_user)],
    session_service: StudySessionSvc,
):
    """End a study session."""
    session = await session_service.end_session(
        session_id, current_user.id, pomodoro_count=end_data.pomodoro_count
    )
    return session


@router.get("/me", response_model=list[StudySessionResponse])
async def get_my_study_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    session_service: StudySessionSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get my study session history."""
    sessions = await session_service.get_user_history(
        current_user.id, skip=skip, limit=limit
    )
    return sessions


@router.get("/me/stats", response_model=StudyStatsResponse)
async def get_my_study_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    session_service: StudySessionSvc,
):
    """Get my study statistics."""
    stats = await session_service.get_user_stats(current_user.id)
    return StudyStatsResponse(**stats)
