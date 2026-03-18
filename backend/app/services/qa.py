"""QA service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.qa_session import QASession
from app.repositories import qa_session_repo


class QAService:
    """Service for Q&A session-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(
        self, resource_id: UUID, user_id: UUID
    ) -> QASession:
        """Get existing QA session or create a new one."""
        session = await qa_session_repo.get_by_resource_and_user(
            self.db, resource_id, user_id
        )
        if session:
            return session

        return await qa_session_repo.create(
            self.db,
            resource_id=resource_id,
            user_id=user_id,
            messages=[],
        )

    async def append_message(
        self,
        resource_id: UUID,
        user_id: UUID,
        role: str,
        content: str,
    ) -> QASession:
        """Append a message to the QA session."""
        session = await self.get_or_create_session(resource_id, user_id)

        messages = list(session.messages) if session.messages else []
        messages.append({"role": role, "content": content})

        return await qa_session_repo.update_messages(
            self.db,
            db_qa_session=session,
            messages=messages,
        )

    async def get_session_history(
        self, resource_id: UUID, user_id: UUID
    ) -> list[dict]:
        """Get the QA session message history."""
        session = await qa_session_repo.get_by_resource_and_user(
            self.db, resource_id, user_id
        )
        if session:
            return session.messages if session.messages else []
        return []
