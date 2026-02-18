# KBIT-Hackathon

Общий репозиторий проекта с фронтендом и бэкендом симуляции AI-агентов (Vivarium).

## Структура

- `FastAPIProject/` - основной backend (FastAPI + PostgreSQL + pgvector).
- `Frontend/vivarium/` - frontend (React, CRA).
- `backend/` - отдельная/старая backend-ветка (не основной runtime для текущего UI).

## Технологии

- Backend: FastAPI, SQLAlchemy Async, PostgreSQL, pgvector, JWT, WebSocket, SSE.
- Frontend: React, react-router-dom, react-scripts.
- Infra: Docker Compose (PostgreSQL + pgvector).

## Быстрый запуск (локально)

### 1. Поднять БД

```bash
cd FastAPIProject
docker compose up -d
```

### 2. Запустить backend

```bash
cd FastAPIProject
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy app.env.example app.env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Проверка:
- `http://127.0.0.1:8000/health`

### 3. Запустить frontend

```bash
cd Frontend/vivarium
npm install
npm start
```

Фронт откроется на:
- `http://localhost:3000`

## Связка Frontend <-> Backend

Во фронте API URL сейчас захардкожен в:
- `Frontend/vivarium/src/services/api.js`

Текущая строка:
- `const API_URL = "http://192.168.0.74:8000";`

Если backend запущен локально, поменяйте на:
- `http://127.0.0.1:8000` или `http://localhost:8000`.

## Что уже реализовано в backend

- Регистрация/логин, JWT и профиль пользователя.
- CRUD агентов, обновление аватаров.
- Отношения между агентами.
- Настроение, планы, рефлексия.
- События мира и чат.
- Realtime события:
  - `GET /events/stream` (SSE)
  - `WS /ws/events` (WebSocket)
- Управление симуляцией:
  - `/simulation/status`
  - `/simulation/start`
  - `/simulation/stop`
  - `/time-speed`
- LLM runtime-конфиг:
  - `/llm/status`
  - `/llm/providers`
  - `/llm/config`
  - `/llm/test`

Подробное API backend описано в:
- `FastAPIProject/README.md`

## Конфигурация

Backend конфиг:
- `FastAPIProject/app.env`
- шаблон: `FastAPIProject/app.env.example`

Критично проверить:
- `DATABASE_URL`
- `AUTH_SECRET_KEY`
- `LLM_PROVIDER` (`none`, `deepseek`, `gigachat`)

## Частые проблемы

1. Фронт не видит API  
Причина: неверный `API_URL` в `Frontend/vivarium/src/services/api.js`.

2. Backend не стартует из-за БД  
Причина: не запущен Docker/PostgreSQL контейнер.

3. Аватары/агенты не обновляются  
Проверьте формат полей в запросах (`avatarFile`, `avatarColor`, `avatarName`) и токен авторизации.

## Команды для демо (кратко)

1. `cd FastAPIProject && docker compose up -d`
2. `cd FastAPIProject && uvicorn main:app --reload --port 8000`
3. `cd Frontend/vivarium && npm start`
4. Открыть `http://localhost:3000`

## Команда / контекст хакатона

Этот README описывает запуск всего решения целиком: база данных + backend + frontend.
