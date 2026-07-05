from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (create_async_engine,async_sessionmaker,AsyncSession,)
from core.settings import settings

# ENGINE
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,

    # Connection pool
    connect_args={"statement_cache_size": 0},
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=1800,
)

# SESSION FACTORY
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# FASTAPI DEPENDENCY
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()