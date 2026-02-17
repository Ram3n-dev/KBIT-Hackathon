import asyncio

from sqlalchemy.exc import SQLAlchemyError
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    future=True,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    last_error: Exception | None = None
    for attempt in range(1, settings.db_connect_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await conn.run_sync(Base.metadata.create_all)
            return
        except SQLAlchemyError as exc:
            last_error = exc
            if attempt >= settings.db_connect_retries:
                break
            await asyncio.sleep(settings.db_connect_retry_delay_seconds)

    raise RuntimeError(
        "Не удалось подключиться к PostgreSQL или инициализировать pgvector. "
        "Проверьте DATABASE_URL, доступность БД и наличие расширения vector."
    ) from last_error


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
