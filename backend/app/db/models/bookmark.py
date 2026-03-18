"""Bookmark database model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.resource import Resource


class Bookmark(Base):
    """Bookmark model for saving resources."""

    __tablename__ = "bookmarks"

    __table_args__ = (
        UniqueConstraint("user_id", "resource_id", name="bookmarks_user_resource_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="bookmarks")
    resource: Mapped["Resource"] = relationship("Resource", back_populates="bookmarks")

    def __repr__(self) -> str:
        return f"<Bookmark(id={self.id}, user_id={self.user_id}, resource_id={self.resource_id})>"
