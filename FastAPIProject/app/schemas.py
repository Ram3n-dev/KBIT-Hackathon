from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=120)
    avatarFile: str | None = Field(default=None, validation_alias=AliasChoices("avatarFile", "avatar"))
    avatarColor: str = "#4CAF50"
    avatarName: str = "Agent"
    personality: str | None = None


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatarFile: str = Field(validation_alias="avatar")
    avatarColor: str = Field(alias="avatar_color")
    avatarName: str = Field(alias="avatar_name")
    personality: str


class AgentUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    avatarFile: str | None = Field(default=None, validation_alias=AliasChoices("avatarFile", "avatar"))
    avatarColor: str | None = None
    avatarName: str | None = None
    personality: str | None = None


class RelationOut(BaseModel):
    from_agent: int = Field(alias="from")
    to_agent: int = Field(alias="to")
    value: float

    model_config = ConfigDict(populate_by_name=True)


class AgentRelationOut(BaseModel):
    id: int
    target_name: str
    type: str
    color: str
    score: float


class RelationCreate(BaseModel):
    from_agent_id: int = Field(alias="from", ge=1)
    to_agent_id: int = Field(alias="to", ge=1)
    value: float = Field(ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class RelationUpdate(BaseModel):
    value: float = Field(ge=0, le=1)


class MoodOut(BaseModel):
    text: str
    emoji: str
    color: str
    score: float


class MoodUpdate(BaseModel):
    text: str | None = None
    emoji: str | None = None
    color: str | None = None
    score: float | None = Field(default=None, ge=0, le=1)


class PlanOut(BaseModel):
    text: str


class PlanCreate(BaseModel):
    text: str = Field(min_length=1)


class EventCreate(BaseModel):
    text: str = Field(min_length=1)
    type: str | None = "event"


class EventOut(BaseModel):
    id: int
    text: str
    event_type: str
    created_at: datetime


class MessageCreate(BaseModel):
    agentId: int = Field(ge=1)
    text: str = Field(min_length=1)


class MessageOut(BaseModel):
    id: int
    sender: str
    agent_id: int
    text: str
    created_at: datetime


class ReflectionUpdate(BaseModel):
    text: str = Field(min_length=1)


class TimeSpeedIn(BaseModel):
    speed: float = Field(ge=0, le=2)


class TimeSpeedOut(BaseModel):
    speed: float


class LLMProviderInfoOut(BaseModel):
    provider: str
    models: list[str]
    configured: bool


class LLMStatusOut(BaseModel):
    provider: str
    model: str
    fallback_model: str | None = None
    enabled: bool
    temperature: float
    max_tokens: int
    timeout_seconds: float
    step_llm_probability: float | None = None
    dialogue_llm_probability: float | None = None
    summary_llm_probability: float | None = None
    agent_cooldown_seconds: int | None = None
    has_deepseek_key: bool
    has_gigachat_auth_key: bool
    has_gigachat_access_token: bool
    gigachat_verify_ssl: bool
    llm_debug_log_enabled: bool
    llm_debug_log_payload: bool
    llm_debug_log_response: bool
    llm_debug_log_max_chars: int


class LLMConfigPatch(BaseModel):
    provider: str | None = None
    model: str | None = None
    fallback_model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=32, le=4096)
    timeout_seconds: float | None = Field(default=None, ge=5, le=180)
    step_llm_probability: float | None = Field(default=None, ge=0, le=1)
    dialogue_llm_probability: float | None = Field(default=None, ge=0, le=1)
    summary_llm_probability: float | None = Field(default=None, ge=0, le=1)
    agent_cooldown_seconds: int | None = Field(default=None, ge=0, le=300)
    max_memories_in_prompt: int | None = Field(default=None, ge=1, le=10)
    max_memory_chars: int | None = Field(default=None, ge=60, le=1000)
    max_chat_context_messages: int | None = Field(default=None, ge=1, le=12)
    max_chat_context_chars: int | None = Field(default=None, ge=60, le=1000)
    deepseek_api_key: str | None = None
    deepseek_api_base: str | None = None
    gigachat_auth_key: str | None = None
    gigachat_access_token: str | None = None
    gigachat_api_base: str | None = None
    gigachat_auth_url: str | None = None
    gigachat_scope: str | None = None
    gigachat_verify_ssl: bool | None = None
    llm_debug_log_enabled: bool | None = None
    llm_debug_log_payload: bool | None = None
    llm_debug_log_response: bool | None = None
    llm_debug_log_max_chars: int | None = Field(default=None, ge=200, le=20000)
    agent_system_prompt: str | None = None
    summary_system_prompt: str | None = None


class LLMTestOut(BaseModel):
    ok: bool
    provider: str
    message: str
    latency_ms: int


class AuthRegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=6, max_length=200)


class AuthLoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    avatar: str

    model_config = ConfigDict(from_attributes=True)


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChatMessageCreate(BaseModel):
    text: str = Field(min_length=1)
    topic: str | None = None
    type: str | None = None
    from_agent_id: int | None = None
    to_agent_id: int | None = None


class ChatMessageOut(BaseModel):
    id: int
    type: str
    agentId: int | None = None
    sender_type: str
    sender_agent_id: int | None
    sender_name: str
    receiver_agent_id: int | None
    receiver_name: str | None
    text: str
    topic: str | None
    timestamp: datetime
    created_at: datetime


class SimulationStatusOut(BaseModel):
    running: bool
