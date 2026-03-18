"""Quiz service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, AuthorizationError
from app.db.models.quiz import Quiz
from app.repositories import quiz_repo
from app.schemas.quiz import QuizCreate, QuizUpdate


class QuizService:
    """Service for quiz-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_quiz(self, created_by: UUID, quiz_in: QuizCreate) -> Quiz:
        """Create a new quiz."""
        return await quiz_repo.create(
            self.db,
            title=quiz_in.title,
            subject=quiz_in.subject,
            description=quiz_in.description,
            time_limit_minutes=quiz_in.time_limit_minutes,
            created_by=created_by,
        )

    async def publish_quiz(self, quiz_id: UUID, user_id: UUID) -> Quiz:
        """Toggle publish status of a quiz."""
        quiz = await self._get_quiz_or_raise(quiz_id, user_id, check_owner=True)

        # Toggle publish status
        update_data = {"is_published": not quiz.is_published}
        return await quiz_repo.update(
            self.db,
            db_quiz=quiz,
            update_data=update_data,
        )

    async def get_quiz_with_questions(
        self, quiz_id: UUID, user_id: UUID, is_creator: bool
    ) -> Quiz:
        """Get quiz with questions.

        If not creator, correct answers are hidden in routes layer.
        """
        quiz = await quiz_repo.get_by_id(self.db, quiz_id)
        if not quiz:
            raise NotFoundError(
                message="Quiz not found",
                details={"quiz_id": str(quiz_id)},
            )

        # Must be published or creator
        if not quiz.is_published and quiz.created_by != user_id:
            raise NotFoundError(
                message="Quiz not found",
                details={"quiz_id": str(quiz_id)},
            )

        return quiz

    async def list_published_quizzes(
        self, subject: str | None = None, skip: int = 0, limit: int = 100
    ) -> list[Quiz]:
        """List published quizzes."""
        return await quiz_repo.get_published(
            self.db, subject=subject, skip=skip, limit=limit
        )

    async def delete_quiz(self, quiz_id: UUID, user_id: UUID) -> Quiz:
        """Delete a quiz (creator only)."""
        await self._get_quiz_or_raise(quiz_id, user_id, check_owner=True)
        return await quiz_repo.delete(self.db, quiz_id)

    async def update_quiz(
        self, quiz_id: UUID, user_id: UUID, quiz_in: QuizUpdate
    ) -> Quiz:
        """Update a quiz (creator only)."""
        quiz = await self._get_quiz_or_raise(quiz_id, user_id, check_owner=True)

        update_data = quiz_in.model_dump(exclude_unset=True)
        return await quiz_repo.update(
            self.db,
            db_quiz=quiz,
            update_data=update_data,
        )

    async def _get_quiz_or_raise(
        self, quiz_id: UUID, user_id: UUID, check_owner: bool = False
    ) -> Quiz:
        """Get quiz or raise NotFoundError. Optionally check ownership."""
        quiz = await quiz_repo.get_by_id(self.db, quiz_id)
        if not quiz:
            raise NotFoundError(
                message="Quiz not found",
                details={"quiz_id": str(quiz_id)},
            )

        if check_owner and quiz.created_by != user_id:
            raise AuthorizationError(
                message="Only the creator can modify this quiz",
            )

        return quiz

    async def get_quiz_by_id(self, quiz_id: UUID) -> Quiz | None:
        """Get quiz by ID (no access checks)."""
        return await quiz_repo.get_by_id(self.db, quiz_id)
