from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
import json

from fastapi import Depends, FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, init_db, SessionLocal
from app.models import Agent, Event, Message, Plan, Relationship, SimulationState
from app.realtime import EventBus, WsHub
from app.schemas import (
    AgentCreate,
    AgentOut,
    AgentRelationOut,
    EventCreate,
    LLMConfigPatch,
    LLMProviderInfoOut,
    LLMStatusOut,
    LLMTestOut,
    MessageCreate,
    MoodOut,
    PlanOut,
    TimeSpeedIn,
    TimeSpeedOut,
)
from app.services.memory import add_memory, retrieve_relevant_memories
from app.services.llm import get_llm_service
from app.services.simulation import SimulationEngine


settings = get_settings()
event_bus = EventBus()
ws_hub = WsHub()
sim_engine = SimulationEngine(event_bus, ws_hub)
llm_service = get_llm_service()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await seed_initial_data()
    await sim_engine.start()
    try:
        yield
    finally:
        await sim_engine.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    return {"service": settings.app_name, "status": "ok"}


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(select(func.now()))
    return {"status": "healthy"}


@app.get("/llm/status", response_model=LLMStatusOut)
async def llm_status() -> LLMStatusOut:
    return LLMStatusOut(**llm_service.get_status())


@app.get("/llm/providers", response_model=list[LLMProviderInfoOut])
async def llm_providers() -> list[LLMProviderInfoOut]:
    return [LLMProviderInfoOut(**item) for item in llm_service.list_providers()]


@app.patch("/llm/config", response_model=LLMStatusOut)
async def llm_config_patch(payload: LLMConfigPatch) -> LLMStatusOut:
    llm_service.update_runtime(**payload.model_dump(exclude_unset=True))
    return LLMStatusOut(**llm_service.get_status())


@app.post("/llm/test", response_model=LLMTestOut)
async def llm_test() -> LLMTestOut:
    result = await llm_service.test_connection()
    return LLMTestOut(**result)


@app.get("/agents", response_model=list[AgentOut])
async def get_agents(db: AsyncSession = Depends(get_db)) -> list[AgentOut]:
    agents = list((await db.scalars(select(Agent).order_by(Agent.id.asc()))).all())
    return [AgentOut.model_validate(a) for a in agents]


@app.post("/agents", response_model=AgentOut)
async def create_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)) -> AgentOut:
    exists = await db.scalar(select(Agent).where(Agent.name == payload.name.strip()))
    if exists:
        raise HTTPException(status_code=400, detail="Агент с таким именем уже существует")

    agent = Agent(
        name=payload.name.strip(),
        avatar=payload.avatar,
        avatar_color=payload.avatarColor,
        avatar_name=payload.avatarName,
        personality=payload.personality or "Новый агент с уникальным взглядом на мир.",
    )
    db.add(agent)
    await db.flush()
    db.add(Plan(agent_id=agent.id, text="Осмотреться и познакомиться с окружающими", active=True))
    await add_memory(db, agent.id, f"Я появился в мире под именем {agent.name}.", source="birth")
    await ensure_relations_for_agent(db, agent.id)
    await db.commit()
    await db.refresh(agent)
    return AgentOut.model_validate(agent)


@app.get("/agents/{agent_id}", response_model=AgentOut)
async def get_agent_by_id(agent_id: int, db: AsyncSession = Depends(get_db)) -> AgentOut:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    return AgentOut.model_validate(agent)


