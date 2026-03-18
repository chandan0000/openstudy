"""Question repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.question import Question


async def get_by_quiz(
    db: AsyncSession, quiz_id: UUID, skip: int = 0, limit: int = 100
) -> list[Question]:
    """Get questions by quiz ID."""
    result = await db.execute(
        select(Question)
        .where(Question.quiz_id == quiz_id)
        .order_by(Question.order_index)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, question_id: UUID) -> Question | None:
    """Get question by ID."""
    return await db.get(Question, question_id)


async def bulk_create(
    db: AsyncSession,
    quiz_id: UUID,
    questions_data: list[dict],
) -> list[Question]:
    """Bulk create questions."""
    questions = []
    for data in questions_data:
        question = Question(
            quiz_id=quiz_id,
            **data,
        )
        db.add(question)
        questions.append(question)

    await db.flush()
    for q in questions:
        await db.refresh(q)
    return questions


async def update(
    db: AsyncSession,
    *,
    db_question: Question,
    update_data: dict,
) -> Question:
    """Update a question."""
    for field, value in update_data.items():
        setattr(db_question, field, value)

    db.add(db_question)
    await db.flush()
    await db.refresh(db_question)
    return db_question


async def delete(db: AsyncSession, question_id: UUID) -> Question | None:
    """Delete a question."""
    question = await get_by_id(db, question_id)
    if question:
        await db.delete(question)
        await db.flush()
    return question
