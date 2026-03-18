"""Leaderboard database model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.quiz import Quiz


class Leaderboard(Base):
    """Leaderboard model for quiz rankings."""

    __tablename__ = "leaderboards"

    __table_args__ = (
        UniqueConstraint("quiz_id", "user_id", name="leaderboards_quiz_user_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    best_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_time: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="leaderboard_entries")
    user: Mapped["User"] = relationship("User", back_populates="leaderboard_entries")

    def __repr__(self) -> str:
        return f"<Leaderboard(id={self.id}, quiz_id={self.quiz_id}, user_id={self.user_id}, rank={self.rank})>"
