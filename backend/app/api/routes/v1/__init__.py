"""API v1 router aggregation."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from fastapi import APIRouter

from app.api.routes.v1 import health
from app.api.routes.v1 import auth, users
from app.api.routes.v1 import oauth
from app.api.routes.v1 import sessions
from app.api.routes.v1 import ws

# Feature 1: Resource Library
from app.api.routes.v1 import subjects, resources, notes, bookmarks

# Feature 2: Quiz Engine
from app.api.routes.v1 import quizzes, attempts

# Feature 3: Study Room
from app.api.routes.v1 import rooms, study_sessions, goals

v1_router = APIRouter()

# Health check routes (no auth required)
v1_router.include_router(health.router, tags=["health"])

# Authentication routes
v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# User routes
v1_router.include_router(users.router, prefix="/users", tags=["users"])

# OAuth2 routes
v1_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])

# Session management routes
v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])

# WebSocket routes
v1_router.include_router(ws.router, tags=["websocket"])

# Feature 1: Resource Library routes
v1_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
v1_router.include_router(resources.router, prefix="/resources", tags=["resources"])
v1_router.include_router(notes.router, prefix="/notes", tags=["notes"])
v1_router.include_router(bookmarks.router, prefix="/bookmarks", tags=["bookmarks"])

# Feature 2: Quiz Engine routes
v1_router.include_router(quizzes.router, prefix="/quizzes", tags=["quizzes"])
v1_router.include_router(attempts.router, prefix="/attempts", tags=["attempts"])

# Feature 3: Study Room routes
v1_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
v1_router.include_router(study_sessions.router, prefix="/study-sessions", tags=["study-sessions"])
v1_router.include_router(goals.router, prefix="/goals", tags=["goals"])
