# app/db/models/room.py

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    max_members: Mapped[int] = mapped_column(Integer, default=10)
    invite_code: Mapped[str] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ✅ FK reference — User table ko point karna
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),  # "users" = tablename
        nullable=False
    )

    # ✅ Relationship — Python mein directly user object access karne ke liye
    owner: Mapped["User"] = relationship("User", back_populates="owned_rooms")

    # ✅ Reverse side — ek room ke saare members
    members: Mapped[list["RoomMember"]] = relationship("RoomMember", back_populates="room")
    study_sessions: Mapped[list["StudySession"]] = relationship("StudySession", back_populates="room")