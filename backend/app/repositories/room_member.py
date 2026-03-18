"""Room Member repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.room_member import RoomMember


async def get_room_members(
    db: AsyncSession, room_id: UUID, skip: int = 0, limit: int = 100
) -> list[RoomMember]:
    """Get members of a room."""
    result = await db.execute(
        select(RoomMember)
        .where(RoomMember.room_id == room_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_room_and_user(
    db: AsyncSession, room_id: UUID, user_id: UUID
) -> RoomMember | None:
    """Get room membership by room ID and user ID."""
    result = await db.execute(
        select(RoomMember).where(
            RoomMember.room_id == room_id,
            RoomMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def add_member(
    db: AsyncSession,
    *,
    room_id: UUID,
    user_id: UUID,
    role: str = "member",
) -> RoomMember:
    """Add a member to a room."""
    member = RoomMember(
        room_id=room_id,
        user_id=user_id,
        role=role,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def remove_member(db: AsyncSession, room_id: UUID, user_id: UUID) -> RoomMember | None:
    """Remove a member from a room."""
    member = await get_by_room_and_user(db, room_id, user_id)
    if member:
        await db.delete(member)
        await db.flush()
    return member


async def get_member_count(db: AsyncSession, room_id: UUID) -> int:
    """Get the number of members in a room."""
    result = await db.execute(
        select(func.count()).select_from(RoomMember).where(RoomMember.room_id == room_id)
    )
    return result.scalar() or 0
