"""Resource Celery tasks."""

import logging
from typing import Any

import httpx
from celery import shared_task

from app.clients.redis import RedisClient
from app.core.config import settings
from app.db.models.resource import ResourceType, SummaryStatus
from app.db.session import get_db_context

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_resource(self, resource_id: str) -> dict[str, Any]:
    """
    Process a resource for summarization.

    Args:
        resource_id: Resource UUID as string

    Returns:
        Result dictionary with processed summary
    """
    import asyncio

    logger.info(f"Processing resource: {resource_id}")

    async def _process():
        async with get_db_context() as db:
            from app.repositories import resource_repo

            # Get resource
            resource = await resource_repo.get_by_id(db, resource_id)
            if not resource:
                logger.error(f"Resource not found: {resource_id}")
                return {"status": "error", "message": "Resource not found"}

            # Update status to processing
            await resource_repo.update(
                db,
                db_resource=resource,
                update_data={"summary_status": SummaryStatus.PROCESSING.value},
            )

            try:
                content = ""

                if resource.type == ResourceType.PDF.value and resource.file_path:
                    # Extract text from PDF
                    try:
                        import pdfplumber

                        # Note: In production, download from S3 first
                        # For now, assume file is local
                        with pdfplumber.open(resource.file_path) as pdf:
                            content = "\n".join(
                                page.extract_text() or "" for page in pdf.pages
                            )
                        logger.info(f"Extracted {len(content)} chars from PDF")
                    except Exception as e:
                        logger.error(f"PDF extraction failed: {e}")
                        content = "Failed to extract PDF content"

                elif resource.type == ResourceType.LINK.value and resource.url:
                    # Fetch URL content
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(resource.url, timeout=30)
                            response.raise_for_status()
                            # Simple text extraction (in production use BeautifulSoup)
                            content = response.text[:50000]  # Limit content size
                        logger.info(f"Fetched {len(content)} chars from URL")
                    except Exception as e:
                        logger.error(f"URL fetch failed: {e}")
                        content = "Failed to fetch URL content"

                elif resource.type == ResourceType.NOTE.value:
                    content = resource.content or ""

                # Generate summary using simple method
                # In production, use PydanticAI agent here
                summary = await _generate_summary(content)

                # Save summary
                await resource_repo.update(
                    db,
                    db_resource=resource,
                    update_data={
                        "summary": summary,
                        "summary_status": SummaryStatus.DONE.value,
                        "content": content[:10000] if content else None,  # Store excerpt
                    },
                )

                # Cache in Redis
                try:
                    redis = RedisClient(settings.REDIS_URL)
                    await redis.connect()
                    await redis.set(
                        f"resource:{resource_id}:summary",
                        summary,
                        ttl=86400,  # 24 hours
                    )
                    await redis.close()
                except Exception as e:
                    logger.warning(f"Failed to cache summary: {e}")

                return {
                    "status": "completed",
                    "resource_id": resource_id,
                    "summary_length": len(summary),
                }

            except Exception as exc:
                logger.error(f"Resource processing failed: {exc}")

                # Update status to failed
                await resource_repo.update(
                    db,
                    db_resource=resource,
                    update_data={"summary_status": SummaryStatus.FAILED.value},
                )

                # Retry with exponential backoff
                raise self.retry(exc=exc, countdown=2**self.request.retries)

    return asyncio.run(_process())


async def _generate_summary(content: str) -> str:
    """Generate a summary of the content."""
    # Simple summarization (in production, use PydanticAI)
    if not content:
        return "No content available for summarization."

    # Extract first 500 chars as summary
    max_summary_len = 500
    if len(content) <= max_summary_len:
        return content

    summary = content[:max_summary_len].rsplit(" ", 1)[0] + "..."
    return summary
