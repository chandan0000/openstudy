"""OpenAI client wrapper.

Provides async and sync OpenAI clients for AI operations.
"""

from openai import AsyncOpenAI, OpenAI

from app.core.config import settings


class OpenAIClient:
    """OpenAI client wrapper for AI operations.

    Usage:
        # Async client
        client = OpenAIClient()
        response = await client.chat.completions.create(...)

        # Sync client (for Celery tasks)
        sync_client = get_sync_openai_client()
        response = sync_client.chat.completions.create(...)
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self._async_client: AsyncOpenAI | None = None

    async def connect(self) -> None:
        """Initialize async OpenAI client."""
        self._async_client = AsyncOpenAI(api_key=self.api_key)

    async def close(self) -> None:
        """Close async OpenAI client."""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None

    @property
    def chat(self):
        """Access chat completions API."""
        if not self._async_client:
            raise RuntimeError("OpenAI client not connected. Call connect() first.")
        return self._async_client.chat

    @property
    def raw(self) -> AsyncOpenAI:
        """Access the underlying AsyncOpenAI client."""
        if not self._async_client:
            raise RuntimeError("OpenAI client not connected. Call connect() first.")
        return self._async_client


def get_sync_openai_client(api_key: str | None = None) -> OpenAI:
    """Get a synchronous OpenAI client (for use in Celery tasks).

    Args:
        api_key: Optional API key (defaults to settings.OPENAI_API_KEY)

    Returns:
        Sync OpenAI client instance
    """
    key = api_key or settings.OPENAI_API_KEY
    return OpenAI(api_key=key)


def get_async_openai_client(api_key: str | None = None) -> AsyncOpenAI:
    """Get an asynchronous OpenAI client.

    Args:
        api_key: Optional API key (defaults to settings.OPENAI_API_KEY)

    Returns:
        Async OpenAI client instance
    """
    key = api_key or settings.OPENAI_API_KEY
    return AsyncOpenAI(api_key=key)
