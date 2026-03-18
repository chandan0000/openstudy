"""Timer service (Redis operations only)."""

import json
import time
from uuid import UUID

from app.clients.redis import RedisClient


class TimerService:
    """Service for room timer state management (Redis only)."""

    def __init__(self, redis: RedisClient):
        self.redis = redis

    def _key(self, room_id: UUID) -> str:
        return f"room:{room_id}:timer"

    async def start_timer(
        self,
        room_id: UUID,
        phase: str = "focus",
        duration: int = 1500,  # 25 minutes default
        pomodoro_number: int = 1,
    ) -> dict:
        """Start a timer for a room."""
        key = self._key(room_id)
        state = {
            "phase": phase,
            "duration": duration,
            "started_at": time.time(),
            "pomodoro_number": pomodoro_number,
        }
        await self.redis.set(key, json.dumps(state), ttl=duration + 60)
        return state

    async def get_timer_state(self, room_id: UUID) -> dict | None:
        """Get current timer state with remaining time."""
        key = self._key(room_id)
        data = await self.redis.get(key)
        if not data:
            return None

        state = json.loads(data)
        elapsed = time.time() - state["started_at"]
        remaining = max(0, state["duration"] - int(elapsed))
        state["remaining"] = remaining
        state["is_running"] = remaining > 0
        return state

    async def stop_timer(self, room_id: UUID) -> bool:
        """Stop a timer."""
        key = self._key(room_id)
        deleted = await self.redis.delete(key)
        return deleted > 0
