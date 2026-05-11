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

## Tests
Backend unit/route tests use `pytest`.

```bash
cd backend
pip install -r requirements.txt
pytest
```

