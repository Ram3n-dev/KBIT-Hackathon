from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

import httpx

from app.config import get_settings


ProviderName = Literal["none", "deepseek", "gigachat"]

PROVIDER_MODELS: dict[str, list[str]] = {
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "gigachat": ["GigaChat-2", "GigaChat", "GigaChat-Pro"],
}


@dataclass
class LLMRuntimeConfig:
    provider: ProviderName
    model: str
    fallback_model: str | None
    temperature: float
    max_tokens: int
    timeout_seconds: float

    deepseek_api_base: str
    deepseek_api_key: str | None

    gigachat_api_base: str
    gigachat_auth_url: str
    gigachat_auth_key: str | None
    gigachat_access_token: str | None
    gigachat_scope: str
    gigachat_verify_ssl: bool

    agent_system_prompt: str
    summary_system_prompt: str


class LLMService:
    def __init__(self) -> None:
        settings = get_settings()
        self._config = LLMRuntimeConfig(
            provider=_normalize_provider(settings.llm_provider),
            model=settings.llm_model,
            fallback_model=settings.llm_fallback_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout_seconds=settings.llm_timeout_seconds,
            deepseek_api_base=settings.deepseek_api_base,
            deepseek_api_key=settings.deepseek_api_key,
            gigachat_api_base=settings.gigachat_api_base,
            gigachat_auth_url=settings.gigachat_auth_url,
            gigachat_auth_key=settings.gigachat_auth_key,
            gigachat_access_token=settings.gigachat_access_token,
            gigachat_scope=settings.gigachat_scope,
            gigachat_verify_ssl=settings.gigachat_verify_ssl,
            agent_system_prompt=settings.llm_agent_system_prompt,
            summary_system_prompt=settings.llm_summary_system_prompt,
        )
        self._gigachat_token: str | None = settings.gigachat_access_token
        self._gigachat_token_expires_at: datetime | None = None

    def update_runtime(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if value is None or not hasattr(self._config, key):
                continue
            if key == "provider":
                value = _normalize_provider(str(value))
            setattr(self._config, key, value)

    def get_status(self) -> dict[str, Any]:
        cfg = self._config
        return {
            "provider": cfg.provider,
            "model": cfg.model,
            "fallback_model": cfg.fallback_model,
            "enabled": self.is_enabled(),
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "timeout_seconds": cfg.timeout_seconds,
            "has_deepseek_key": bool(cfg.deepseek_api_key),
            "has_gigachat_auth_key": bool(cfg.gigachat_auth_key),
            "has_gigachat_access_token": bool(cfg.gigachat_access_token or self._gigachat_token),
            "gigachat_verify_ssl": cfg.gigachat_verify_ssl,
        }

    def list_providers(self) -> list[dict[str, Any]]:
        cfg = self._config
        return [
            {"provider": "none", "models": [], "configured": True},
            {
                "provider": "deepseek",
                "models": PROVIDER_MODELS["deepseek"],
                "configured": bool(cfg.deepseek_api_key),
            },
            {
                "provider": "gigachat",
                "models": PROVIDER_MODELS["gigachat"],
                "configured": bool(cfg.gigachat_access_token or cfg.gigachat_auth_key or self._gigachat_token),
            },
        ]

    def is_enabled(self) -> bool:
        cfg = self._config
        if cfg.provider == "deepseek":
            return bool(cfg.deepseek_api_key)
        if cfg.provider == "gigachat":
            return bool(cfg.gigachat_access_token or cfg.gigachat_auth_key or self._gigachat_token)
        return False

    async def test_connection(self) -> dict[str, Any]:
        started = time.perf_counter()
        if self._config.provider == "none":
            return {"ok": True, "provider": "none", "message": "LLM disabled by config", "latency_ms": 0}
        text = await self._chat("Ответь одним словом: ok", "ping")
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": bool(text),
            "provider": self._config.provider,
            "message": text or "No response from provider",
            "latency_ms": elapsed_ms,
        }

    async def generate_agent_step(
        self,
        *,
        actor_name: str,
        actor_personality: str,
        actor_mood: str,
        target_name: str,
        memories: list[str],
    ) -> dict[str, Any] | None:
        if not self.is_enabled():
            return None

        memory_text = "\n".join(f"- {m}" for m in memories[:5]) if memories else "- (нет воспоминаний)"
        user_prompt = (
            f"Агент: {actor_name}\n"
            f"Личность: {actor_personality}\n"
            f"Текущее настроение: {actor_mood}\n"
            f"Взаимодействует с: {target_name}\n"
            f"Ключевые воспоминания:\n{memory_text}\n"
            "Сгенерируй рефлексию, план и действие на текущий тик."
        )

        text = await self._chat(self._config.agent_system_prompt, user_prompt)
        if not text:
            return None
        return _parse_agent_step_json(text)

    async def summarize_memories(self, memories: list[str]) -> str | None:
        if not self.is_enabled() or not memories:
            return None
        user_prompt = "Эпизоды:\n" + "\n".join(f"- {m}" for m in memories[:12])
        text = await self._chat(self._config.summary_system_prompt, user_prompt)
        return text.strip() if text else None

    async def _chat(self, system_prompt: str, user_prompt: str) -> str | None:
        cfg = self._config
        try:
            if cfg.provider == "deepseek":
                text = await self._chat_deepseek(system_prompt, user_prompt, cfg.model)
                if text or not cfg.fallback_model:
                    return text
                return await self._chat_deepseek(system_prompt, user_prompt, cfg.fallback_model)
            if cfg.provider == "gigachat":
                text = await self._chat_gigachat(system_prompt, user_prompt, cfg.model)
                if text or not cfg.fallback_model:
                    return text
                return await self._chat_gigachat(system_prompt, user_prompt, cfg.fallback_model)
        except Exception:
            return None
        return None

    async def _chat_deepseek(self, system_prompt: str, user_prompt: str, model: str) -> str | None:
        cfg = self._config
        if not cfg.deepseek_api_key:
            return None

        url = f"{cfg.deepseek_api_base.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
        }
        headers = {"Authorization": f"Bearer {cfg.deepseek_api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return _extract_content(response.json())

    async def _chat_gigachat(self, system_prompt: str, user_prompt: str, model: str) -> str | None:
        cfg = self._config
        token = await self._get_gigachat_token()
        if not token:
            return None

        url = f"{cfg.gigachat_api_base.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=cfg.timeout_seconds, verify=cfg.gigachat_verify_ssl) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return _extract_content(response.json())

    async def _get_gigachat_token(self) -> str | None:
        cfg = self._config
        if cfg.gigachat_access_token:
            return cfg.gigachat_access_token
        if self._gigachat_token and self._gigachat_token_expires_at:
            if datetime.now(timezone.utc) < self._gigachat_token_expires_at:
                return self._gigachat_token
        if not cfg.gigachat_auth_key:
            return None

        headers = {
            "Authorization": f"Basic {cfg.gigachat_auth_key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "RqUID": str(uuid.uuid4()),
        }
        payload = {"scope": cfg.gigachat_scope}
        async with httpx.AsyncClient(timeout=cfg.timeout_seconds, verify=cfg.gigachat_verify_ssl) as client:
            response = await client.post(cfg.gigachat_auth_url, data=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        token = data.get("access_token")
        if not token:
            return None
        self._gigachat_token = token
        expires_at_ms = data.get("expires_at")
        if isinstance(expires_at_ms, (int, float)):
            self._gigachat_token_expires_at = datetime.fromtimestamp(expires_at_ms / 1000, tz=timezone.utc)
        else:
            self._gigachat_token_expires_at = datetime.now(timezone.utc)
        return token


def _normalize_provider(value: str) -> ProviderName:
    candidate = value.lower().strip()
    if candidate in ("none", "deepseek", "gigachat"):
        return candidate  # type: ignore[return-value]
    return "none"


def _extract_content(data: dict[str, Any]) -> str | None:
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def _parse_agent_step_json(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()

    parsed = _safe_json_parse(text)
    if not isinstance(parsed, dict):
        return {"reflection": "", "plan": "", "action": "", "relation_delta": 0.0}
    return {
        "reflection": str(parsed.get("reflection", "")).strip(),
        "plan": str(parsed.get("plan", "")).strip(),
        "action": str(parsed.get("action", "")).strip(),
        "relation_delta": _clamp_delta(parsed.get("relation_delta", 0.0)),
    }


def _safe_json_parse(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return None
        return None


def _clamp_delta(value: Any) -> float:
    try:
        number = float(value)
    except Exception:
        return 0.0
    return max(-0.2, min(0.2, number))


_llm_singleton: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_singleton
    if _llm_singleton is None:
        _llm_singleton = LLMService()
    return _llm_singleton
