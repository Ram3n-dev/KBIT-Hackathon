from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="app.env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Vivarium Backend"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vivarium"
    memory_embedding_dim: int = 128
    memory_context_limit: int = 15
    summary_batch_size: int = 8
    simulation_tick_seconds: float = 6.0
    db_connect_retries: int = 20
    db_connect_retry_delay_seconds: float = 1.5

    llm_provider: str = "none"  # none | deepseek | gigachat
    llm_model: str = "deepseek/deepseek-v3.2"
    llm_fallback_model: str | None = None
    llm_temperature: float = 0.7
    llm_timeout_seconds: float = 45.0
    llm_max_tokens: int = 512
    llm_debug_log_enabled: bool = True
    llm_debug_log_payload: bool = True
    llm_debug_log_response: bool = True
    llm_debug_log_max_chars: int = 2500
    llm_agent_system_prompt: str = (
        "Ты симулятор поведения AI-агента в виртуальном мире. "
        "Отвечай строго JSON без markdown в формате "
        '{"reflection":"...", "plan":"...", "action":"...", "relation_delta":0.0}.'
    )
    llm_summary_system_prompt: str = (
        "Ты модуль долговременной памяти. Сожми список эпизодов в короткую сводку "
        "на русском (2-4 предложения), сохрани факты и причинно-следственные связи."
    )

    deepseek_api_base: str = "https://api.deepseek.com"
    deepseek_api_key: str | None = None

    gigachat_api_base: str = "https://gigachat.devices.sberbank.ru/api/v1"
    gigachat_auth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_auth_key: str | None = None
    gigachat_access_token: str | None = None
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_verify_ssl: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
