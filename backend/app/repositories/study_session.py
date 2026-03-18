"""Study Session repository (PostgreSQL async)."""

from uuid import UUID
from datetime import datetime, date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.study_session import StudySession


async def create(
    db: AsyncSession,
    *,
    user_id: UUID,
    room_id: UUID | None,
    session_type: str = "pomodoro",
) -> StudySession:
    """Create a new study session."""
    session = StudySession(
        user_id=user_id,
        room_id=room_id,
        started_at=datetime.utcnow(),
        session_type=session_type,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def end_session(
    db: AsyncSession,
    *,
    db_session: StudySession,
    pomodoro_count: int = 0,
) -> StudySession:
    """End a study session."""
    now = datetime.utcnow()
    db_session.ended_at = now

    # Calculate duration in minutes
    if db_session.started_at:
        duration = now - db_session.started_at
        db_session.duration_minutes = int(duration.total_seconds() / 60)

    db_session.pomodoro_count = pomodoro_count

    db.add(db_session)
    await db.flush()
    await db.refresh(db_session)
    return db_session


async def get_by_user(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
) -> list[StudySession]:
    """Get study sessions by user ID."""
    result = await db.execute(
        select(StudySession)
        .where(StudySession.user_id == user_id)
        .order_by(StudySession.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_room(
    db: AsyncSession, room_id: UUID, skip: int = 0, limit: int = 100
) -> list[StudySession]:
    """Get study sessions by room ID."""
    result = await db.execute(
        select(StudySession)
        .where(StudySession.room_id == room_id)
        .order_by(StudySession.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_today_total_minutes(db: AsyncSession, user_id: UUID) -> int:
    """Get total study minutes for today."""
    today = date.today()
    tomorrow = today + timedelta(days=1)

    result = await db.execute(
        select(func.coalesce(func.sum(StudySession.duration_minutes), 0))
        .where(
            StudySession.user_id == user_id,
            StudySession.started_at >= today,
            StudySession.started_at < tomorrow,
            StudySession.ended_at.isnot(None),
        )
    )
    return result.scalar() or 0


async def get_by_id(db: AsyncSession, session_id: UUID) -> StudySession | None:
    """Get study session by ID."""
    return await db.get(StudySession, session_id)
