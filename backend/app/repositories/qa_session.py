"""QA Session repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.qa_session import QASession


async def get_by_resource_and_user(
    db: AsyncSession, resource_id: UUID, user_id: UUID
) -> QASession | None:
    """Get QA session by resource ID and user ID."""
    result = await db.execute(
        select(QASession).where(
            QASession.resource_id == resource_id,
            QASession.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, session_id: UUID) -> QASession | None:
    """Get QA session by ID."""
    return await db.get(QASession, session_id)


async def create(
    db: AsyncSession,
    *,
    resource_id: UUID,
    user_id: UUID,
    messages: list[dict],
) -> QASession:
    """Create a new QA session."""
    qa_session = QASession(
        resource_id=resource_id,
        user_id=user_id,
        messages=messages,
    )
    db.add(qa_session)
    await db.flush()
    await db.refresh(qa_session)
    return qa_session


async def update_messages(
    db: AsyncSession,
    *,
    db_qa_session: QASession,
    messages: list[dict],
) -> QASession:
    """Update QA session messages."""
    db_qa_session.messages = messages
    db.add(db_qa_session)
    await db.flush()
    await db.refresh(db_qa_session)
    return db_qa_session
