"""Room repository (PostgreSQL async)."""

from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.room import Room


async def get_public_rooms(
    db: AsyncSession,
    subject: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Room]:
    """Get public rooms with optional subject filter."""
    query = select(Room).where(Room.is_public == True, Room.is_active == True)

    if subject:
        query = query.where(Room.subject == subject)

    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_by_invite_code(db: AsyncSession, invite_code: str) -> Room | None:
    """Get room by invite code."""
    result = await db.execute(
        select(Room).where(
            Room.invite_code == invite_code,
            Room.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, room_id: UUID) -> Room | None:
    """Get room by ID."""
    return await db.get(Room, room_id)


async def create(
    db: AsyncSession,
    *,
    name: str,
    subject: str | None,
    owner_id: UUID,
    is_public: bool,
    max_members: int,
    invite_code: str | None = None,
) -> Room:
    """Create a new room."""
    room = Room(
        name=name,
        subject=subject,
        owner_id=owner_id,
        is_public=is_public,
        max_members=max_members,
        invite_code=invite_code,
        is_active=True,
    )
    db.add(room)
    await db.flush()
    await db.refresh(room)
    return room


async def update(
    db: AsyncSession,
    *,
    db_room: Room,
    update_data: dict,
) -> Room:
    """Update a room."""
    for field, value in update_data.items():
        setattr(db_room, field, value)

    db.add(db_room)
    await db.flush()
    await db.refresh(db_room)
    return db_room


async def deactivate(db: AsyncSession, room_id: UUID) -> Room | None:
    """Deactivate a room."""
    room = await get_by_id(db, room_id)
    if room:
        room.is_active = False
        db.add(room)
        await db.flush()
        await db.refresh(room)
    return room


async def cleanup_inactive(
    db: AsyncSession,
    days: int = 30,
) -> int:
    """Deactivate rooms with no activity in the given number of days."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    # Note: This is a simplified version - you may want to check actual session activity
    result = await db.execute(
        select(Room).where(
            Room.is_active == True,
            Room.created_at < cutoff_date,
        )
    )
    rooms = result.scalars().all()
    count = 0
    for room in rooms:
        room.is_active = False
        db.add(room)
        count += 1

    await db.flush()
    return count
