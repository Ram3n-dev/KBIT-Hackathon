from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import logging

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import SessionLocal, get_db, init_db
from app.models import Agent, ChatMessage, Event, Message, Plan, Relationship, SimulationState, User
from app.realtime import EventBus, WsHub
from app.schemas import (
    AgentCreate,
    AgentOut,
    AgentRelationOut,
    AgentUpdate,
    AuthLoginIn,
    AuthOut,
    AuthRegisterIn,
    ChatMessageCreate,
    ChatMessageOut,
    EventCreate,
    LLMConfigPatch,
    LLMProviderInfoOut,
    LLMStatusOut,
    LLMTestOut,
    MessageCreate,
    MessageOut,
    MoodOut,
    MoodUpdate,
    PlanCreate,
    PlanOut,
    ReflectionUpdate,
    RelationCreate,
    RelationUpdate,
    SimulationStatusOut,
    TimeSpeedIn,
    TimeSpeedOut,
    UserOut,
)
from app.services.llm import get_llm_service
from app.services.avatars import (
    DEFAULT_AVATAR_FILE,
    avatar_assets_dir,
    get_avatar_catalog,
    get_avatar_meta,
    is_valid_avatar_file,
)
from app.services.memory import add_memory, retrieve_relevant_memories
from app.services.simulation import SimulationEngine


settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.app_log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
event_bus = EventBus()
ws_hub = WsHub()
sim_engine = SimulationEngine(event_bus, ws_hub)
llm_service = get_llm_service()
bearer = HTTPBearer(auto_error=False)
CHAT_DB_MAX_LEN = 120


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
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"message": str(exc.detail)})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else None
    msg = first.get("msg", "Validation error") if first else "Validation error"
    return JSONResponse(status_code=422, content={"message": msg})


@app.get("/")
async def root() -> dict:
    return {"service": settings.app_name, "status": "ok"}


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(select(func.now()))
    return {"status": "healthy"}


