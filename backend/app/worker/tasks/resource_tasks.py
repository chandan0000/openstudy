"""Resource Celery tasks."""

import asyncio
import io
import logging
import os
import re
from typing import Any

import httpx
import pdfplumber
from celery import shared_task

from app.clients.openai_client import get_sync_openai_client
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
            await db.commit()

            try:
                content = ""

                if resource.type == ResourceType.PDF.value:
                    # Get file bytes from Redis
                    redis = RedisClient(settings.REDIS_URL)
                    await redis.connect()
                    file_bytes = await redis.raw.get(f"resource:{resource_id}:upload_bytes")
                    
                    if not file_bytes:
                        logger.error(f"No file bytes found in Redis for resource: {resource_id}")
                        raise ValueError("File bytes not found in Redis")
                    
                    # Extract text from PDF
                    try:
                        pdf_file = io.BytesIO(file_bytes)
                        with pdfplumber.open(pdf_file) as pdf:
                            content = "\n".join(
                                page.extract_text() or "" for page in pdf.pages
                            )
                            page_count = len(pdf.pages)
                        logger.info(f"Extracted {len(content)} chars from PDF, {page_count} pages")
                    except Exception as e:
                        logger.error(f"PDF extraction failed: {e}")
                        content = "Failed to extract PDF content"
                        page_count = None
                    
                    # Save file to S3 or local storage
                    file_path = None
                    if settings.AWS_S3_ENABLED:
                        # Save to S3
                        import boto3
                        s3 = boto3.client(
                            "s3",
                            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                            region_name=settings.AWS_REGION,
                        )
                        s3_key = f"resources/{resource.user_id}/{resource_id}.pdf"
                        s3.put_object(
                            Bucket=settings.AWS_BUCKET_NAME,
                            Key=s3_key,
                            Body=file_bytes,
                            ContentType="application/pdf",
                        )
                        file_path = f"s3://{settings.AWS_BUCKET_NAME}/{s3_key}"
                        logger.info(f"Saved PDF to S3: {file_path}")
                    else:
                        # Save to local storage
                        upload_dir = settings.LOCAL_UPLOAD_DIR
                        os.makedirs(upload_dir, exist_ok=True)
                        local_path = os.path.join(upload_dir, f"{resource_id}.pdf")
                        with open(local_path, "wb") as f:
                            f.write(file_bytes)
                        file_path = local_path
                        logger.info(f"Saved PDF to local: {file_path}")
                    
                    # Update resource with file_path and page_count
                    await resource_repo.update(
                        db,
                        db_resource=resource,
                        update_data={
                            "file_path": file_path,
                            "page_count": page_count,
                        },
                    )
                    await db.commit()
                    
                    # Clean up Redis
                    await redis.delete(f"resource:{resource_id}:upload_bytes")
                    await redis.close()

                elif resource.type == ResourceType.LINK.value and resource.url:
                    # Fetch URL content
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(resource.url, timeout=30)
                            response.raise_for_status()
                            html_content = response.text
                            
                            # Strip HTML tags using BeautifulSoup if available
                            try:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(html_content, "html.parser")
                                # Remove script and style elements
                                for script in soup(["script", "style"]):
                                    script.decompose()
                                # Get text
                                text = soup.get_text()
                                # Clean up whitespace
                                lines = (line.strip() for line in text.splitlines())
                                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                                content = "\n".join(chunk for chunk in chunks if chunk)
                            except ImportError:
                                # Fallback to regex if BeautifulSoup not available
                                content = re.sub(r"<[^>]+>", "", html_content)
                                content = re.sub(r"\s+", " ", content).strip()
                            
                            # Limit content size
                            content = content[:50000]
                        logger.info(f"Fetched {len(content)} chars from URL")
                    except Exception as e:
                        logger.error(f"URL fetch failed: {e}")
                        content = "Failed to fetch URL content"

                elif resource.type == ResourceType.NOTE.value:
                    content = resource.content or ""

                # Generate summary using OpenAI
                summary = await _generate_summary_with_openai(content)

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
                await db.commit()

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
                await db.commit()

                # Retry with 60 second delay
                raise self.retry(exc=exc, countdown=60)

    return asyncio.run(_process())


async def _generate_summary_with_openai(content: str) -> str:
    """Generate a summary using OpenAI API."""
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not set, returning truncated content")
        if not content:
            return "No content available for summarization."
        max_len = 500
        if len(content) <= max_len:
            return content
        return content[:max_len].rsplit(" ", 1)[0] + "..."
    
    if not content:
        return "No content available for summarization."
    
    # Limit input to avoid token overflow
    max_input_chars = 12000
    truncated_content = content[:max_input_chars]
    if len(content) > max_input_chars:
        truncated_content = truncated_content.rsplit(" ", 1)[0] + "..."
    
    try:
        client = get_sync_openai_client()
        
        prompt = f"""Please provide a structured study summary of the following content. 
Format your response with these sections:
- Main Topic: A brief description of what this material is about
- Key Concepts: The important concepts covered (bullet points)
- Important Points: Key takeaways and facts to remember
- Quick Overview: A 2-3 sentence summary

Keep it student-friendly and easy to study from.

Content to summarize:
{truncated_content}
"""
        
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful study assistant that creates clear, structured summaries of educational material."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=0.5,
        )
        
        summary = response.choices[0].message.content
        logger.info(f"Generated summary of {len(summary)} chars using OpenAI")
        return summary or "Failed to generate summary."
        
    except Exception as e:
        logger.error(f"OpenAI summary generation failed: {e}")
        # Fallback to simple truncation
        max_len = 500
        if len(content) <= max_len:
            return content
        return content[:max_len].rsplit(" ", 1)[0] + "..."


# Keep the old function for backward compatibility
async def _generate_summary(content: str) -> str:
    """Generate a summary of the content (fallback method)."""
    return await _generate_summary_with_openai(content)
