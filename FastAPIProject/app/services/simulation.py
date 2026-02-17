import asyncio
import random
from datetime import datetime

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Agent, Event, Plan, Relationship, SimulationState
from app.realtime import EventBus, WsHub
from app.services.llm import get_llm_service
from app.services.memory import add_memory, retrieve_relevant_memories


settings = get_settings()

MOODS = [
    ("Радостный", "😄", "#4CAF50", 0.85),
    ("Воодушевленный", "✨", "#8BC34A", 0.75),
    ("Спокоен", "😐", "#FFC107", 0.50),
    ("Тревожный", "😟", "#FF9800", 0.30),
    ("Раздражен", "😠", "#F44336", 0.12),
]

PLANS = [
    "Исследовать новое место",
    "Поговорить с соседом",
    "Осмыслить недавнее событие",
    "Помочь другому агенту",
    "Спланировать совместный проект",
]

ACTIONS = [
    "обсудил идею",
    "предложил сотрудничество",
    "вспомнил важный момент",
    "высказал сомнение",
    "похвалил товарища",
]


class SimulationEngine:
    def __init__(self, event_bus: EventBus, ws_hub: WsHub) -> None:
        self._event_bus = event_bus
        self._ws_hub = ws_hub
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._llm = get_llm_service()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception:
                await asyncio.sleep(1.0)

            speed = await self._get_speed()
            sleep_time = max(1.0, settings.simulation_tick_seconds / max(speed, 0.1))
            await asyncio.sleep(sleep_time)

    async def _get_speed(self) -> float:
        async with SessionLocal() as session:
            state = await session.get(SimulationState, 1)
            return state.speed if state else 1.0

    async def _tick(self) -> None:
        async with SessionLocal() as session:
            agents = list((await session.scalars(select(Agent).order_by(Agent.id.asc()))).all())
            if len(agents) < 2:
                return

            actor = random.choice(agents)
            others = [a for a in agents if a.id != actor.id]
            target = random.choice(others)

            memories = await retrieve_relevant_memories(session, actor.id, f"{target.name} общение", k=3)
            reflective_hint = f" Вспоминает: {memories[0]}" if memories else ""

            llm_step = await self._llm.generate_agent_step(
                actor_name=actor.name,
                actor_personality=actor.personality,
                actor_mood=actor.mood_text,
                target_name=target.name,
                memories=memories,
            )

            plan_text = (llm_step or {}).get("plan") or random.choice(PLANS)
            action = (llm_step or {}).get("action") or random.choice(ACTIONS)
            relation_delta = (llm_step or {}).get("relation_delta", random.uniform(-0.08, 0.12))
            try:
                relation_delta = float(relation_delta)
            except Exception:
                relation_delta = random.uniform(-0.08, 0.12)

            event_text = f"{actor.name} {action} с {target.name}.{reflective_hint}"

            actor.reflection = (llm_step or {}).get("reflection") or (
                f"Я думаю о {target.name} и хочу действовать осмысленно. "
                f"Последняя мысль: {event_text[:120]}"
            )
            actor.current_plan = plan_text
            session.add(Plan(agent_id=actor.id, text=plan_text, active=True))

            rel = await _get_or_create_relation(session, actor.id, target.id)
            rel.score = max(0.0, min(1.0, rel.score + relation_delta))

            mood = _mood_from_relation(rel.score)
            actor.mood_text, actor.mood_emoji, actor.mood_color, actor.mood_score = mood

            event = Event(text=event_text, event_type="agent_action")
            session.add(event)
            await add_memory(session, actor.id, event_text, source="agent_action")
            await add_memory(session, target.id, f"{actor.name}: {event_text}", source="social")
            await session.commit()

            payload = {
                "type": "event",
                "event_id": event.id,
                "text": event.text,
                "event_type": event.event_type,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            await self._event_bus.publish(payload)
            await self._ws_hub.broadcast(payload)


async def _get_or_create_relation(session, source_id: int, target_id: int) -> Relationship:
    stmt = select(Relationship).where(
        Relationship.source_agent_id == source_id,
        Relationship.target_agent_id == target_id,
    )
    rel = await session.scalar(stmt)
    if rel:
        return rel
    rel = Relationship(source_agent_id=source_id, target_agent_id=target_id, score=0.5)
    session.add(rel)
    await session.flush()
    return rel


def _mood_from_relation(score: float) -> tuple[str, str, str, float]:
    if score >= 0.75:
        return MOODS[0]
    if score >= 0.62:
        return MOODS[1]
    if score >= 0.38:
        return MOODS[2]
    if score >= 0.2:
        return MOODS[3]
    return MOODS[4]
