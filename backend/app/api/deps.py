"""API dependencies.

Dependency injection factories for services, repositories, and authentication.
"""
# ruff: noqa: I001, E402 - Imports structured for Jinja2 template conditionals

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
from fastapi import Request

from app.clients.redis import RedisClient


async def get_redis(request: Request) -> RedisClient:
    """Get Redis client from lifespan state."""
    return request.state.redis


Redis = Annotated[RedisClient, Depends(get_redis)]


# === Service Dependencies ===

from app.services.user import UserService
from app.services.session import SessionService
from app.services.subject import SubjectService
from app.services.resource import ResourceService
from app.services.note import NoteService
from app.services.bookmark import BookmarkService
from app.services.qa import QAService
from app.services.quiz import QuizService
from app.services.question import QuestionService
from app.services.attempt import AttemptService
from app.services.leaderboard import LeaderboardService
from app.services.room import RoomService
from app.services.timer import TimerService
from app.services.study_session import SessionService as StudySessionService
from app.services.goal import GoalService

def get_user_service(db: DBSession) -> UserService:
    """Create UserService instance with database session."""
    return UserService(db)


def get_session_service(db: DBSession) -> SessionService:
    """Create SessionService instance with database session."""
    return SessionService(db)


def get_subject_service(db: DBSession) -> SubjectService:
    """Create SubjectService instance with database session."""
    return SubjectService(db)


def get_resource_service(db: DBSession, redis: Redis = None) -> ResourceService:
    """Create ResourceService instance with database session."""
    return ResourceService(db, redis)


def get_note_service(db: DBSession) -> NoteService:
    """Create NoteService instance with database session."""
    return NoteService(db)


def get_bookmark_service(db: DBSession) -> BookmarkService:
    """Create BookmarkService instance with database session."""
    return BookmarkService(db)


def get_qa_service(db: DBSession) -> QAService:
    """Create QAService instance with database session."""
    return QAService(db)


def get_quiz_service(db: DBSession) -> QuizService:
    """Create QuizService instance with database session."""
    return QuizService(db)


def get_question_service(db: DBSession) -> QuestionService:
    """Create QuestionService instance with database session."""
    return QuestionService(db)


def get_attempt_service(db: DBSession, redis: Redis = None) -> AttemptService:
    """Create AttemptService instance with database session."""
    return AttemptService(db, redis)


def get_leaderboard_service(db: DBSession, redis: Redis = None) -> LeaderboardService:
    """Create LeaderboardService instance with database session."""
    return LeaderboardService(db, redis)


def get_room_service(db: DBSession) -> RoomService:
    """Create RoomService instance with database session."""
    return RoomService(db)


def get_timer_service(redis: Redis) -> TimerService:
    """Create TimerService instance with Redis."""
    return TimerService(redis)


def get_study_session_service(db: DBSession) -> StudySessionService:
    """Create StudySessionService instance with database session."""
    return StudySessionService(db)


def get_goal_service(db: DBSession) -> GoalService:
    """Create GoalService instance with database session."""
    return GoalService(db)


UserSvc = Annotated[UserService, Depends(get_user_service)]
SessionSvc = Annotated[SessionService, Depends(get_session_service)]
SubjectSvc = Annotated[SubjectService, Depends(get_subject_service)]
ResourceSvc = Annotated[ResourceService, Depends(get_resource_service)]
NoteSvc = Annotated[NoteService, Depends(get_note_service)]
BookmarkSvc = Annotated[BookmarkService, Depends(get_bookmark_service)]
QASvc = Annotated[QAService, Depends(get_qa_service)]
QuizSvc = Annotated[QuizService, Depends(get_quiz_service)]
QuestionSvc = Annotated[QuestionService, Depends(get_question_service)]
AttemptSvc = Annotated[AttemptService, Depends(get_attempt_service)]
LeaderboardSvc = Annotated[LeaderboardService, Depends(get_leaderboard_service)]
RoomSvc = Annotated[RoomService, Depends(get_room_service)]
TimerSvc = Annotated[TimerService, Depends(get_timer_service)]
StudySessionSvc = Annotated[StudySessionService, Depends(get_study_session_service)]
GoalSvc = Annotated[GoalService, Depends(get_goal_service)]


# === Authentication Dependencies ===

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.db.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: UserSvc,
) -> User:
    """Get current authenticated user from JWT token.

    Returns the full User object including role information.

    Raises:
        AuthenticationError: If token is invalid or user not found.
    """
    from uuid import UUID

    from app.core.security import verify_token

    payload = verify_token(token)
    if payload is None:
        raise AuthenticationError(message="Invalid or expired token")

    # Ensure this is an access token, not a refresh token
    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token payload")

    user = await user_service.get_by_id(UUID(user_id))
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    return user


class RoleChecker:
    """Dependency class for role-based access control.

    Usage:
        # Require admin role
        @router.get("/admin-only")
        async def admin_endpoint(
            user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]
        ):
            ...

        # Require any authenticated user
        @router.get("/users")
        async def users_endpoint(
            user: Annotated[User, Depends(get_current_user)]
        ):
            ...
    """

    def __init__(self, required_role: UserRole) -> None:
        self.required_role = required_role

    async def __call__(
        self,
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if user has the required role.

        Raises:
            AuthorizationError: If user doesn't have the required role.
        """
        if not user.has_role(self.required_role):
            raise AuthorizationError(
                message=f"Role '{self.required_role.value}' required for this action"
            )
        return user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user and verify they are a superuser.

    Raises:
        AuthorizationError: If user is not a superuser.
    """
    if not current_user.is_superuser:
        raise AuthorizationError(message="Superuser privileges required")
    return current_user


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_active_superuser)]
CurrentAdmin = Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]


# WebSocket authentication dependency
from fastapi import WebSocket, Query, Cookie


async def get_current_user_ws(
    websocket: WebSocket,
    token: str | None = Query(None, alias="token"),
    access_token: str | None = Cookie(None),
) -> User:
    """Get current user from WebSocket JWT token.

    Token can be passed either as:
    - Query parameter: ws://...?token=<jwt>
    - Cookie: access_token cookie (set by HTTP login)

    Raises:
        AuthenticationError: If token is invalid or user not found.
    """
    from uuid import UUID

    from app.core.security import verify_token

    # Try query parameter first, then cookie
    auth_token = token or access_token

    if not auth_token:
        await websocket.close(code=4001, reason="Missing authentication token")
        raise AuthenticationError(message="Missing authentication token")

    payload = verify_token(auth_token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        raise AuthenticationError(message="Invalid or expired token")

    if payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid token type")
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid token payload")
        raise AuthenticationError(message="Invalid token payload")

    from app.db.session import get_db_context

    async with get_db_context() as db:
        user_service = UserService(db)
        user = await user_service.get_by_id(UUID(user_id))

    if not user.is_active:
        await websocket.close(code=4001, reason="User account is disabled")
        raise AuthenticationError(message="User account is disabled")

    return user


import secrets

from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def verify_api_key(
    api_key: Annotated[str | None, Depends(api_key_header)],
) -> str:
    """Verify API key from header.

    Uses constant-time comparison to prevent timing attacks.

    Raises:
        AuthenticationError: If API key is missing.
        AuthorizationError: If API key is invalid.
    """
    if api_key is None:
        raise AuthenticationError(message="API Key header missing")
    if not secrets.compare_digest(api_key, settings.API_KEY):
        raise AuthorizationError(message="Invalid API Key")
    return api_key


ValidAPIKey = Annotated[str, Depends(verify_api_key)]