@app.post("/auth/register", response_model=AuthOut)
async def auth_register(payload: AuthRegisterIn, db: AsyncSession = Depends(get_db)) -> AuthOut:
    username = payload.username.strip()
    email = payload.email.strip().lower()
    exists = await db.scalar(select(User).where(or_(User.username == username, User.email == email)))
    if exists:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    user = User(
        username=username,
        email=email,
        password_hash=_hash_password(payload.password),
        avatar=DEFAULT_AVATAR_FILE,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = _create_token(user.id)
    return AuthOut(access_token=token, user=UserOut.model_validate(user))


@app.post("/auth/login", response_model=AuthOut)
async def auth_login(payload: AuthLoginIn, db: AsyncSession = Depends(get_db)) -> AuthOut:
    user = await db.scalar(select(User).where(User.username == payload.username.strip()))
    if not user or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверные учетные данные")
    token = _create_token(user.id)
    return AuthOut(access_token=token, user=UserOut.model_validate(user))


@app.get("/auth/profile", response_model=UserOut)
async def auth_profile(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await _get_current_user(credentials, db)
    return UserOut.model_validate(user)


@app.get("/avatars")
async def get_avatars(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    user = await _get_current_user(credentials, db)
    selected = user.avatar if is_valid_avatar_file(user.avatar) else DEFAULT_AVATAR_FILE
    base_url = str(request.base_url).rstrip("/")
    rows: list[dict] = []
    for item in get_avatar_catalog():
        rows.append(
            {
                **item,
                "image": f"{base_url}/avatars/files/{item['file']}",
                "isSelected": item["file"] == selected,
            }
        )
    return rows


@app.get("/avatars/files/{file_name}")
async def get_avatar_file(file_name: str) -> FileResponse:
    if not is_valid_avatar_file(file_name):
        raise HTTPException(status_code=404, detail="Avatar file not found")
    path = avatar_assets_dir() / file_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Avatar file not found")
    return FileResponse(path)


@app.post("/auth/logout")
async def auth_logout() -> dict:
    return {"status": "ok"}


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

    avatar_file = payload.avatarFile if is_valid_avatar_file(payload.avatarFile) else DEFAULT_AVATAR_FILE
    avatar_meta = get_avatar_meta(avatar_file) or {}
    agent = Agent(
        name=payload.name.strip(),
        avatar=avatar_file,
        avatar_color=payload.avatarColor or avatar_meta.get("color", "#4CAF50"),
        avatar_name=payload.avatarName or avatar_meta.get("name", "Agent"),
        personality=payload.personality or "Новый агент с уникальным взглядом на мир.",
    )
    db.add(agent)
    await db.flush()
    db.add(Plan(agent_id=agent.id, text="Осмотреться и познакомиться с окружающими", active=True))
    await add_memory(db, agent.id, f"Я появился в мире под именем {agent.name}.", source="birth")
    greeting = f"Всем привет! Я {agent.name}, рад(а) быть в этом чате."
    chat_greeting = ChatMessage(
        sender_type="agent",
        sender_agent_id=agent.id,
        receiver_agent_id=None,
        text=_db_fit(greeting),
        topic=_db_fit("intro"),
    )
    db.add(chat_greeting)
    await add_memory(db, agent.id, f"Я поприветствовал(а) всех: {greeting}", source="chat")
    await ensure_relations_for_agent(db, agent.id)
    await db.commit()
    await db.refresh(agent)
    payload_chat = {
        "type": "chat_message",
        "id": chat_greeting.id,
        "sender_type": "agent",
        "sender_agent_id": agent.id,
        "sender_name": agent.name,
        "receiver_agent_id": None,
        "receiver_name": None,
        "text": greeting,
        "topic": "intro",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    await event_bus.publish(payload_chat)
    await ws_hub.broadcast(payload_chat)
    return AgentOut.model_validate(agent)


@app.get("/agents/{agent_id}", response_model=AgentOut)
async def get_agent_by_id(agent_id: int, db: AsyncSession = Depends(get_db)) -> AgentOut:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    return AgentOut.model_validate(agent)


@app.put("/agents/{agent_id}", response_model=AgentOut)
async def update_agent(agent_id: int, payload: AgentUpdate, db: AsyncSession = Depends(get_db)) -> AgentOut:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        agent.name = data["name"].strip()
    if "avatarFile" in data and data["avatarFile"] is not None and is_valid_avatar_file(data["avatarFile"]):
        agent.avatar = data["avatarFile"]
        meta = get_avatar_meta(agent.avatar) or {}
        if "avatarColor" not in data:
            agent.avatar_color = meta.get("color", agent.avatar_color)
        if "avatarName" not in data:
            agent.avatar_name = meta.get("name", agent.avatar_name)
    if "avatarColor" in data and data["avatarColor"] is not None:
        agent.avatar_color = data["avatarColor"]
    if "avatarName" in data and data["avatarName"] is not None:
        agent.avatar_name = data["avatarName"]
    if "personality" in data and data["personality"] is not None:
        agent.personality = data["personality"]

    await db.commit()
    await db.refresh(agent)
    return AgentOut.model_validate(agent)


@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    await db.delete(agent)
    await db.commit()
    return {"status": "ok", "deleted_id": agent_id}


@app.get("/relations")
async def get_relations(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = list((await db.scalars(select(Relationship))).all())
    return [{"from": r.source_agent_id, "to": r.target_agent_id, "value": round(r.score, 3)} for r in rows]


@app.post("/relations")
async def create_relation(payload: RelationCreate, db: AsyncSession = Depends(get_db)) -> dict:
    if payload.from_agent_id == payload.to_agent_id:
        raise HTTPException(status_code=400, detail="Нельзя создать связь агента с самим собой")
    rel = await db.scalar(
        select(Relationship).where(
            Relationship.source_agent_id == payload.from_agent_id,
            Relationship.target_agent_id == payload.to_agent_id,
        )
    )
    if rel:
        rel.score = payload.value
    else:
        rel = Relationship(
            source_agent_id=payload.from_agent_id,
            target_agent_id=payload.to_agent_id,
            score=payload.value,
        )
        db.add(rel)
    await db.commit()
    return {"id": rel.id, "from": rel.source_agent_id, "to": rel.target_agent_id, "value": rel.score}


@app.put("/relations/{relation_id}")
async def update_relation(relation_id: int, payload: RelationUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    rel = await db.get(Relationship, relation_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Связь не найдена")
    rel.score = payload.value
    await db.commit()
    return {"id": rel.id, "from": rel.source_agent_id, "to": rel.target_agent_id, "value": rel.score}


@app.delete("/relations/{relation_id}")
async def delete_relation(relation_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    rel = await db.get(Relationship, relation_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Связь не найдена")
    await db.delete(rel)
    await db.commit()
    return {"status": "ok", "deleted_id": relation_id}


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


@app.put("/agents/{agent_id}/mood", response_model=MoodOut)
async def update_agent_mood(agent_id: int, payload: MoodUpdate, db: AsyncSession = Depends(get_db)) -> MoodOut:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")

    data = payload.model_dump(exclude_unset=True)
    if "text" in data and data["text"] is not None:
        agent.mood_text = data["text"]
    if "emoji" in data and data["emoji"] is not None:
        agent.mood_emoji = data["emoji"]
    if "color" in data and data["color"] is not None:
        agent.mood_color = data["color"]
    if "score" in data and data["score"] is not None:
        agent.mood_score = data["score"]

    await db.commit()
    return MoodOut(text=agent.mood_text, emoji=agent.mood_emoji, color=agent.mood_color, score=agent.mood_score)


@app.get("/agents/{agent_id}/plans", response_model=list[PlanOut])
async def get_agent_plans(agent_id: int, db: AsyncSession = Depends(get_db)) -> list[PlanOut]:
    plans = list(
        (
            await db.scalars(
                select(Plan)
                .where(Plan.agent_id == agent_id, Plan.active.is_(True))
                .order_by(Plan.created_at.desc())
                .limit(10)
            )
        ).all()
    )
    return [PlanOut(text=p.text) for p in plans]


@app.post("/agents/{agent_id}/plans", response_model=PlanOut)
async def create_agent_plan(agent_id: int, payload: PlanCreate, db: AsyncSession = Depends(get_db)) -> PlanOut:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    plan = Plan(agent_id=agent_id, text=payload.text, active=True)
    db.add(plan)
    await db.commit()
    return PlanOut(text=plan.text)


@app.get("/agents/{agent_id}/reflection")
async def get_agent_reflection(agent_id: int, db: AsyncSession = Depends(get_db)) -> str:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    memories = await retrieve_relevant_memories(db, agent_id, "последние мысли", k=2)
    if memories:
        return f"{agent.reflection} Ключевое воспоминание: {memories[0]}"
    return agent.reflection


@app.put("/agents/{agent_id}/reflection")
async def update_agent_reflection(agent_id: int, payload: ReflectionUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    agent.reflection = payload.text
    await db.commit()
    return {"text": agent.reflection}


@app.get("/events")
async def get_events(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = list((await db.scalars(select(Event).order_by(Event.created_at.desc()).limit(max(1, min(limit, 500))))).all())
    rows.reverse()
    return [
        {
            "id": row.id,
            "text": row.text,
            "event_type": row.event_type,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@app.post("/events")
async def create_event(payload: EventCreate, db: AsyncSession = Depends(get_db)) -> dict:
    result = await _create_world_event(db, payload.text.strip())
    return {"id": result["id"], "text": result["text"], "event_type": result["event_type"]}


@app.post("/messages")
async def send_message(payload: MessageCreate, db: AsyncSession = Depends(get_db)) -> dict:
    agent = await db.get(Agent, payload.agentId)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")

    msg = Message(sender="user", agent_id=payload.agentId, text=payload.text.strip())
    db.add(msg)
    db.add(
        ChatMessage(
            sender_type="user",
            sender_agent_id=None,
            receiver_agent_id=payload.agentId,
            text=_db_fit(payload.text.strip()),
            topic=_db_fit("direct"),
        )
    )
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


@app.get("/agents/{agent_id}/messages", response_model=list[MessageOut])
async def get_agent_messages(agent_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[MessageOut]:
    rows = list(
        (
            await db.scalars(
                select(Message)
                .where(Message.agent_id == agent_id)
                .order_by(Message.created_at.desc())
                .limit(max(1, min(limit, 500)))
            )
        ).all()
    )
    rows.reverse()
    return [
        MessageOut(id=row.id, sender=row.sender, agent_id=row.agent_id, text=row.text, created_at=row.created_at)
        for row in rows
    ]


@app.get("/chat/messages", response_model=list[ChatMessageOut])
async def get_chat_messages(limit: int = 50, after: int | None = None, db: AsyncSession = Depends(get_db)) -> list[ChatMessageOut]:
    stmt = select(ChatMessage)
    if after is not None:
        stmt = stmt.where(ChatMessage.id > after)
    rows = list((await db.scalars(stmt.order_by(ChatMessage.created_at.desc()).limit(max(1, min(limit, 500))))).all())
    rows.reverse()
    return await _serialize_chat_messages(rows, db)


@app.post("/chat/messages", response_model=ChatMessageOut)
async def send_chat_message(payload: ChatMessageCreate, db: AsyncSession = Depends(get_db)) -> ChatMessageOut:
    text = payload.text.strip()
    message_type = (payload.type or "").strip().lower()
    if message_type == "event" or (payload.topic or "").strip().lower() == "event":
        result = await _create_world_event(db, text)
        event_chat = await db.get(ChatMessage, result["chat_message_id"])
        if not event_chat:
            raise HTTPException(status_code=500, detail="Ошибка создания сообщения события")
        return (await _serialize_chat_messages([event_chat], db))[0]

    sender_type = "user"
    sender_agent_id = None
    receiver_agent_id = payload.to_agent_id
    if payload.from_agent_id is not None:
        sender_type = "agent"
        sender_agent_id = payload.from_agent_id
    if sender_agent_id is not None and receiver_agent_id is not None and sender_agent_id == receiver_agent_id:
        raise HTTPException(status_code=400, detail="Агент не может писать самому себе")

    if sender_agent_id is not None:
        sender_agent = await db.get(Agent, sender_agent_id)
        if not sender_agent:
            raise HTTPException(status_code=404, detail="Агент-отправитель не найден")

    if receiver_agent_id is not None:
        receiver_agent = await db.get(Agent, receiver_agent_id)
        if not receiver_agent:
            raise HTTPException(status_code=404, detail="Агент-получатель не найден")

    row = ChatMessage(
        sender_type=sender_type,
        sender_agent_id=sender_agent_id,
        receiver_agent_id=receiver_agent_id,
        text=_db_fit(text),
        topic=_db_fit(payload.topic),
    )
    db.add(row)

    # Пользовательское сообщение в общий чат видят все агенты.
    if sender_type == "user" and receiver_agent_id is None:
        agents = list((await db.scalars(select(Agent))).all())
        for agent in agents:
            await add_memory(db, agent.id, f"Пользователь написал в чат: {text}", source="chat")

    await db.commit()
    await db.refresh(row)

    out = (await _serialize_chat_messages([row], db))[0]
    payload_out = {
        "type": "chat_message",
        "id": out.id,
        "sender_type": out.sender_type,
        "sender_agent_id": out.sender_agent_id,
        "sender_name": out.sender_name,
        "receiver_agent_id": out.receiver_agent_id,
        "receiver_name": out.receiver_name,
        "text": out.text,
        "topic": out.topic,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    await event_bus.publish(payload_out)
    await ws_hub.broadcast(payload_out)
    return out


@app.post("/chat/clear")
async def clear_chat(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(delete(ChatMessage))
    await db.commit()
    deleted = int(result.rowcount or 0)
    payload_out = {
        "type": "chat_cleared",
        "deleted_count": deleted,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    await event_bus.publish(payload_out)
    await ws_hub.broadcast(payload_out)
    return {"status": "ok", "deleted_count": deleted}


@app.post("/time-speed", response_model=TimeSpeedOut)
async def set_time_speed_post(payload: TimeSpeedIn, db: AsyncSession = Depends(get_db)) -> TimeSpeedOut:
    return await _set_time_speed(payload, db)


@app.put("/time-speed", response_model=TimeSpeedOut)
async def set_time_speed_put(payload: TimeSpeedIn, db: AsyncSession = Depends(get_db)) -> TimeSpeedOut:
    return await _set_time_speed(payload, db)


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
                avatar="yellow_slime.svg",
                avatar_color="#FFD700",
                avatar_name="Yellow Slime",
                personality="Энергичная стратегиня, быстро строит планы и любит командные активности.",
            ),
            Agent(
                name="Бруно",
                avatar="blue_slime.svg",
                avatar_color="#4169E1",
                avatar_name="Blue Slime",
                personality="Верный и эмпатичный, защищает друзей и стремится к стабильности.",
            ),
            Agent(
                name="Нова",
                avatar="purple_slime.svg",
                avatar_color="#800080",
                avatar_name="Purple Slime",
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


async def _set_time_speed(payload: TimeSpeedIn, db: AsyncSession) -> TimeSpeedOut:
    state = await db.get(SimulationState, 1)
    if not state:
        state = SimulationState(id=1, speed=payload.speed)
        db.add(state)
    else:
        state.speed = payload.speed
    await db.commit()
    return TimeSpeedOut(speed=state.speed)


def relation_label(score: float) -> tuple[str, str]:
    if score >= 0.7:
        return ("Симпатия", "#4CAF50")
    if score >= 0.4:
        return ("Нейтралитет", "#FFC107")
    return ("Антипатия", "#F44336")


def _hash_password(password: str) -> str:
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return f"sha256${digest}"


def _verify_password(password: str, password_hash: str) -> bool:
    expected = _hash_password(password)
    return hmac.compare_digest(expected, password_hash)


def _create_token(user_id: int) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.auth_token_expire_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.auth_secret_key, algorithm="HS256")


async def _get_current_user(credentials: HTTPAuthorizationCredentials | None, db: AsyncSession) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.auth_secret_key, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Невалидный токен") from exc

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


async def _serialize_chat_messages(rows: list[ChatMessage], db: AsyncSession) -> list[ChatMessageOut]:
    agent_ids: set[int] = set()
    for row in rows:
        if row.sender_agent_id:
            agent_ids.add(row.sender_agent_id)
        if row.receiver_agent_id:
            agent_ids.add(row.receiver_agent_id)

    names: dict[int, str] = {}
    if agent_ids:
        agents = list((await db.scalars(select(Agent).where(Agent.id.in_(agent_ids)))).all())
        names = {agent.id: agent.name for agent in agents}

    out: list[ChatMessageOut] = []
    for row in rows:
        sender_name = "Пользователь"
        if row.sender_type == "agent" and row.sender_agent_id:
            sender_name = names.get(row.sender_agent_id, f"Agent {row.sender_agent_id}")
        elif row.sender_type == "system":
            sender_name = "Система"

        receiver_name = None
        if row.receiver_agent_id:
            receiver_name = names.get(row.receiver_agent_id, f"Agent {row.receiver_agent_id}")

        out.append(
            ChatMessageOut(
                id=row.id,
                type=_chat_message_type(row),
                agentId=row.sender_agent_id,
                sender_type=row.sender_type,
                sender_agent_id=row.sender_agent_id,
                sender_name=sender_name,
                receiver_agent_id=row.receiver_agent_id,
                receiver_name=receiver_name,
                text=row.text,
                topic=row.topic,
                timestamp=row.created_at,
                created_at=row.created_at,
            )
        )
    return out


@app.get("/simulation/status", response_model=SimulationStatusOut)
async def simulation_status() -> SimulationStatusOut:
    return SimulationStatusOut(running=sim_engine.is_running())


@app.post("/simulation/start", response_model=SimulationStatusOut)
async def simulation_start() -> SimulationStatusOut:
    sim_engine.set_running(True)
    return SimulationStatusOut(running=True)


@app.post("/simulation/stop", response_model=SimulationStatusOut)
async def simulation_stop() -> SimulationStatusOut:
    sim_engine.set_running(False)
    return SimulationStatusOut(running=False)


async def _create_world_event(db: AsyncSession, text: str) -> dict:
    event = Event(text=text, event_type="user_event")
    db.add(event)
    agents = list((await db.scalars(select(Agent))).all())
    for agent in agents:
        await add_memory(db, agent.id, f"Событие мира: {text}", source="world")
        agent.reflection = f"Произошло важное событие: {text}. Нужно переосмыслить действия."
        agent.current_plan = "Адаптироваться к новому событию"
    await _apply_event_mood_updates(db, text, agents)

    event_chat = ChatMessage(
        sender_type="system",
        sender_agent_id=None,
        receiver_agent_id=None,
        text=_db_fit(text),
        topic=_db_fit("event"),
    )
    db.add(event_chat)
    await db.commit()

    payload_event = {
        "type": "event",
        "event_id": event.id,
        "text": event.text,
        "event_type": event.event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    payload_chat = {
        "type": "chat_message",
        "id": event_chat.id,
        "sender_type": "system",
        "sender_agent_id": None,
        "sender_name": "Система",
        "receiver_agent_id": None,
        "receiver_name": None,
        "text": event_chat.text,
        "topic": "event",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    await event_bus.publish(payload_event)
    await event_bus.publish(payload_chat)
    await ws_hub.broadcast(payload_event)
    await ws_hub.broadcast(payload_chat)
    return {"id": event.id, "text": event.text, "event_type": event.event_type, "chat_message_id": event_chat.id}


async def _apply_event_mood_updates(db: AsyncSession, event_text: str, agents: list[Agent]) -> None:
    text = event_text.lower()
    angry_keywords = [
        "плохое настроение",
        "зл",
        "бесит",
        "раздраж",
        "в ярости",
        "сердит",
        "грустит",
        "подавлен",
        "расстроен",
        "тревож",
    ]
    calm_keywords = ["успоко", "рад", "счаст", "вдохнов", "весел", "доволен"]
    group_words = ["все", "каждый", "друг с другом", "между собой"]
    conflict_words = ["поссор", "конфликт", "руга", "ненавид", "вражду"]

    group_conflict = any(w in text for w in group_words) and any(w in text for w in conflict_words)
    if group_conflict:
        for agent in agents:
            agent.mood_text = "Раздражен"
            agent.mood_emoji = "😠"
            agent.mood_color = "#F44336"
            agent.mood_score = 0.15
            await add_memory(
                db,
                agent.id,
                f"Глобальное событие ухудшило атмосферу и мое настроение: {event_text}",
                source="event_mood",
            )
        rels = list((await db.scalars(select(Relationship))).all())
        for rel in rels:
            rel.score = max(0.0, rel.score - 0.22)

    for agent in agents:
        if agent.name.lower() not in text:
            continue
        if any(k in text for k in angry_keywords):
            agent.mood_text = "Тревожный"
            agent.mood_emoji = "😟"
            agent.mood_color = "#FF9800"
            agent.mood_score = 0.22
            await add_memory(db, agent.id, f"Событие повлияло на мое настроение: {event_text}", source="event_mood")
        elif any(k in text for k in calm_keywords):
            agent.mood_text = "Воодушевленный"
            agent.mood_emoji = "✨"
            agent.mood_color = "#8BC34A"
            agent.mood_score = 0.75
            await add_memory(db, agent.id, f"Событие улучшило мое настроение: {event_text}", source="event_mood")


def _chat_message_type(row: ChatMessage) -> str:
    if row.topic == "event":
        return "event"
    if row.sender_type == "agent":
        return "agent"
    if row.sender_type == "user":
        return "user"
    return "system"


def _db_fit(text: str | None, max_len: int = CHAT_DB_MAX_LEN) -> str | None:
    if text is None:
        return None
    value = text.strip()
    if len(value) <= max_len:
        return value
    return value[: max_len - 1].rstrip() + "…"
    SimulationStatusOut,
