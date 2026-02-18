from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Memory
from app.services.embedding import embed_text
from app.services.llm import get_llm_service


settings = get_settings()
llm_service = get_llm_service()


async def add_memory(session: AsyncSession, agent_id: int, content: str, source: str = "event") -> Memory:
    # Cap memory size to prevent recursive memory inflation and token blowups.
    content = _clip(content.strip(), 480)
    memory = Memory(
        agent_id=agent_id,
        content=content,
        source=source,
        embedding=embed_text(content),
    )
    session.add(memory)
    await session.flush()
    await summarize_if_needed(session, agent_id)
    return memory


async def summarize_if_needed(session: AsyncSession, agent_id: int) -> None:
    count_stmt = select(func.count()).select_from(Memory).where(
        Memory.agent_id == agent_id,
        Memory.summarized.is_(False),
    )
    count_unsummarized = await session.scalar(count_stmt) or 0
    if count_unsummarized <= settings.memory_context_limit:
        return

    oldest_stmt = (
        select(Memory)
        .where(Memory.agent_id == agent_id, Memory.summarized.is_(False))
        .order_by(Memory.created_at.asc())
        .limit(settings.summary_batch_size)
    )
    oldest = list((await session.scalars(oldest_stmt)).all())
    if not oldest:
        return

    llm_summary = await llm_service.summarize_memories([m.content for m in oldest])
    summary_text = llm_summary or _build_summary(oldest)
    for item in oldest:
        item.summarized = True
    session.add(
        Memory(
            agent_id=agent_id,
            source="summary",
            content=summary_text,
            embedding=embed_text(summary_text),
            summarized=False,
        )
    )


def _build_summary(memories: list[Memory]) -> str:
    snippets = [m.content.strip() for m in memories[:5] if m.content.strip()]
    if not snippets:
        return "Ключевые воспоминания были обобщены."
    return "Сводка прошлых событий: " + "; ".join(snippets) + "."


async def retrieve_relevant_memories(
    session: AsyncSession,
    agent_id: int,
    query: str,
    k: int = 5,
) -> list[str]:
    query_vector = embed_text(query)
    stmt_main = (
        select(Memory)
        .where(Memory.agent_id == agent_id, Memory.source != "summary")
        .order_by(Memory.embedding.cosine_distance(query_vector))
        .limit(k)
    )
    rows = list((await session.scalars(stmt_main)).all())

    # Keep one freshest summary if it exists, but avoid summary-of-summary cascades.
    stmt_summary = (
        select(Memory)
        .where(Memory.agent_id == agent_id, Memory.source == "summary")
        .order_by(Memory.created_at.desc())
        .limit(1)
    )
    latest_summary = await session.scalar(stmt_summary)
    result = [row.content for row in rows]
    if latest_summary:
        result.append(latest_summary.content)
    return result[:k]


def _clip(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]
