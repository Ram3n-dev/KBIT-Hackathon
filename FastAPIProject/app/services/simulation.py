import asyncio
import logging
import random
import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Agent, ChatMessage, Event, Memory, Relationship, SimulationState
from app.realtime import EventBus, WsHub
from app.services.llm import get_llm_service
from app.services.memory import add_memory, retrieve_relevant_memories
from app.services.plans import compact_plan_text, normalize_plan_text, set_current_plan


settings = get_settings()
logger = logging.getLogger("app.sim")

MOODS = [
    ("Радостный", "😄", "#4CAF50", 0.85),
    ("Воодушевленный", "✨", "#8BC34A", 0.75),
    ("Спокоен", "😐", "#FFC107", 0.50),
    ("Тревожный", "😟", "#FF9800", 0.30),
    ("Раздражен", "😠", "#F44336", 0.12),
]

NEUTRAL_TOPICS = [
    "как распределить задачи на сегодня",
    "какой следующий шаг у команды",
    "что мешает продвинуться быстрее",
    "как улучшить взаимодействие между нами",
]

BAD_PATTERNS = [
    "после того что произошло",
    "это важно",
    "давай обсудим",
    "у меня мысль по поводу",
]

SAFE_FALLBACKS = [
    "Я за то, чтобы сейчас выбрать один конкретный следующий шаг и закрепить его.",
    "Давай не распыляться: определим приоритет на ближайший час и двинемся по нему.",
    "Предлагаю коротко синхронизироваться и договориться, кто что делает дальше.",
]
CHAT_DB_MAX_LEN = 120


@dataclass
class ConversationState:
    topic: str
    remaining_turns: int


