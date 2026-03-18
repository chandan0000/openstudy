"""User database model."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.session import Session
    from app.db.models.room import Room
    from app.db.models.room_member import RoomMember
    from app.db.models.study_session import StudySession
    from app.db.models.daily_goal import DailyGoal
    from app.db.models.subject import Subject
    from app.db.models.resource import Resource
    from app.db.models.note import Note
    from app.db.models.bookmark import Bookmark
    from app.db.models.qa_session import QASession
    from app.db.models.quiz import Quiz
    from app.db.models.attempt import Attempt
    from app.db.models.leaderboard import Leaderboard


class UserRole(str, Enum):
    """User role enumeration.

    Roles hierarchy (higher includes lower permissions):
    - ADMIN: Full system access, can manage users and settings
    - USER: Standard user access
    """

    ADMIN = "admin"
    USER = "user"


class User(Base, TimestampMixin):
    """User model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value, nullable=False)
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Relationship to sessions
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )

    # Feature 3: Study Room relationships
    owned_rooms: Mapped[list["Room"]] = relationship(
        "Room", back_populates="owner", cascade="all, delete-orphan"
    )
    room_memberships: Mapped[list["RoomMember"]] = relationship(
        "RoomMember", back_populates="user", cascade="all, delete-orphan"
    )
    study_sessions: Mapped[list["StudySession"]] = relationship(
        "StudySession", back_populates="user", cascade="all, delete-orphan"
    )
    daily_goals: Mapped[list["DailyGoal"]] = relationship(
        "DailyGoal", back_populates="user", cascade="all, delete-orphan"
    )

    # Feature 1: Resource Library relationships
    subjects: Mapped[list["Subject"]] = relationship(
        "Subject", back_populates="user", cascade="all, delete-orphan"
    )
    resources: Mapped[list["Resource"]] = relationship(
        "Resource", back_populates="user", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(
        "Note", back_populates="user", cascade="all, delete-orphan"
    )
    bookmarks: Mapped[list["Bookmark"]] = relationship(
        "Bookmark", back_populates="user", cascade="all, delete-orphan"
    )
    qa_sessions: Mapped[list["QASession"]] = relationship(
        "QASession", back_populates="user", cascade="all, delete-orphan"
    )

    # Feature 2: Quiz Engine relationships
    quizzes_created: Mapped[list["Quiz"]] = relationship(
        "Quiz", back_populates="creator", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt", back_populates="user", cascade="all, delete-orphan"
    )
    leaderboard_entries: Mapped[list["Leaderboard"]] = relationship(
        "Leaderboard", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def user_role(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)

    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has the required role or higher.

        Admin role has access to everything.
        """
        if self.role == UserRole.ADMIN.value:
            return True
        return self.role == required_role.value

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
