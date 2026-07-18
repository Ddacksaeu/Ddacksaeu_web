# Ddacksaeu backend

## Database and seed data

`20260718_0002_database_seed_entities` extends the immutable initial schema
with normalized universities, departments, professors, Korean/English
keywords, recommendation scores, crawl provenance, and admission events. It
also adds the needed relations to existing labs, users, and papers. It does
not add CRUD APIs, crawlers, authentication, or frontend changes.

The seed command is idempotent and inserts only clearly labelled fictional
fixtures, including fixture versions of Seoul National University, KAIST, and
POSTECH. Their source URL is `example.invalid`; no real email, professor,
publication, or admission schedule is claimed.

FastAPI and synchronous SQLAlchemy 2 foundation for the POSTECH Lab Finder MVP.
`POST /api/v1/documents/analyze` accepts a PDF CV or portfolio, extracts and
normalizes its text, requests a structured OpenAI analysis, and stores the
private upload plus the fields supported by the current document schema. The
API has no frontend integration in this stage.

## Setup

Run all commands from `backend/` with Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Use the root `.env.example` as a reference, then export values into the process
environment. The application does not load `.env` files directly; Docker
Compose may use an untracked local `.env` for its own variable interpolation.

## Commands

```powershell
# Apply the initial schema to the configured DATABASE_URL.
alembic upgrade head

# Insert clearly fictional, idempotent fixture records after migration.
python -m scripts.seed

# Start the API.
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Verify code quality and tests (SQLite only; no network calls).
ruff format --check .
ruff check .
pytest
```

The health endpoint is available at `http://127.0.0.1:8000/api/v1/health` and
OpenAPI docs at `http://127.0.0.1:8000/api/v1/docs`.

## Environment

| Variable | Development default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | `development`, `test`, or `production` |
| `BACKEND_HOST` | `127.0.0.1` | Server bind host for the launch command |
| `BACKEND_PORT` | `8000` | Server port for the launch command |
| `DATABASE_URL` | `sqlite+pysqlite:///./ddacksaeu.db` | SQLite locally or `postgresql+psycopg://...` in production |
| `CORS_ORIGINS` | `http://localhost:5173` in development | Comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | Structured logger level |
| `OPENAI_API_KEY` | unset | Required only for document analysis; read on the server |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used for structured document analysis |
| `DOCUMENT_UPLOAD_DIR` | `.document_uploads` | Private filesystem directory for uploads |
| `DOCUMENT_MAX_UPLOAD_BYTES` | `10485760` | Maximum PDF size (10 MiB) |

Production and test environments have no default CORS origins, and reject `*`.

## Docker

From the repository root:

```powershell
$env:POSTGRES_PASSWORD = "<local-development-password>"
docker compose up --build
```

The backend container runs `alembic upgrade head` before Uvicorn. The compose
configuration requires `POSTGRES_PASSWORD` from a non-committed local
environment before it can start.
