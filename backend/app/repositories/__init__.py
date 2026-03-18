"""Repository layer for database operations."""
# ruff: noqa: I001, RUF022 - Imports structured for Jinja2 template conditionals

from app.repositories import user as user_repo
from app.repositories import session as session_repo
from app.repositories import subject as subject_repo
from app.repositories import resource as resource_repo
from app.repositories import note as note_repo
from app.repositories import bookmark as bookmark_repo
from app.repositories import qa_session as qa_session_repo
from app.repositories import quiz as quiz_repo
from app.repositories import question as question_repo
from app.repositories import attempt as attempt_repo
from app.repositories import leaderboard as leaderboard_repo
from app.repositories import room as room_repo
from app.repositories import room_member as room_member_repo
from app.repositories import study_session as study_session_repo
from app.repositories import daily_goal as daily_goal_repo

__all__ = [
    "user_repo",
    "session_repo",
    "subject_repo",
    "resource_repo",
    "note_repo",
    "bookmark_repo",
    "qa_session_repo",
    "quiz_repo",
    "question_repo",
    "attempt_repo",
    "leaderboard_repo",
    "room_repo",
    "room_member_repo",
    "study_session_repo",
    "daily_goal_repo",
]
