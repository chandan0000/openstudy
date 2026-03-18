"""Study Session service (PostgreSQL async)."""

from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.study_session import StudySession
from app.repositories import study_session_repo
from app.services.goal import GoalService


class SessionService:
    """Service for study session-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.goal_service = GoalService(db)

    async def start_session(
        self,
        user_id: UUID,
        room_id: UUID | None,
        session_type: str = "pomodoro",
    ) -> StudySession:
        """Start a new study session."""
        return await study_session_repo.create(
            self.db,
            user_id=user_id,
            room_id=room_id,
            session_type=session_type,
        )

    async def end_session(
        self,
        session_id: UUID,
        user_id: UUID,
        pomodoro_count: int = 0,
    ) -> StudySession:
        """End a study session and check daily goal progress."""
        session = await study_session_repo.get_by_id(self.db, session_id)
        if not session or session.user_id != user_id:
            raise NotFoundError(
                message="Session not found",
                details={"session_id": str(session_id)},
            )

        if session.ended_at:
            raise NotFoundError(
                message="Session already ended",
                details={"session_id": str(session_id)},
            )

        # End the session
        session = await study_session_repo.end_session(
            self.db,
            db_session=session,
            pomodoro_count=pomodoro_count,
        )

        # Check daily goal progress
        await self.goal_service.check_and_update_goal(user_id)

        return session

    async def get_user_stats(self, user_id: UUID) -> dict:
        """Get user study statistics."""
        today_minutes = await study_session_repo.get_today_total_minutes(self.db, user_id)

        # Get week minutes (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        sessions = await study_session_repo.get_by_user(self.db, user_id, limit=1000)
        week_minutes = sum(
            s.duration_minutes or 0
            for s in sessions
            if s.started_at and s.started_at >= week_ago and s.ended_at
        )

        # Total pomodoros
        total_pomodoros = sum(s.pomodoro_count or 0 for s in sessions)
        total_sessions = len([s for s in sessions if s.ended_at])

        return {
            "today_minutes": today_minutes,
            "week_minutes": week_minutes,
            "total_pomodoros": total_pomodoros,
            "total_sessions": total_sessions,
        }

    async def get_user_history(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[StudySession]:
        """Get user study session history."""
        return await study_session_repo.get_by_user(self.db, user_id, skip=skip, limit=limit)

    async def get_session_by_id(self, session_id: UUID, user_id: UUID) -> StudySession:
        """Get a session by ID."""
        session = await study_session_repo.get_by_id(self.db, session_id)
        if not session or session.user_id != user_id:
            raise NotFoundError(
                message="Session not found",
                details={"session_id": str(session_id)},
            )
        return session
