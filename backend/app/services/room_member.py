"""Room Member service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.room_member import RoomMember
from app.repositories import room_member_repo


class RoomMemberService:
    """Service for room member-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_room_members(
        self, room_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[RoomMember]:
        """Get members of a room."""
        return await room_member_repo.get_room_members(
            self.db, room_id, skip=skip, limit=limit
        )

    async def get_member_count(self, room_id: UUID) -> int:
        """Get the number of members in a room."""
        return await room_member_repo.get_member_count(self.db, room_id)

    async def get_membership(
        self, room_id: UUID, user_id: UUID
    ) -> RoomMember | None:
        """Get a user's membership in a room."""
        return await room_member_repo.get_by_room_and_user(
            self.db, room_id, user_id
        )
