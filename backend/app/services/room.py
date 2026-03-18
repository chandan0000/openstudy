"""Room service (PostgreSQL async)."""

import random
import string
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, AlreadyExistsError, BadRequestError
from app.db.models.room import Room
from app.db.models.room_member import RoomMember
from app.repositories import room_repo, room_member_repo
from app.schemas.room import RoomCreate


class RoomService:
    """Service for room-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_room(self, owner_id: UUID, room_in: RoomCreate) -> Room:
        """Create a new room."""
        invite_code = None
        if not room_in.is_public:
            # Generate 6-char invite code for private rooms
            invite_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

        room = await room_repo.create(
            self.db,
            name=room_in.name,
            subject=room_in.subject,
            owner_id=owner_id,
            is_public=room_in.is_public,
            max_members=room_in.max_members,
            invite_code=invite_code,
        )

        # Add owner as room member
        await room_member_repo.add_member(
            self.db,
            room_id=room.id,
            user_id=owner_id,
            role="owner",
        )

        return room

    async def join_room_public(self, room_id: UUID, user_id: UUID) -> RoomMember:
        """Join a public room."""
        room = await room_repo.get_by_id(self.db, room_id)
        if not room or not room.is_public or not room.is_active:
            raise NotFoundError(
                message="Room not found",
                details={"room_id": str(room_id)},
            )

        # Check if already a member
        existing = await room_member_repo.get_by_room_and_user(self.db, room_id, user_id)
        if existing:
            raise AlreadyExistsError(
                message="Already a member of this room",
            )

        # Check room capacity
        member_count = await room_member_repo.get_member_count(self.db, room_id)
        if member_count >= room.max_members:
            raise BadRequestError(
                message="Room is full",
            )

        return await room_member_repo.add_member(
            self.db,
            room_id=room_id,
            user_id=user_id,
            role="member",
        )

    async def join_room_private(self, invite_code: str, user_id: UUID) -> RoomMember:
        """Join a private room by invite code."""
        room = await room_repo.get_by_invite_code(self.db, invite_code)
        if not room or not room.is_active:
            raise NotFoundError(
                message="Invalid invite code",
                details={"invite_code": invite_code},
            )

        # Check if already a member
        existing = await room_member_repo.get_by_room_and_user(self.db, room.id, user_id)
        if existing:
            raise AlreadyExistsError(
                message="Already a member of this room",
            )

        # Check room capacity
        member_count = await room_member_repo.get_member_count(self.db, room.id)
        if member_count >= room.max_members:
            raise BadRequestError(
                message="Room is full",
            )

        return await room_member_repo.add_member(
            self.db,
            room_id=room.id,
            user_id=user_id,
            role="member",
        )

    async def leave_room(self, room_id: UUID, user_id: UUID) -> RoomMember | None:
        """Leave a room."""
        room = await room_repo.get_by_id(self.db, room_id)
        if not room or not room.is_active:
            raise NotFoundError(
                message="Room not found",
                details={"room_id": str(room_id)},
            )

        # Don't allow owner to leave (they must delete the room)
        member = await room_member_repo.get_by_room_and_user(self.db, room_id, user_id)
        if member and member.role == "owner":
            raise BadRequestError(
                message="Room owner cannot leave. Delete the room instead.",
            )

        return await room_member_repo.remove_member(self.db, room_id, user_id)

    async def get_public_rooms(
        self,
        subject: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Room]:
        """Get public rooms."""
        return await room_repo.get_public_rooms(
            self.db, subject=subject, skip=skip, limit=limit
        )

    async def get_room_detail(self, room_id: UUID) -> Room:
        """Get room details."""
        room = await room_repo.get_by_id(self.db, room_id)
        if not room or not room.is_active:
            raise NotFoundError(
                message="Room not found",
                details={"room_id": str(room_id)},
            )
        return room
