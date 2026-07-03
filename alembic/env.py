from logging.config import fileConfig

from core.settings import settings
from core.db.base import Base
from alembic import context

from sqlalchemy import pool
from sqlalchemy import create_engine

# import models EXAMPLE

from modules.course_management.infrastructure.models import CourseModel
from modules.gamification.infrastructure.models import AchievementModel, UserAchievementModel
from modules.iam.infrastructure.models.user_model import UserModel
from modules.quiz_generation.infrastructure.models.answer_model import AnswerModel
from modules.quiz_generation.infrastructure.models.question_model import QuestionModel
from modules.quiz_generation.infrastructure.models.quiz_model import QuizModel
from modules.quiz_management.infrastructure.models import (
    QuestionAttemptModel,
    QuizAttemptModel,
    QuizSourceDocumentModel,
)
from modules.analytics.infrastructure.models import BloomStatsModel, CourseStatsModel
from modules.content_processing.infrastructure.models.content_document_model import ContentDocumentModel
from modules.content_processing.infrastructure.models.document_chunk_model import DocumentChunkModel
from modules.bloom_taxonomy.infrastructure.models import BloomLevelModel
##from modules.course.infrastructure.models import Course
from modules.content_processing.infrastructure.models.content_document_model import ContentDocumentModel

# ALEMBIC CONFIG
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DATABASE  URL FROM SETTINGS.PY
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("+asyncpg", "")
)

# METADATA
# It compares the python models with the real database
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    # Run migrations in 'offline' mode.
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Run migrations in 'online' mode.
    connectable = create_engine(
        settings.DATABASE_URL_SYNC,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
