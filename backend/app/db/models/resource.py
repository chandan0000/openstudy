"""Resource database model."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.subject import Subject
    from app.db.models.note import Note
    from app.db.models.bookmark import Bookmark
    from app.db.models.qa_session import QASession


class ResourceType(str, Enum):
    """Resource type enumeration."""

    PDF = "pdf"
    LINK = "link"
    NOTE = "note"


class SummaryStatus(str, Enum):
    """Summary processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class Resource(Base, TimestampMixin):
    """Resource model for storing learning materials."""

    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(
        SAEnum(ResourceType, name="resourcetype"),
        nullable=False,
    )
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_status: Mapped[str] = mapped_column(
        SAEnum(SummaryStatus, name="summarystatus"),
        default=SummaryStatus.PENDING.value,
        nullable=False,
    )
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    subject: Mapped["Subject | None"] = relationship(
        "Subject", back_populates="resources"
    )
    user: Mapped["User"] = relationship("User", back_populates="resources")
    notes: Mapped[list["Note"]] = relationship(
        "Note", back_populates="resource", cascade="all, delete-orphan"
    )
    bookmarks: Mapped[list["Bookmark"]] = relationship(
        "Bookmark", back_populates="resource", cascade="all, delete-orphan"
    )
    qa_sessions: Mapped[list["QASession"]] = relationship(
        "QASession", back_populates="resource", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Resource(id={self.id}, title={self.title}, type={self.type})>"
