"""Leaderboard service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.redis import RedisClient
from app.db.models.leaderboard import Leaderboard
from app.repositories import leaderboard_repo


class LeaderboardService:
    """Service for leaderboard-related business logic."""

    def __init__(self, db: AsyncSession, redis: RedisClient | None = None):
        self.db = db
        self.redis = redis

    async def get_quiz_leaderboard(
        self,
        quiz_id: UUID,
        limit: int = 10,
    ) -> list[Leaderboard]:
        """Get quiz leaderboard. Check Redis first, fallback to DB."""
        # Try Redis sorted set first
        if self.redis:
            try:
                # Get top users from Redis
                results = await self.redis.raw.zrevrange(
                    f"leaderboard:{quiz_id}",
                    0,
                    limit - 1,
                    withscores=True,
                )
                if results:
                    # Convert to leaderboard entries
                    entries = []
                    for rank, (user_id_bytes, score) in enumerate(results, start=1):
                        user_id = user_id_bytes.decode() if isinstance(user_id_bytes, bytes) else user_id_bytes
                        # Get full entry from DB for user info
                        entry = await leaderboard_repo.get_by_user_and_quiz(
                            self.db, UUID(user_id), quiz_id
                        )
                        if entry:
                            entry.rank = rank
                            entries.append(entry)
                    if entries:
                        return entries
            except Exception:
                # Fallback to DB on Redis error
                pass

        # Fallback to database
        return await leaderboard_repo.get_by_quiz(self.db, quiz_id, limit=limit)

    async def recalculate_ranks(self, quiz_id: UUID) -> None:
        """Recalculate leaderboard ranks for a quiz."""
        await leaderboard_repo.update_ranks(self.db, quiz_id)
