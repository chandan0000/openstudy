"""Quiz routes (Quiz Engine)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession, get_current_user
from app.db.models.user import User
from app.services.quiz import QuizService
from app.services.question import QuestionService
from app.services.leaderboard import LeaderboardService
from app.schemas.quiz import QuizCreate, QuizResponse, QuizUpdate, QuizWithQuestions
from app.schemas.leaderboard import LeaderboardResponse, LeaderboardEntryResponse

router = APIRouter()


def get_quiz_service(db: DBSession) -> QuizService:
    """Dependency for QuizService."""
    return QuizService(db)


def get_question_service(db: DBSession) -> QuestionService:
    """Dependency for QuestionService."""
    return QuestionService(db)


def get_leaderboard_service(db: DBSession) -> LeaderboardService:
    """Dependency for LeaderboardService."""
    return LeaderboardService(db)


QuizSvc = Annotated[QuizService, Depends(get_quiz_service)]
QuestionSvc = Annotated[QuestionService, Depends(get_question_service)]
LeaderboardSvc = Annotated[LeaderboardService, Depends(get_leaderboard_service)]


@router.get("", response_model=list[QuizResponse])
async def list_quizzes(
    quiz_service: QuizSvc,
    subject: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List published quizzes."""
    quizzes = await quiz_service.list_published_quizzes(
        subject=subject, skip=skip, limit=limit
    )
    return quizzes


@router.post("", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    quiz_in: QuizCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    quiz_service: QuizSvc,
):
    """Create a new quiz."""
    quiz = await quiz_service.create_quiz(current_user.id, quiz_in)
    return quiz


@router.get("/{quiz_id}", response_model=QuizWithQuestions)
async def get_quiz(
    quiz_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    quiz_service: QuizSvc,
    question_service: QuestionSvc,
):
    """Get quiz detail with questions."""
    quiz = await quiz_service.get_quiz_with_questions(
        quiz_id, current_user.id, is_creator=False
    )
    questions = await question_service.get_quiz_questions(quiz_id)

    # Hide correct answers if not creator
    is_creator = quiz.created_by == current_user.id
    question_responses = []
    for q in questions:
        q_dict = {
            "id": q.id,
            "quiz_id": q.quiz_id,
            "question_text": q.question_text,
            "options": q.options,
            "correct_answer": q.correct_answer if is_creator else None,
            "explanation": q.explanation,
            "difficulty": q.difficulty,
            "marks": q.marks,
            "order_index": q.order_index,
        }
        question_responses.append(q_dict)

    return QuizWithQuestions(
        id=quiz.id,
        title=quiz.title,
        subject=quiz.subject,
        description=quiz.description,
        time_limit_minutes=quiz.time_limit_minutes,
        is_published=quiz.is_published,
        is_ai_generated=quiz.is_ai_generated,
        created_by=quiz.created_by,
        created_at=quiz.created_at,
        updated_at=quiz.updated_at,
        questions=question_responses,
    )


@router.put("/{quiz_id}", response_model=QuizResponse)
async def update_quiz(
    quiz_id: UUID,
    quiz_in: QuizUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    quiz_service: QuizSvc,
):
    """Update a quiz (creator only)."""
    quiz = await quiz_service.update_quiz(quiz_id, current_user.id, quiz_in)
    return quiz


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(
    quiz_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    quiz_service: QuizSvc,
):
    """Delete a quiz (creator only)."""
    await quiz_service.delete_quiz(quiz_id, current_user.id)


@router.post("/{quiz_id}/publish", response_model=QuizResponse)
async def publish_quiz(
    quiz_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    quiz_service: QuizSvc,
):
    """Toggle quiz publish status (creator only)."""
    quiz = await quiz_service.publish_quiz(quiz_id, current_user.id)
    return quiz


@router.get("/{quiz_id}/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    quiz_id: UUID,
    leaderboard_service: LeaderboardSvc,
):
    """Get quiz leaderboard (top 10)."""
    entries = await leaderboard_service.get_quiz_leaderboard(quiz_id, limit=10)

    # Get quiz info for response
    from app.repositories import quiz_repo
    quiz = await quiz_repo.get_by_id(leaderboard_service.db, quiz_id)

    return LeaderboardResponse(
        quiz_id=quiz_id,
        quiz_title=quiz.title if quiz else "",
        entries=[
            LeaderboardEntryResponse(
                id=e.id,
                quiz_id=e.quiz_id,
                user={"id": e.user.id, "full_name": e.user.full_name} if hasattr(e, 'user') else {"id": e.user_id, "full_name": None},
                rank=e.rank,
                best_score=e.best_score,
                best_time=e.best_time,
                attempt_count=e.attempt_count,
            )
            for e in entries
        ],
    )
