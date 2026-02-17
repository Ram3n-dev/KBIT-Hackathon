from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    avatar: str = "🤖"
    avatarColor: str = "#4CAF50"
    avatarName: str = "Робот"
    personality: str | None = None


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar: str
    avatarColor: str = Field(alias="avatar_color")
    avatarName: str = Field(alias="avatar_name")


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


class MoodOut(BaseModel):
    text: str
    emoji: str
    color: str
    score: float


class PlanOut(BaseModel):
    text: str


class EventCreate(BaseModel):
    text: str = Field(min_length=1)


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
