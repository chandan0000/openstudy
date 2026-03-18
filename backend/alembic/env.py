"""Alembic migration environment."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base

# Import all models here to ensure they are registered with metadata
from app.db.models.user import User  # noqa: F401
from app.db.models.session import Session  # noqa: F401
from app.db.models.room import Room  # noqa: F401
from app.db.models.room_member import RoomMember  # noqa: F401
from app.db.models.study_session import StudySession  # noqa: F401
from app.db.models.daily_goal import DailyGoal  # noqa: F401

# Feature 1: Resource Library models
from app.db.models.subject import Subject  # noqa: F401
from app.db.models.resource import Resource  # noqa: F401
from app.db.models.note import Note  # noqa: F401
from app.db.models.bookmark import Bookmark  # noqa: F401
from app.db.models.qa_session import QASession  # noqa: F401

# Feature 2: Quiz Engine models
from app.db.models.quiz import Quiz  # noqa: F401
from app.db.models.question import Question  # noqa: F401
from app.db.models.attempt import Attempt  # noqa: F401
from app.db.models.leaderboard import Leaderboard  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from settings."""
    return settings.DATABASE_URL_SYNC


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
