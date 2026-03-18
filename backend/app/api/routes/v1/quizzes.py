"""Quiz routes (Quiz Engine)."""

import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app.api.deps import DBSession, get_current_user, get_current_user_ws
from app.db.models.user import User
from app.db.session import get_db_context
from app.repositories import question_repo, quiz_repo
from app.services.quiz import QuizService
from app.services.question import QuestionService
from app.services.leaderboard import LeaderboardService
from app.schemas.quiz import QuizCreate, QuizResponse, QuizUpdate, QuizWithQuestions
from app.schemas.leaderboard import LeaderboardResponse, LeaderboardEntryResponse

router = APIRouter()
logger = logging.getLogger(__name__)


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


@router.websocket("/{quiz_id}/generate-questions")
async def quiz_generate_questions_websocket(
    websocket: WebSocket,
    quiz_id: UUID,
    token: str | None = Query(None),
):
    """WebSocket endpoint for AI-generated quiz questions.
    
    Connect with: ws://.../quizzes/{quiz_id}/generate-questions?token=<jwt>
    
    Send JSON: {"topic": "Python Basics", "count": 5, "difficulty": "easy"}
    Receive JSON: 
      - {"type": "progress", "content": "Generation started..."}
      - {"type": "question", "index": 1, "total": 5, "data": {...}}
      - {"type": "done", "total": 5}
      - {"type": "error", "content": "..."}
    """
    # Authenticate user
    try:
        current_user = await get_current_user_ws(websocket, token=token)
    except Exception:
        # Connection will be closed by get_current_user_ws
        return
    
    await websocket.accept()
    
    try:
        async with get_db_context() as db:
            # Verify quiz exists and belongs to current user
            quiz_service = QuizService(db)
            quiz = await quiz_service.get_quiz_by_id(quiz_id)
            
            if not quiz:
                await websocket.send_json({
                    "type": "error",
                    "content": "Quiz not found"
                })
                await websocket.close()
                return
            
            if quiz.created_by != current_user.id:
                await websocket.send_json({
                    "type": "error",
                    "content": "Only the quiz creator can generate questions"
                })
                await websocket.close()
                return
            
            # Wait for generation parameters
            try:
                data = await websocket.receive_text()
                params = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON format"
                })
                await websocket.close()
                return
            except WebSocketDisconnect:
                return
            
            topic = params.get("topic", "").strip()
            count = min(int(params.get("count", 5)), 20)  # Max 20 questions
            difficulty = params.get("difficulty", "medium")
            
            if not topic:
                await websocket.send_json({
                    "type": "error",
                    "content": "Topic is required"
                })
                await websocket.close()
                return
            
            # Send progress message
            await websocket.send_json({
                "type": "progress",
                "content": f"Generating {count} questions about '{topic}'..."
            })
            
            try:
                # Generate questions with AI
                questions = await quiz_service.generate_questions_with_ai(
                    topic=topic,
                    count=count,
                    difficulty=difficulty,
                    subject=quiz.subject,
                )
                
                if not questions:
                    await websocket.send_json({
                        "type": "error",
                        "content": "No valid questions were generated"
                    })
                    await websocket.close()
                    return
                
                # Save each question and send to client
                for i, question_data in enumerate(questions):
                    # Add order_index based on current question count
                    question_data["order_index"] = i
                    
                    # Save to database
                    from app.db.models.question import Question
                    question = Question(
                        quiz_id=quiz_id,
                        **question_data,
                    )
                    db.add(question)
                    await db.flush()
                    await db.refresh(question)
                    
                    # Send question to client
                    await websocket.send_json({
                        "type": "question",
                        "index": i + 1,
                        "total": len(questions),
                        "data": {
                            "id": str(question.id),
                            "question_text": question.question_text,
                            "options": question.options,
                            "correct_answer": question.correct_answer,
                            "explanation": question.explanation,
                            "difficulty": question.difficulty,
                            "marks": question.marks,
                            "order_index": question.order_index,
                        }
                    })
                
                # Update quiz as AI generated
                await quiz_repo.update(
                    db,
                    db_quiz=quiz,
                    update_data={"is_ai_generated": True},
                )
                await db.commit()
                
                # Send done message
                await websocket.send_json({
                    "type": "done",
                    "total": len(questions)
                })
                
            except ValueError as e:
                await websocket.send_json({
                    "type": "error",
                    "content": str(e)
                })
            except Exception as e:
                logger.error(f"Error generating questions: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Failed to generate questions: {str(e)}"
                })
                
    except WebSocketDisconnect:
        # Client disconnected normally
        pass
    except Exception as e:
        logger.error(f"WebSocket error in quiz generation: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": str(e)
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


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
