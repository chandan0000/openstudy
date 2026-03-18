"""QA Session database model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.resource import Resource


class QASession(Base, TimestampMixin):
    """QA Session model for resource Q&A conversations."""

    __tablename__ = "qa_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    messages: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    resource: Mapped["Resource"] = relationship("Resource", back_populates="qa_sessions")
    user: Mapped["User"] = relationship("User", back_populates="qa_sessions")

    def __repr__(self) -> str:
        return f"<QASession(id={self.id}, resource_id={self.resource_id})>"
