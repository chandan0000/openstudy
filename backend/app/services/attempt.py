"""Attempt service (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.redis import RedisClient
from app.core.exceptions import NotFoundError, BadRequestError
from app.db.models.attempt import Attempt
from app.db.models.question import Question
from app.repositories import attempt_repo, leaderboard_repo, question_repo
from app.schemas.attempt import AttemptUpdate, AttemptSubmit, QuestionResult


class AttemptService:
    """Service for attempt-related business logic."""

    def __init__(self, db: AsyncSession, redis: RedisClient | None = None):
        self.db = db
        self.redis = redis

    async def start_attempt(self, user_id: UUID, quiz_id: UUID) -> Attempt:
        """Start a new quiz attempt."""
        # Check for existing incomplete attempt
        existing = await attempt_repo.get_incomplete_attempt(self.db, user_id, quiz_id)
        if existing:
            return existing

        return await attempt_repo.create(
            self.db,
            user_id=user_id,
            quiz_id=quiz_id,
        )

    async def save_progress(
        self, attempt_id: UUID, user_id: UUID, progress: AttemptUpdate
    ) -> Attempt:
        """Save attempt progress (auto-save answers)."""
        attempt = await self._get_attempt_or_raise(attempt_id, user_id)

        if attempt.is_completed:
            raise BadRequestError(message="Attempt is already completed")

        update_data = {"answers": progress.answers}
        return await attempt_repo.update(
            self.db,
            db_attempt=attempt,
            update_data=update_data,
        )

    async def submit_attempt(
        self,
        attempt_id: UUID,
        user_id: UUID,
        submit_data: AttemptSubmit,
    ) -> tuple[Attempt, list[QuestionResult], int | None]:
        """Submit an attempt, calculate score, and update leaderboard."""
        attempt = await self._get_attempt_or_raise(attempt_id, user_id)

        if attempt.is_completed:
            raise BadRequestError(message="Attempt is already completed")

        # Get quiz questions
        questions = await question_repo.get_by_quiz(self.db, attempt.quiz_id)
        question_map = {str(q.id): q for q in questions}

        # Calculate score
        score = 0
        total_marks = 0
        question_results = []

        for question in questions:
            total_marks += question.marks
            q_id = str(question.id)
            user_answer = submit_data.answers.get(q_id)
            is_correct = user_answer == question.correct_answer
            earned_marks = question.marks if is_correct else 0
            score += earned_marks

            question_results.append(
                QuestionResult(
                    question_id=question.id,
                    user_answer=user_answer,
                    correct_answer=question.correct_answer,
                    is_correct=is_correct,
                    marks=question.marks,
                    earned_marks=earned_marks,
                )
            )

        # Complete the attempt
        attempt = await attempt_repo.complete_attempt(
            self.db,
            db_attempt=attempt,
            score=score,
            total_marks=total_marks,
            time_taken_seconds=submit_data.time_taken_seconds or 0,
        )

        # Update leaderboard
        await leaderboard_repo.upsert(
            self.db,
            quiz_id=attempt.quiz_id,
            user_id=user_id,
            score=score,
            time_seconds=submit_data.time_taken_seconds or 0,
        )

        # Recalculate ranks
        await leaderboard_repo.update_ranks(self.db, attempt.quiz_id)

        # Update Redis sorted set
        if self.redis:
            await self.redis.raw.zadd(
                f"leaderboard:{attempt.quiz_id}",
                {str(user_id): score},
            )

        # Get rank
        rank = None
        if self.redis:
            rank_data = await self.redis.raw.zrevrank(
                f"leaderboard:{attempt.quiz_id}",
                str(user_id),
            )
            if rank_data is not None:
                rank = rank_data + 1  # 1-based rank

        return attempt, question_results, rank

    async def get_attempt_result(
        self, attempt_id: UUID, user_id: UUID
    ) -> tuple[Attempt, list[QuestionResult]]:
        """Get attempt result with per-question breakdown."""
        attempt = await self._get_attempt_or_raise(attempt_id, user_id)

        # Get quiz questions
        questions = await question_repo.get_by_quiz(self.db, attempt.quiz_id)

        # Build results
        question_results = []
        for question in questions:
            q_id = str(question.id)
            user_answer = attempt.answers.get(q_id) if attempt.answers else None
            is_correct = user_answer == question.correct_answer
            earned_marks = question.marks if is_correct else 0

            question_results.append(
                QuestionResult(
                    question_id=question.id,
                    user_answer=user_answer,
                    correct_answer=question.correct_answer,
                    is_correct=is_correct,
                    marks=question.marks,
                    earned_marks=earned_marks,
                )
            )

        return attempt, question_results

    async def _get_attempt_or_raise(self, attempt_id: UUID, user_id: UUID) -> Attempt:
        """Get attempt or raise NotFoundError."""
        attempt = await attempt_repo.get_by_id(self.db, attempt_id)
        if not attempt or attempt.user_id != user_id:
            raise NotFoundError(
                message="Attempt not found",
                details={"attempt_id": str(attempt_id)},
            )
        return attempt
