"""Question service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.question import Question
from app.repositories import question_repo
from app.schemas.question import QuestionCreate, QuestionUpdate, BulkQuestionCreate


class QuestionService:
    """Service for question-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_questions(
        self, quiz_id: UUID, questions_in: BulkQuestionCreate
    ) -> list[Question]:
        """Add questions to a quiz."""
        questions_data = [
            q.model_dump() for q in questions_in.questions
        ]
        return await question_repo.bulk_create(self.db, quiz_id, questions_data)

    async def bulk_add(
        self, quiz_id: UUID, questions_data: list[dict]
    ) -> list[Question]:
        """Bulk add questions from AI generation."""
        return await question_repo.bulk_create(self.db, quiz_id, questions_data)

    async def update_question(
        self, question_id: UUID, question_in: QuestionUpdate
    ) -> Question:
        """Update a question."""
        question = await question_repo.get_by_id(self.db, question_id)
        if not question:
            raise NotFoundError(
                message="Question not found",
                details={"question_id": str(question_id)},
            )

        update_data = question_in.model_dump(exclude_unset=True)
        return await question_repo.update(
            self.db,
            db_question=question,
            update_data=update_data,
        )

    async def delete_question(self, question_id: UUID) -> Question:
        """Delete a question."""
        question = await question_repo.get_by_id(self.db, question_id)
        if not question:
            raise NotFoundError(
                message="Question not found",
                details={"question_id": str(question_id)},
            )

        return await question_repo.delete(self.db, question_id)

    async def get_quiz_questions(
        self, quiz_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Question]:
        """Get questions for a quiz."""
        return await question_repo.get_by_quiz(self.db, quiz_id, skip=skip, limit=limit)
