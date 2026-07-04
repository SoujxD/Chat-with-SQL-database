# Chat with SQL Database

Ask natural-language questions over a database and get back generated SQL,
an explanation, and results — via a React UI backed by a FastAPI API.

## Run with Docker Compose (recommended)

Brings up three services: `postgres` (seeded with a sample ecommerce
database), `backend` (FastAPI), and `frontend` (React, served statically).

```bash
cp .env.example .env   # set GROQ_API_KEY
docker compose up -d --build
```

- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs
- Postgres: `localhost:5432` (`chatsql` / `chatsql`, db `ecommerce`)

In the top-right database selector, pick **"Ecommerce Analytics (Postgres)"**
to query the seeded data — try questions like *"what are the top 5 products
by revenue?"* or *"which customers have spent the most?"*.

The Postgres seed data is loaded once, on first start, into a named volume
(`postgres_data`). To reset it: `docker compose down -v`.

## Run without Docker

```bash
pip install -r requirements.txt
cp .env.example .env   # set GROQ_API_KEY

# Backend API
uvicorn backend.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL, defaults to http://localhost:8000
npm run dev
```

See [backend/README.md](backend/README.md) for API endpoints and the SQL
guardrails (blocked keywords, required LIMIT, query timeout, read-only
connections, row caps). See [frontend/README.md](frontend/README.md) for the
UI's pages and components.

## Databases

| `database_id` | Engine   | Notes                                    |
|----------------|----------|-------------------------------------------|
| `student`      | SQLite   | Bundled `student.db`, always available.   |
| `ecommerce`    | Postgres | Seeded via `seed/ecommerce_postgres.sql`. |

Add more in `backend/config.py`'s `DATABASES` registry.

## Tests

```bash
pip install -r requirements-dev.txt
pytest backend/tests evaluation/tests
```

## Evaluation suite

A 50-question benchmark (easy/medium/hard/adversarial) with ground-truth
answers computed directly from the seeded `ecommerce` database, measuring
SQL validity, execution accuracy, blocked-unsafe-query rate, and latency.
See [evaluation/README.md](evaluation/README.md).

```bash
python -m evaluation.harness --base-url http://localhost:8000 --database-id ecommerce
```
