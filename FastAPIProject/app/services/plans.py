from __future__ import annotations

import re

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plan


def normalize_plan_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def compact_plan_text(raw_text: str, fallback: str, max_len: int = 220) -> str:
    text = normalize_plan_text(raw_text)
    if not text:
        text = normalize_plan_text(fallback)

    # If LLM returned a multi-item list, keep only the first actionable item.
    if re.search(r"(?:^|\s)1\.\s+", text):
        m = re.search(r"(?:^|\s)1\.\s*(.+?)(?=(?:\s+\d\.\s+)|$)", text)
        if m:
            text = normalize_plan_text(m.group(1))

    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


async def set_current_plan(session: AsyncSession, agent_id: int, text: str) -> Plan:
    normalized = normalize_plan_text(text)
    latest_active = await session.scalar(
        select(Plan)
        .where(Plan.agent_id == agent_id, Plan.active.is_(True))
        .order_by(Plan.created_at.desc())
        .limit(1)
    )
    if latest_active and normalize_plan_text(latest_active.text) == normalized:
        return latest_active

    await session.execute(update(Plan).where(Plan.agent_id == agent_id, Plan.active.is_(True)).values(active=False))
    row = Plan(agent_id=agent_id, text=normalized, active=True)
    session.add(row)
    await session.flush()
    return row

