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
                # Lightweight schema migration for per-user worlds on existing DBs.
                await conn.execute(text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS user_id INTEGER"))
                await conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS user_id INTEGER"))
                await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS user_id INTEGER"))
                await conn.execute(text("ALTER TABLE simulation_state ADD COLUMN IF NOT EXISTS user_id INTEGER"))
                await conn.execute(text("DELETE FROM simulation_state WHERE user_id IS NULL"))
                await conn.execute(text("ALTER TABLE simulation_state ALTER COLUMN id DROP DEFAULT"))
                await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS simulation_state_id_seq"))
                await conn.execute(
                    text(
                        "ALTER TABLE simulation_state ALTER COLUMN id "
                        "SET DEFAULT nextval('simulation_state_id_seq')"
                    )
                )
                await conn.execute(
                    text(
                        "SELECT setval('simulation_state_id_seq', "
                        "COALESCE((SELECT MAX(id) FROM simulation_state), 1), true)"
                    )
                )
                await conn.execute(
                    text("CREATE UNIQUE INDEX IF NOT EXISTS ix_simulation_state_user_id ON simulation_state (user_id)")
                )
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_agents_user_id ON agents (user_id)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_user_id ON events (user_id)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_chat_messages_user_id ON chat_messages (user_id)"))
                await conn.execute(text("ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_name_key"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_agents_user_name ON agents (user_id, name)"))
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
