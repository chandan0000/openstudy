"""Quiz service (PostgreSQL async)."""

import json
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.openai_client import get_async_openai_client
from app.core.config import settings
from app.core.exceptions import NotFoundError, AuthorizationError
from app.db.models.quiz import Quiz
from app.repositories import quiz_repo
from app.schemas.quiz import QuizCreate, QuizUpdate

logger = logging.getLogger(__name__)


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

    async def generate_questions_with_ai(
        self,
        topic: str,
        count: int,
        difficulty: str,
        subject: str | None = None,
    ) -> list[dict]:
        """Generate multiple choice questions using OpenAI.
        
        Args:
            topic: The topic to generate questions about
            count: Number of questions to generate
            difficulty: easy, medium, or hard
            subject: Optional subject category
            
        Returns:
            List of question dictionaries with question_text, options,
            correct_answer, explanation, difficulty, and marks fields
        """
        if not settings.OPENAI_API_KEY or not settings.AI_QUIZ_GENERATION_ENABLED:
            raise ValueError("AI quiz generation is not enabled or OpenAI API key is not configured")
        
        # Clamp count to reasonable range
        count = max(1, min(count, 20))
        
        client = get_async_openai_client()
        
        prompt = f"""Generate {count} multiple choice questions about: {topic}

Difficulty level: {difficulty}
{f'Subject: {subject}' if subject else ''}

Requirements:
- Each question must have exactly 4 options (A, B, C, D)
- Only one correct answer per question
- Include a brief explanation for the correct answer
- Questions should be clear and unambiguous
- Difficulty should match the specified level

Return ONLY a valid JSON array in this exact format with no markdown, no code blocks, and no additional text:
[
  {{
    "question_text": "What is the capital of France?",
    "options": ["A. London", "B. Paris", "C. Berlin", "D. Madrid"],
    "correct_answer": "B",
    "explanation": "Paris is the capital and most populous city of France.",
    "difficulty": "easy",
    "marks": 1
  }}
]

The correct_answer must be a single uppercase letter: A, B, C, or D.
The options array must have 4 strings, each prefixed with "A. ", "B. ", "C. ", "D. " respectively."""

        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educational content creator specializing in multiple choice questions. You always return valid JSON without any markdown formatting or code blocks."
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=settings.OPENAI_MAX_TOKENS * 2,  # Allow more tokens for multiple questions
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
            
            # Parse the JSON response
            try:
                data = json.loads(content)
                # The response might be wrapped in an object with a "questions" key
                if isinstance(data, dict):
                    if "questions" in data:
                        questions = data["questions"]
                    else:
                        # Try to find any array in the response
                        questions = next(
                            (v for v in data.values() if isinstance(v, list)),
                            []
                        )
                else:
                    questions = data if isinstance(data, list) else []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                raise ValueError(f"Invalid JSON response from OpenAI: {e}")
            
            # Validate and clean up questions
            valid_questions = []
            for i, q in enumerate(questions):
                if not isinstance(q, dict):
                    logger.warning(f"Question {i} is not a dict, skipping")
                    continue
                
                # Check required fields
                required_fields = ["question_text", "options", "correct_answer", "explanation"]
                missing = [f for f in required_fields if f not in q]
                if missing:
                    logger.warning(f"Question {i} missing fields {missing}, skipping")
                    continue
                
                # Validate options
                if not isinstance(q["options"], list) or len(q["options"]) != 4:
                    logger.warning(f"Question {i} must have exactly 4 options, skipping")
                    continue
                
                # Validate correct_answer
                if q["correct_answer"] not in ["A", "B", "C", "D"]:
                    logger.warning(f"Question {i} has invalid correct_answer, skipping")
                    continue
                
                # Ensure options are prefixed correctly
                prefixes = ["A. ", "B. ", "C. ", "D. "],
                options = []
                for j, opt in enumerate(q["options"]):
                    opt_str = str(opt)
                    # Remove existing prefix if present and add correct one
                    for prefix in ["A. ", "B. ", "C. ", "D. ", "A ", "B ", "C ", "D "]:
                        if opt_str.startswith(prefix):
                            opt_str = opt_str[len(prefix):]
                            break
                    options.append(f"{prefixes[0][j]}{opt_str}")
                
                # Add difficulty and marks if missing
                question_data = {
                    "question_text": str(q["question_text"]),
                    "options": options,
                    "correct_answer": str(q["correct_answer"]),
                    "explanation": str(q["explanation"]),
                    "difficulty": str(q.get("difficulty", difficulty)),
                    "marks": int(q.get("marks", 1)),
                }
                
                valid_questions.append(question_data)
            
            logger.info(f"Generated {len(valid_questions)} valid questions out of {len(questions)}")
            return valid_questions
            
        except Exception as e:
            logger.error(f"Failed to generate questions with AI: {e}")
            raise ValueError(f"AI question generation failed: {e}")