@app.get("/relations")
async def get_relations(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = list((await db.scalars(select(Relationship))).all())
    return [{"from": r.source_agent_id, "to": r.target_agent_id, "value": round(r.score, 3)} for r in rows]


@app.get("/agents/{agent_id}/relations", response_model=list[AgentRelationOut])
async def get_agent_relations(agent_id: int, db: AsyncSession = Depends(get_db)) -> list[AgentRelationOut]:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")

    rows = list(
        (
            await db.execute(
                select(Relationship, Agent.name)
                .join(Agent, Agent.id == Relationship.target_agent_id)
                .where(Relationship.source_agent_id == agent_id)
                .order_by(Relationship.score.desc())
            )
        ).all()
    )
    result: list[AgentRelationOut] = []
    for rel, target_name in rows:
        relation_type, color = relation_label(rel.score)
        result.append(
            AgentRelationOut(
                id=rel.id,
                target_name=target_name,
                type=relation_type,
                color=color,
                score=round(rel.score, 3),
            )
        )
    return result


@app.get("/agents/{agent_id}/mood", response_model=MoodOut)
async def get_agent_mood(agent_id: int, db: AsyncSession = Depends(get_db)) -> MoodOut:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    return MoodOut(text=agent.mood_text, emoji=agent.mood_emoji, color=agent.mood_color, score=agent.mood_score)


@app.get("/agents/{agent_id}/plans", response_model=list[PlanOut])
async def get_agent_plans(agent_id: int, db: AsyncSession = Depends(get_db)) -> list[PlanOut]:
    plans = list(
        (
            await db.scalars(
                select(Plan)
                .where(Plan.agent_id == agent_id, Plan.active.is_(True))
                .order_by(Plan.created_at.desc())
                .limit(5)
            )
        ).all()
    )
    return [PlanOut(text=p.text) for p in plans]


@app.get("/agents/{agent_id}/reflection")
async def get_agent_reflection(agent_id: int, db: AsyncSession = Depends(get_db)) -> str:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    memories = await retrieve_relevant_memories(db, agent_id, "последние мысли", k=2)
    if memories:
        return f"{agent.reflection} Ключевое воспоминание: {memories[0]}"
    return agent.reflection


@app.post("/events")
async def create_event(payload: EventCreate, db: AsyncSession = Depends(get_db)) -> dict:
    event = Event(text=payload.text.strip(), event_type="user_event")
    db.add(event)
    agents = list((await db.scalars(select(Agent))).all())
    for agent in agents:
        await add_memory(db, agent.id, f"Событие мира: {payload.text}", source="world")
        agent.reflection = f"Произошло важное событие: {payload.text}. Нужно переосмыслить действия."
        agent.current_plan = "Адаптироваться к новому событию"
    await db.commit()

    response = {"id": event.id, "text": event.text, "event_type": event.event_type}
    payload_out = {
        "type": "event",
        "event_id": event.id,
        "text": event.text,
        "event_type": event.event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    await event_bus.publish(payload_out)
    await ws_hub.broadcast(payload_out)
    return response


@app.post("/messages")
async def send_message(payload: MessageCreate, db: AsyncSession = Depends(get_db)) -> dict:
    agent = await db.get(Agent, payload.agentId)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")

    msg = Message(sender="user", agent_id=payload.agentId, text=payload.text.strip())
    db.add(msg)
    await add_memory(db, payload.agentId, f"Пользователь сказал: {payload.text}", source="user_message")
    agent.reflection = f"Пользователь написал мне: '{payload.text}'. Стоит ответить с учетом настроения."
    await db.commit()

    payload_out = {
        "type": "message",
        "agent_id": payload.agentId,
        "text": payload.text.strip(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    await event_bus.publish(payload_out)
    await ws_hub.broadcast(payload_out)
    return {"status": "ok", "agentId": payload.agentId}


@app.post("/time-speed", response_model=TimeSpeedOut)
async def set_time_speed(payload: TimeSpeedIn, db: AsyncSession = Depends(get_db)) -> TimeSpeedOut:
    state = await db.get(SimulationState, 1)
    if not state:
        state = SimulationState(id=1, speed=payload.speed)
        db.add(state)
    else:
        state.speed = payload.speed
    await db.commit()
    return TimeSpeedOut(speed=state.speed)


@app.get("/time-speed", response_model=TimeSpeedOut)
async def get_time_speed(db: AsyncSession = Depends(get_db)) -> TimeSpeedOut:
    state = await db.get(SimulationState, 1)
    if not state:
        state = SimulationState(id=1, speed=1.0)
        db.add(state)
        await db.commit()
    return TimeSpeedOut(speed=state.speed)


@app.get("/events/stream")
async def event_stream() -> StreamingResponse:
    async def gen():
        async for item in event_bus.subscribe():
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.websocket("/ws/events")
async def events_ws(ws: WebSocket):
    await ws_hub.connect(ws)
    try:
        while True:
            # keep connection open; we only push server events
            await ws.receive_text()
    except Exception:
        await ws_hub.disconnect(ws)


async def seed_initial_data() -> None:
    async with SessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(Agent))
        if count and count > 0:
            state = await db.get(SimulationState, 1)
            if not state:
                db.add(SimulationState(id=1, speed=1.0))
                await db.commit()
            return

        seed_agents = [
            Agent(
                name="Астра",
                avatar="🦊",
                avatar_color="#aab97e",
                avatar_name="Лиса",
                personality="Энергичная стратегиня, быстро строит планы и любит командные активности.",
            ),
            Agent(
                name="Бруно",
                avatar="🐶",
                avatar_color="#5d6939",
                avatar_name="Пес",
                personality="Верный и эмпатичный, защищает друзей и стремится к стабильности.",
            ),
            Agent(
                name="Нова",
                avatar="🦉",
                avatar_color="#8b8b7a",
                avatar_name="Сова",
                personality="Наблюдательная, склонна к рефлексии и аналитическим выводам.",
            ),
        ]
        db.add_all(seed_agents)
        await db.flush()

        for agent in seed_agents:
            db.add(Plan(agent_id=agent.id, text="Осмотреть среду и оценить риски", active=True))
            await add_memory(db, agent.id, f"{agent.name} проснулся в новом виртуальном мире.", source="boot")

        for source in seed_agents:
            for target in seed_agents:
                if source.id == target.id:
                    continue
                score = 0.45 if source.id < target.id else 0.55
                db.add(Relationship(source_agent_id=source.id, target_agent_id=target.id, score=score))

        db.add(SimulationState(id=1, speed=1.0))
        db.add(Event(text="Симуляция запущена. Агенты начинают взаимодействовать.", event_type="system"))
        await db.commit()


async def ensure_relations_for_agent(db: AsyncSession, agent_id: int) -> None:
    other_agents = list((await db.scalars(select(Agent).where(Agent.id != agent_id))).all())
    for other in other_agents:
        left = await db.scalar(
            select(Relationship).where(
                Relationship.source_agent_id == agent_id,
                Relationship.target_agent_id == other.id,
            )
        )
        if not left:
            db.add(Relationship(source_agent_id=agent_id, target_agent_id=other.id, score=0.5))
        right = await db.scalar(
            select(Relationship).where(
                Relationship.source_agent_id == other.id,
                Relationship.target_agent_id == agent_id,
            )
        )
        if not right:
            db.add(Relationship(source_agent_id=other.id, target_agent_id=agent_id, score=0.5))


def relation_label(score: float) -> tuple[str, str]:
    if score >= 0.7:
        return ("Симпатия", "#4CAF50")
    if score >= 0.4:
        return ("Нейтралитет", "#FFC107")
    return ("Антипатия", "#F44336")
