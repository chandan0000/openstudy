import uuid
from datetime import date
from sqlalchemy import Date, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

class DailyGoal(Base, TimestampMixin):
    __tablename__ = "daily_goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    target_minutes: Mapped[int] = mapped_column(Integer, default=60)
    date: Mapped[date] = mapped_column(Date, default=date.today)
    achieved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="daily_goals")