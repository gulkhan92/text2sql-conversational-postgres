# text2sql-conversational-postgres

Natural-language-to-SQL chatbot for an e-commerce dataset.

- Frontend: React 18 + Vite + TypeScript + Recharts
- Backend: FastAPI (Python 3.11+) + asyncpg (PostgreSQL)
- LLM: Google Gemini (Gemini API) for NL→SQL + answer(retrieved data) analysis & summarization
- DB: PostgreSQL 15+

## Quickstart (local)

### 1) Configure environment
Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.

```bash
cp .env.example .env
```

### 2) Start PostgreSQL
```bash
docker compose -f docker-compose.db.yml up -d
```

### 3) Seed database
```bash
docker compose -f docker-compose.db.yml run --rm backend python -m backend.scripts.seed_db
```

### 4) Run backend
```bash
docker compose up --build
```

Backend will be available at: `http://localhost:8000`

### 5) Run frontend
Frontend will be available at: `http://localhost:5173`

## Ask /chat
POST `http://localhost:8000/chat`

Request:
```json
{ "message": "What is the average amount spent by gender?" }
```

Response:
```json
{
  "answer": "....",
  "sql": "SELECT ...",
  "data": [],
  "chart_suggested": false,
  "chart_type": "bar"
}
```

## Flow diagram

```mermaid
flowchart TD
  U[User question] --> A[POST /chat]
  A --> S[SchemaCache /schema introspection]
  S --> L1[Gemini generate_sql]
  L1 --> Q[execute_readonly_select (guardrails + statement_timeout)]
  Q --> R[Gemini summarize_results]
  R --> Resp[Response JSON: answer/sql/data/chart_suggested]
```

## Tests
Backend unit/route tests use `pytest`.


Test coverage focuses on:
- `backend/db/query_executor.py`: SELECT-only + forbidden keyword guardrails and statement_timeout
- `backend/llm/gemini_client.py`: `strip_sql()` parsing and prompt construction
- `backend/db/schema_cache.py`: TTL fresh vs stale refresh logic
- `backend/routes/chat.py`: `/chat` behavior for empty input, happy path, and error path (with mocks)
- `backend/routes/schema.py`: `/schema` uses cache and always closes the DB connection (with mocks)

```bash
cd backend
pip install -r requirements.txt
pytest
```


