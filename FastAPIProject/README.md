# Vivarium FastAPI Backend

Backend для хакатон-кейса "Виртуальный мир". Стек: `FastAPI + PostgreSQL + pgvector`.

## Что реализовано
- AI-агенты с состоянием: личность, настроение, рефлексия, планы.
- Долговременная память в `pgvector` (`memories.embedding`) + поиск релевантных воспоминаний.
- Автосуммаризация старых воспоминаний при переполнении контекста.
- Мультиагентные отношения (направленные связи `source -> target` со score 0..1).
- Фоновая симуляция: `рефлексия -> цель -> действие`.
- Управление симуляцией: скорость времени (`/time-speed`).
- Realtime события: `WebSocket /ws/events` и `SSE /events/stream`.
- API совместим с текущим фронтендом (`src/services/api.js`).
- LLM-слой с переключаемыми провайдерами: `DeepSeek` или `GigaChat` (+ fallback без LLM).

## Быстрый старт
1. Поднять PostgreSQL + pgvector:
```bash
docker compose up -d
```
2. Установить зависимости:
```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
```
3. Настроить env:
```bash
copy .env.example .env
```
4. Запустить backend:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Подключение LLM (DeepSeek / GigaChat)
В `.env` выставьте `LLM_PROVIDER`:
- `LLM_PROVIDER=deepseek`
- `LLM_PROVIDER=gigachat`
- `LLM_PROVIDER=none` (fallback-режим без внешнего LLM)

### DeepSeek
```env
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=your_key
DEEPSEEK_API_BASE=https://api.deepseek.com
```

### GigaChat
Вариант A (готовый access token):
```env
LLM_PROVIDER=gigachat
LLM_MODEL=GigaChat-2
GIGACHAT_ACCESS_TOKEN=your_access_token
GIGACHAT_API_BASE=https://gigachat.devices.sberbank.ru/api/v1
```

Вариант B (автополучение токена через OAuth):
```env
LLM_PROVIDER=gigachat
LLM_MODEL=GigaChat-2
GIGACHAT_AUTH_KEY=base64(client_id:client_secret)
GIGACHAT_AUTH_URL=https://ngw.devices.sberbank.ru:9443/api/v2/oauth
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_API_BASE=https://gigachat.devices.sberbank.ru/api/v1
```

LLM используется для:
- генерации шага агента (`reflection -> plan -> action`)
- суммаризации старых воспоминаний при переполнении контекста.

### Runtime-управление LLM через API
- `GET /llm/status` — текущий провайдер, модель и состояние ключей.
- `GET /llm/providers` — список доступных провайдеров и рекомендуемых моделей.
- `PATCH /llm/config` — смена провайдера/модели/параметров на лету.
- `POST /llm/test` — тест запроса к выбранному провайдеру.

Пример смены на DeepSeek без перезапуска:
```bash
curl -X PATCH http://localhost:8000/llm/config ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\":\"deepseek\",\"model\":\"deepseek-chat\",\"deepseek_api_key\":\"YOUR_KEY\"}"
```

## Эндпоинты для фронтенда
- `GET /agents`
- `POST /agents`
- `GET /agents/{id}`
- `GET /relations`
- `GET /agents/{id}/relations`
- `GET /agents/{id}/mood`
- `GET /agents/{id}/plans`
- `GET /agents/{id}/reflection`
- `POST /events`
- `POST /messages`
- `GET /time-speed`
- `POST /time-speed`

## Примечание по фронтенду
Фронт в `src/services/api.js` указывает `http://localhost:8000`, backend использует CORS для `localhost:3000`.
