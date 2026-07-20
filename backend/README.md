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

## Local CV analysis

`POST /api/v1/documents/analyze` accepts authenticated PDF, DOCX, and TXT CVs
(maximum 10 MiB). It uses `LocalRuleBasedCvAnalyzer`: deterministic section and
keyword rules, not GPT/OpenAI or any paid external API. No API key is required.
`GET /api/v1/documents/latest` returns the current user's latest completed
analysis and `GET /api/v1/documents` returns that user's history.

Run `alembic upgrade head` after pulling the project to apply the local-CV
analysis migration. Image-only PDFs return a 4xx response because OCR is out of
scope. Uploads use a random private storage key; CV text is not logged or stored
as a database field. The structured result and a derived keyword search text are
stored per user. `app.services.cv_lab_similarity` provides deterministic local
TF-IDF/cosine similarity for reuse by recommendations.

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

# Inspect the POSTECH crawler output without changing the database.
python -m scripts.import_postech --dry-run

# Import validated POSTECH data into an empty development/demo database.
# The default retains the 10 newest outputs per lab for recommendation evidence.
python -m scripts.import_postech --max-publications-per-lab 10

# Import all valid publication records (explicitly opt in; can be large).
python -m scripts.import_postech --all-publications

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
| `DOCUMENT_UPLOAD_DIR` | `.document_uploads` | Private filesystem directory for uploads |
| `DOCUMENT_MAX_UPLOAD_BYTES` | `10485760` | Maximum PDF, DOCX, or TXT size (10 MiB) |

Production and test environments have no default CORS origins, and reject `*`.

## Fixture versus real POSTECH data

Fixtures and real crawler data are deliberately separate commands. Tests create a
temporary SQLite schema and call `scripts.seed`; they never read `Crawler/data` or
the network. The POSTECH importer refuses a database containing fixture labs unless
`--allow-mixed` is supplied explicitly. For a clean local reset, delete only the
configured local SQLite database, run `alembic upgrade head`, then choose exactly one
of `python -m scripts.seed` or `python -m scripts.import_postech`.

Each import writes `import_reports/postech-import-<batch-id>.json` containing planned
or applied creates/updates plus skipped/error records. The report is gitignored.
Records with invalid URLs, names, departments, duplicate professor/lab pairs, invalid
years, or papers linked to excluded labs are omitted rather than coerced into the DB.
Only `output_type=publication` enters `papers`: presentation, patent, and book outputs
remain in the immutable raw CSV because the recommendation engine currently consumes
publication text only.

SQLite is used for local/test development and enables foreign keys per connection.
PostgreSQL uses the same SQLAlchemy models and Alembic migration; run the importer
against its production `DATABASE_URL` only after a dry run and backup. The importer
uses one transaction, so a database exception rolls the batch back; individual input
validation failures are reported and do not stop valid records.

## Docker

From the repository root:

```powershell
$env:POSTGRES_PASSWORD = "<local-development-password>"
docker compose up --build
```

The backend container runs `alembic upgrade head` before Uvicorn. The compose
configuration requires `POSTGRES_PASSWORD` from a non-committed local
environment before it can start.

## Admission calendar

`GET /api/v1/admissions` and `/api/v1/admissions/export.ics` provide
source-labelled admission events. They accept `start_at`,
`end_at`, `university_id`, `department_id`, and `event_type` filters.

No real admission dates are committed in this repository. After a human checks an
official source, copy `data/admissions.example.json`, add only verified records,
and run `python -m scripts.import_admissions path/to/admissions.json --dry-run`
before running the same command without `--dry-run`. Each event requires `id`,
`university_id`, `university_name`, `title`, `event_type`, timezone-aware
`start_at`, `source_url`, and `checked_at`; optional `end_at` must not precede
`start_at`. Invalid events are reported with a skip reason, and event IDs are
upserted on re-import. Imported records are marked `origin=official_import`;
development fixtures remain `origin=fixture`.

## Release Playwright smoke

`npm run test:e2e:release` (from `frontend_v2`) runs only the API-backed release
smoke when `PLAYWRIGHT_RELEASE_SMOKE=1`. Start a backend against a migrated,
isolated SQLite database with a small approved POSTECH import first, then set
`BACKEND_API_ORIGIN=http://127.0.0.1:8000`. It uses a unique account and makes
no external web, OCR, or email-service calls.

## Recommendations

Read persisted items with `GET /api/v1/recommendations` and explicitly refresh
them with `POST /api/v1/recommendations/recompute`. Keyword normalization,
TF-IDF similarity, and lexical overlap are deterministic and require no network,
external AI service, or API key.