class SimulationEngine:
    def __init__(self, event_bus: EventBus, ws_hub: WsHub) -> None:
        self._event_bus = event_bus
        self._ws_hub = ws_hub
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._llm = get_llm_service()
        self._last_step_llm_at: dict[int, datetime] = {}
        self._last_dialogue_llm_at: dict[int, datetime] = {}
        self._last_sent_at: dict[int, datetime] = {}
        self._pending_reply: dict[int, int] = {}
        self._pair_topics: dict[tuple[int, int], ConversationState] = {}
        self._running = True

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    def set_running(self, running: bool) -> None:
        self._running = running

    def is_running(self) -> bool:
        return self._running

    async def _run(self) -> None:
        while not self._stop.is_set():
            if not self._running:
                await asyncio.sleep(0.5)
                continue
            try:
                await self._tick()
            except Exception as exc:
                logger.exception("tick error: %s", exc)
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
            by_id = {a.id: a for a in agents}

            pair = self._pick_actor_target(by_id)
            if not pair:
                return
            actor, target = pair

            if self._is_agent_on_cooldown(actor.id):
                return

            rel = await _get_or_create_relation(session, actor.id, target.id)
            if random.random() > max(0.10, rel.score * 0.60):
                return

            memories = await retrieve_relevant_memories(session, actor.id, f"{target.name} диалог", k=3)
            llm_step = None
            if self._can_use_llm(self._last_step_llm_at, actor.id):
                llm_step = await self._llm.generate_agent_step(
                    actor_name=actor.name,
                    actor_personality=actor.personality,
                    actor_mood=actor.mood_text,
                    target_name=target.name,
                    memories=memories,
                )
                if llm_step:
                    self._last_step_llm_at[actor.id] = datetime.utcnow()

            latest_event = await _latest_user_event(session, actor.created_at)
            force_event_reaction = bool(latest_event and not await _has_agent_reacted_to_event(session, actor.id, latest_event.id))
            topic = self._select_topic(actor, target, latest_event.text if latest_event else None, force_event_reaction)
            topic_db = _db_fit(topic, CHAT_DB_MAX_LEN)

            recent_chat = await _recent_chat_context(session, actor.id, target.id)
            llm_chat = None
            if self._can_use_llm(self._last_dialogue_llm_at, actor.id):
                llm_chat = await self._llm.generate_dialogue_message(
                    actor_name=actor.name,
                    actor_personality=actor.personality,
                    actor_mood=actor.mood_text,
                    target_name=target.name,
                    topic=topic,
                    recent_messages=recent_chat,
                )
                if llm_chat:
                    self._last_dialogue_llm_at[actor.id] = datetime.utcnow()

            chat_text = _clean_message(llm_chat or "")
            if not _is_quality_message(chat_text):
                retry_prompt = f"{topic}. Сформулируй иначе: без шаблонов, без повторов, с конкретным шагом."
                retry = await self._llm.generate_dialogue_message(
                    actor_name=actor.name,
                    actor_personality=actor.personality,
                    actor_mood=actor.mood_text,
                    target_name=target.name,
                    topic=retry_prompt,
                    recent_messages=recent_chat,
                )
                chat_text = _clean_message(retry or "")

            if not _is_quality_message(chat_text):
                chat_text = random.choice(SAFE_FALLBACKS)
            chat_text_db = _db_fit(chat_text, CHAT_DB_MAX_LEN)

            if await _is_duplicate_chat(session, actor.id, target.id, chat_text_db):
                logger.info("drop: duplicate sender=%s receiver=%s", actor.id, target.id)
                return
            if await _is_repetitive_chat(session, actor.id, chat_text_db):
                logger.info("drop: repetitive sender=%s", actor.id)
                return

            default_plan = _build_default_plan(target.name, topic)
            plan_text = compact_plan_text((llm_step or {}).get("plan") or "", fallback=default_plan)
            relation_delta = (llm_step or {}).get("relation_delta", random.uniform(-0.03, 0.06))
            try:
                relation_delta = float(relation_delta)
            except Exception:
                relation_delta = random.uniform(-0.03, 0.06)

            event_text = f"{actor.name} скорректировал(а) план после диалога с {target.name}."
            actor.reflection = (llm_step or {}).get("reflection") or (
                f"Я веду разговор с {target.name} по теме '{topic}' и держу фокус на конкретных шагах."
            )
            actor.current_plan = plan_text
            await set_current_plan(session, actor.id, plan_text)

            rel.score = max(0.0, min(1.0, rel.score + relation_delta))
            mood = _mood_from_relation(rel.score)
            actor.mood_text, actor.mood_emoji, actor.mood_color, actor.mood_score = mood

            event = Event(text=event_text, event_type="agent_action")
            chat_msg = ChatMessage(
                sender_type="agent",
                sender_agent_id=actor.id,
                receiver_agent_id=target.id,
                text=chat_text_db,
                topic=topic_db,
            )
            session.add(event)
            session.add(chat_msg)

            await add_memory(session, actor.id, f"Я написал {target.name}: {chat_text_db}", source="chat")
            await add_memory(session, target.id, f"{actor.name} написал мне: {chat_text_db}", source="chat")
            await add_memory(session, actor.id, event_text, source="agent_action")
            if force_event_reaction and latest_event:
                await add_memory(
                    session,
                    actor.id,
                    f"Я отреагировал на событие: {latest_event.text}",
                    source=f"evt_rx_{latest_event.id}",
                )

            await session.commit()
            self._mark_turn(actor.id, target.id)

            payload_event = {
                "type": "event",
                "event_id": event.id,
                "text": event.text,
                "event_type": event.event_type,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            payload_chat = {
                "type": "chat_message",
                "id": chat_msg.id,
                "sender_type": "agent",
                "sender_agent_id": actor.id,
                "sender_name": actor.name,
                "receiver_agent_id": target.id,
                "receiver_name": target.name,
                "text": chat_text_db,
                "topic": topic_db,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            await self._event_bus.publish(payload_event)
            await self._event_bus.publish(payload_chat)
            await self._ws_hub.broadcast(payload_event)
            await self._ws_hub.broadcast(payload_chat)

    def _pick_actor_target(self, by_id: dict[int, Agent]) -> tuple[Agent, Agent] | None:
        pending_candidates = [aid for aid in self._pending_reply if aid in by_id and self._pending_reply[aid] in by_id]
        if pending_candidates and random.random() < 0.75:
            actor_id = random.choice(pending_candidates)
            target_id = self._pending_reply.pop(actor_id)
            if actor_id != target_id:
                return by_id[actor_id], by_id[target_id]

        agents = list(by_id.values())
        actor = random.choice(agents)
        others = [a for a in agents if a.id != actor.id]
        if not others:
            return None
        return actor, random.choice(others)

    def _select_topic(self, actor: Agent, target: Agent, latest_event_text: str | None, force_event: bool) -> str:
        key = tuple(sorted((actor.id, target.id)))
        state = self._pair_topics.get(key)

        if force_event and latest_event_text:
            topic = latest_event_text
            self._pair_topics[key] = ConversationState(topic=topic, remaining_turns=random.randint(3, 5))
            return topic

        if state and state.remaining_turns > 0:
            state.remaining_turns -= 1
            return state.topic

        if actor.current_plan and actor.current_plan.strip():
            topic = actor.current_plan.strip()
        elif latest_event_text and random.random() < 0.30:
            topic = latest_event_text
        else:
            topic = random.choice(NEUTRAL_TOPICS)

        self._pair_topics[key] = ConversationState(topic=topic, remaining_turns=random.randint(2, 4))
        return topic

    def _mark_turn(self, actor_id: int, target_id: int) -> None:
        self._last_sent_at[actor_id] = datetime.utcnow()
        self._pending_reply[target_id] = actor_id

    def _is_agent_on_cooldown(self, agent_id: int) -> bool:
        last = self._last_sent_at.get(agent_id)
        if not last:
            return False
        return (datetime.utcnow() - last).total_seconds() < 8

    def _can_use_llm(self, store: dict[int, datetime], agent_id: int) -> bool:
        last = store.get(agent_id)
        if not last:
            return True
        return (datetime.utcnow() - last).total_seconds() >= max(8, settings.llm_agent_cooldown_seconds // 2)


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


async def _recent_chat_context(session, agent_a_id: int, agent_b_id: int) -> list[str]:
    stmt = (
        select(ChatMessage)
        .where(
            ((ChatMessage.sender_agent_id == agent_a_id) & (ChatMessage.receiver_agent_id == agent_b_id))
            | ((ChatMessage.sender_agent_id == agent_b_id) & (ChatMessage.receiver_agent_id == agent_a_id))
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    rows = list((await session.scalars(stmt)).all())
    rows.reverse()
    return [f"{'agent:'+str(r.sender_agent_id) if r.sender_agent_id else r.sender_type}: {r.text}" for r in rows]


async def _is_duplicate_chat(session, sender_id: int, receiver_id: int, text: str) -> bool:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.sender_agent_id == sender_id, ChatMessage.receiver_agent_id == receiver_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )
    last = await session.scalar(stmt)
    if not last:
        return False
    return _normalize_text(text) == _normalize_text(last.text or "")


async def _is_repetitive_chat(session, sender_id: int, text: str) -> bool:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.sender_agent_id == sender_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(4)
    )
    rows = list((await session.scalars(stmt)).all())
    if not rows:
        return False

    new_text = _normalize_text(text)
    new_tokens = set(new_text.split())
    if len(new_tokens) < 4:
        return True

    for row in rows:
        old_text = _normalize_text(row.text or "")
        old_tokens = set(old_text.split())
        if not old_tokens:
            continue
        if new_text == old_text:
            return True
        overlap = len(new_tokens & old_tokens) / max(1, len(new_tokens | old_tokens))
        if overlap >= 0.90:
            return True
    return False


async def _latest_user_event(session, not_before: datetime | None = None) -> Event | None:
    stmt = (
        select(Event)
        .where(Event.event_type == "user_event")
        .order_by(Event.created_at.desc())
        .limit(1)
    )
    latest = await session.scalar(stmt)
    if not latest:
        return None
    if not_before is not None and latest.created_at < not_before:
        return None

    created_at = latest.created_at
    if created_at.tzinfo is not None:
        created_at = created_at.replace(tzinfo=None)

    age_seconds = (datetime.utcnow() - created_at).total_seconds()
    if age_seconds > 10 * 60:
        return None
    return latest


async def _has_agent_reacted_to_event(session, agent_id: int, event_id: int) -> bool:
    marker = f"evt_rx_{event_id}"
    stmt = select(Memory.id).where(Memory.agent_id == agent_id, Memory.source == marker).limit(1)
    row = await session.scalar(stmt)
    return row is not None


def _clean_message(text: str) -> str:
    return " ".join((text or "").strip().split()).replace("\n", " ").replace("\r", " ")


def _is_quality_message(text: str) -> bool:
    norm = _normalize_text(text)
    if not norm:
        return False
    if len(norm) < 12 or len(norm) > 320:
        return False

    for p in BAD_PATTERNS:
        if p in norm:
            return False

    tokens = norm.split()
    unique_ratio = len(set(tokens)) / max(1, len(tokens))
    if unique_ratio < 0.35:
        return False

    sentence_marks = text.count(".") + text.count("!") + text.count("?")
    if sentence_marks > 4:
        return False
    return True


def _normalize_text(text: str) -> str:
    t = text.lower().replace("ё", "е")
    t = re.sub(r"[^a-zа-я0-9\s]", " ", t)
    return " ".join(t.split())


def _db_fit(text: str | None, max_len: int) -> str | None:
    if text is None:
        return None
    value = text.strip()
    if len(value) <= max_len:
        return value
    return value[: max_len - 1].rstrip() + "…"


def _build_default_plan(target_name: str, topic: str) -> str:
    normalized_topic = normalize_plan_text(topic).strip(" .")
    if not normalized_topic:
        return f"Согласовать с {target_name} следующий практический шаг."
    if normalized_topic.lower().startswith("согласовать с"):
        return normalized_topic if normalized_topic.endswith(".") else f"{normalized_topic}."
    return f"Согласовать с {target_name} следующий практический шаг по теме '{normalized_topic}'."


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
