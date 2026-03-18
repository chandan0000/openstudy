"""Room routes (Study Room)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession, Redis, get_current_user
from app.clients.redis import RedisClient
from app.db.models.user import User
from app.services.room import RoomService
from app.services.timer import TimerService
from app.services.room_member import RoomMemberService  # Will be created
from app.schemas.room import RoomCreate, RoomResponse, RoomDetailResponse

router = APIRouter()


def get_room_service(db: DBSession) -> RoomService:
    """Dependency for RoomService."""
    return RoomService(db)


def get_timer_service(redis: Redis = None) -> TimerService:
    """Dependency for TimerService."""
    return TimerService(redis) if redis else None


RoomSvc = Annotated[RoomService, Depends(get_room_service)]
TimerSvc = Annotated[TimerService, Depends(get_timer_service)]


@router.get("", response_model=list[RoomResponse])
async def list_rooms(
    room_service: RoomSvc,
    subject: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List public rooms."""
    rooms = await room_service.get_public_rooms(
        subject=subject, skip=skip, limit=limit
    )
    # Add member count (would need to fetch from Redis or calculate)
    return rooms


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_in: RoomCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    room_service: RoomSvc,
):
    """Create a new room."""
    room = await room_service.create_room(current_user.id, room_in)
    return room


@router.get("/{room_id}", response_model=RoomDetailResponse)
async def get_room(
    room_id: UUID,
    room_service: RoomSvc,
):
    """Get room detail."""
    room = await room_service.get_room_detail(room_id)
    return room


@router.post("/{room_id}/join", response_model=dict)
async def join_public_room(
    room_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    room_service: RoomSvc,
):
    """Join a public room."""
    member = await room_service.join_room_public(room_id, current_user.id)
    return {"success": True, "member_id": str(member.id)}


@router.post("/join-private", response_model=dict)
async def join_private_room(
    invite_code: str,
    current_user: Annotated[User, Depends(get_current_user)],
    room_service: RoomSvc,
):
    """Join a private room by invite code."""
    member = await room_service.join_room_private(invite_code, current_user.id)
    return {"success": True, "member_id": str(member.id), "room_id": str(member.room_id)}


@router.delete("/{room_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_room(
    room_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    room_service: RoomSvc,
):
    """Leave a room."""
    await room_service.leave_room(room_id, current_user.id)
