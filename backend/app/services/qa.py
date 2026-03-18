"""QA service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.openai_client import get_async_openai_client
from app.clients.redis import RedisClient
from app.core.config import settings
from app.db.models.qa_session import QASession
from app.repositories import qa_session_repo, resource_repo


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

    async def ask_question(
        self,
        resource_id: UUID,
        user_id: UUID,
        user_message: str,
        redis_client: RedisClient | None = None,
    ):
        """Ask a question about a resource and stream the AI response.
        
        This is an async generator that yields string tokens.
        
        Args:
            resource_id: The resource UUID
            user_id: The user UUID
            user_message: The user's question
            redis_client: Optional Redis client for caching
            
        Yields:
            String tokens from the AI response
        """
        # Get the resource
        resource = await resource_repo.get_by_id(self.db, resource_id)
        if not resource:
            raise ValueError(f"Resource not found: {resource_id}")
        
        # Check if user has access to this resource
        if resource.user_id != user_id:
            raise ValueError("User does not have access to this resource")
        
        # Get context from Redis cache or resource
        context = None
        if redis_client:
            try:
                context = await redis_client.get(f"resource:{resource_id}:summary")
            except Exception:
                pass
        
        if not context:
            # Fallback to resource summary or content
            context = resource.summary or resource.content or ""
        
        # Get or create QA session
        session = await self.get_or_create_session(resource_id, user_id)
        
        # Load last 10 messages for conversation history
        history = list(session.messages) if session.messages else []
        recent_history = history[-10:] if len(history) > 10 else history
        
        # Build OpenAI messages
        messages = [
            {
                "role": "system",
                "content": f"""You are a helpful study assistant. Answer the user's questions based ONLY on the following study material.
If the answer cannot be found in the material, say so clearly.

Study Material:
{context[:8000]}

Instructions:
- Only answer based on the provided material
- Be concise but thorough
- Use bullet points for lists when appropriate
- If uncertain, admit it"""
            }
        ]
        
        # Add conversation history
        for msg in recent_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add the current question
        messages.append({"role": "user", "content": user_message})
        
        # Stream response from OpenAI
        full_response = ""
        
        if not settings.OPENAI_API_KEY or not settings.AI_QA_ENABLED:
            # Fallback when OpenAI is not configured
            fallback_response = "AI Q&A is not enabled or OpenAI API key is not configured. Please check your settings."
            yield fallback_response
            full_response = fallback_response
        else:
            try:
                client = get_async_openai_client()
                stream = await client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,
                    max_tokens=settings.OPENAI_MAX_TOKENS,
                    temperature=0.7,
                    stream=True,
                )
                
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_response += token
                        yield token
                        
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                yield error_msg
                full_response = error_msg
        
        # After streaming, save messages to database
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": full_response})
        
        await qa_session_repo.update_messages(
            self.db,
            db_qa_session=session,
            messages=history,
        )
        await self.db.commit()
