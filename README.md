# Ddacksaeu

Ddacksaeu is a web service for students who are preparing for graduate school applications.

The main purpose of this project is to make the lab search process easier. Instead of checking many university and laboratory pages one by one, users can search for laboratories, review professor and publication information, upload a CV, and receive recommendations based on their research interests and experience.

The project also includes tools for saving laboratories, writing contact email drafts, and organizing admission schedules.

This repository was developed as a hackathon MVP, but the current version has both a working frontend and backend structure.

---

## Main User Flow

Users search for laboratories, review professors and publication evidence, and
save promising labs. After signing in, they can upload a CV for local
rule-based analysis, view explainable recommendations, prepare an outreach
draft, and organize admission deadlines in a calendar.

## How We Used Codex and GPT-5.6

Codex supported repository analysis, implementation, frontend-backend
integration, debugging, tests, and documentation. GPT-5.6 was used inside
Codex for those development activities. The team reviewed and corrected
AI-assisted changes, ran tests, and made the product and submission decisions.

The shipped product has no direct OpenAI API or GPT-5.6 feature. CV analysis
uses local document parsing and controlled rules; recommendations use keyword
normalization, scikit-learn TF-IDF, fixed score weights, and rule-based
explanations. No CV text is sent to an OpenAI service by these flows.

For the detailed development workflow and representative examples, see
[`docs/OPENAI_USAGE.md`](docs/OPENAI_USAGE.md).

---

## Main Features

### Laboratory Search

Users can search laboratories and review information such as:

- university and department
- professor
- research keywords
- recent publications
- laboratory details
- data source information

The backend can use either fictional fixture data or imported POSTECH crawler data.

### CV Analysis

Users can upload a CV in one of the following formats:

- PDF
- DOCX
- TXT

The backend extracts sections and keywords from the document and saves a structured analysis result for the user.

The current analyzer is rule-based. It does not use OCR, so image-only PDF files are not supported.

The maximum upload size is 10 MB.

### Lab Recommendations

After uploading a CV, users can receive laboratory recommendations.

The recommendation score is calculated with several parts:

| Component | Weight |
| --- | ---: |
| Research keyword match | 35 |
| CV and lab similarity | 30 |
| Recent publication relevance | 20 |
| User preference match | 10 |
| Data freshness | 5 |
| **Total** | **100** |

The recommendation system uses keyword normalization, TF-IDF, cosine similarity, and lexical overlap.

It also shows supporting information such as matched keywords, missing keywords, score details, and suggested next actions. This makes it easier for the user to understand why a laboratory was recommended.

The current recommendation system runs locally and does not require an external LLM or embedding API.

### Saved Laboratories

Signed-in users can save laboratories that they want to review later.

This feature is connected to the backend API, so saved items are linked to each user account.

### Contact Email Draft

Users can prepare a contact email draft for a professor.

The feature is designed to help users organize basic information before contacting a laboratory. Users should still review and edit the draft before sending it.

### Admission Calendar

The admission calendar helps users organize graduate school deadlines and related events.

Admission events can be filtered by:

- date range
- university
- department
- event type

The backend also supports ICS export, so the schedule can be added to a calendar application.

Only verified admission information should be imported into the real dataset. The repository does not claim that fixture dates are official admission dates.

### User Dashboard

The frontend includes:

- sign in and account setup
- personalized dashboard
- laboratory search
- laboratory detail pages
- CV analysis
- recommendation results
- saved laboratories
- contact email drafts
- admission scheduler
- profile page

---

## How It Works

```text
User
  |
  v
Next.js Frontend
  |
  |  /api/backend/*
  v
Next.js BFF Route
  |
  v
FastAPI Backend
  |
  +-- Authentication
  +-- CV Analysis
  +-- Laboratory Search
  +-- Recommendations
  +-- Saved Laboratories
  +-- Email Drafts
  +-- Admission Calendar
  |
  v
SQLAlchemy
  |
  +-- SQLite for local development and tests
  +-- PostgreSQL for Docker or production
```

The frontend does not store the backend authentication token in browser storage. It uses the Next.js backend-for-frontend route and an HttpOnly session cookie.

---

## Tech Stack

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- Ky
- Zod
- Vitest
- Playwright
- ESLint

### Backend

- Python 3.11+
- FastAPI
- SQLAlchemy 2
- Alembic
- Pydantic
- scikit-learn
- PyPDF
- python-docx
- Ruff
- Pytest

### Database and Deployment

- SQLite
- PostgreSQL
- Docker
- Docker Compose

---

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── config/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── migrations/
│   ├── scripts/
│   ├── tests/
│   ├── README.md
│   └── pyproject.toml
│
├── frontend_v2/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── public/
│   ├── tests/
│   ├── README.md
│   └── package.json
│
├── Crawler/
├── data/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

Some folders may contain development data, crawler outputs, fixtures, or internal documentation.

---

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Ddacksaeu/Ddacksaeu_web.git
cd Ddacksaeu_web
```

---

## Backend Setup

Run the following commands from the `backend` directory.

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### macOS or Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Apply the database migrations:

```bash
alembic upgrade head
```

After migration, choose one data source.

### Option A: Fictional Fixture Data

```bash
python -m scripts.seed
```

The fixture data is only for local development and testing. It does not represent real professor, publication, email, or admission information.

### Option B: POSTECH Crawler Data

First, check the import without changing the database:

```bash
python -m scripts.import_postech --dry-run
```

Then import the validated data:

```bash
python -m scripts.import_postech --max-publications-per-lab 10
```

Do not use fixture data and POSTECH crawler data together unless mixed data is intentionally allowed.

Start the backend:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend URLs:

- API health check: `http://127.0.0.1:8000/api/v1/health`
- OpenAPI documentation: `http://127.0.0.1:8000/api/v1/docs`

---

## Frontend Setup

Open another terminal.

```bash
cd frontend_v2
npm install
```

Create a local environment file:

```bash
cp .env.example .env.local
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env.local
```

Make sure the frontend can access the backend.

```env
BACKEND_API_ORIGIN=http://127.0.0.1:8000
```

Start the frontend:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

For a production build:

```bash
npm run build
npm run start
```

---

## Environment Variables

The backend uses the root `.env.example` as a reference.

| Variable | Default | Description |
| --- | --- | --- |
| `APP_ENV` | `development` | Application environment |
| `BACKEND_HOST` | `127.0.0.1` | Backend host |
| `BACKEND_PORT` | `8000` | Backend port |
| `DATABASE_URL` | `sqlite+pysqlite:///./ddacksaeu.db` | Database connection |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins |
| `LOG_LEVEL` | `INFO` | Backend log level |
| `DOCUMENT_UPLOAD_DIR` | `.document_uploads` | Private upload directory |
| `DOCUMENT_MAX_UPLOAD_BYTES` | `10485760` | Maximum CV upload size |

The application does not automatically load backend `.env` files. Environment variables must be set in the process environment. Docker Compose can use a local untracked `.env` file for variable interpolation.

For production, set a secure `OWNER_SESSION_SECRET` with at least 16 characters for the frontend session.

---

## Docker

From the repository root, set a PostgreSQL password and start the services.

### Windows PowerShell

```powershell
$env:POSTGRES_PASSWORD = "<local-development-password>"
docker compose up --build
```

### macOS or Linux

```bash
export POSTGRES_PASSWORD="<local-development-password>"
docker compose up --build
```

The backend container applies Alembic migrations before starting Uvicorn.

---

## API Overview

The backend API is versioned under:

```text
/api/v1
```

Main API groups include:

| API Group | Purpose |
| --- | --- |
| Authentication | User registration, login, and session-related functions |
| Profile | User profile and preferences |
| Laboratories | Lab search and lab detail information |
| Documents | CV upload, analysis, latest result, and history |
| Recommendations | Saved recommendation results and recomputation |
| Saved Labs | Save or remove laboratories |
| Email Drafts | Prepare contact email drafts |
| Admissions | Admission events and ICS export |
| Health | Backend status check |

The frontend accesses the FastAPI backend through:

```text
/api/backend/*
```

For example:

```text
http://localhost:3000/api/backend/health
```

---

## CV Data and Privacy

Uploaded CV files are stored with a random private storage key.

The backend does not save the full extracted CV text as a database field. It saves the structured analysis result and derived keyword search text.

CV text should not be written to application logs.

This project does not send CV data to an external AI service in the current version.

---

## Recommendation Details

The recommendation result is deterministic. Running the same version with the same data should produce the same result.

If one score component has no available data, that component receives zero and the response includes a warning. The remaining score weights are not automatically increased.

Recommendation evidence may include:

- matched research terms
- missing research terms
- CV-to-lab similarity
- recent publication evidence
- user preference evidence
- data origin
- data freshness
- a suggested next action

Crawler-imported laboratories and fixture laboratories use the same recommendation fields.

Recommendation weights can be changed in:

```text
backend/app/config/recommendation_weights.py
```

The total weight must remain 100.

---

## Data Import Notes

The POSTECH importer validates crawler records before adding them to the database.

Records may be skipped when they have problems such as:

- invalid URLs
- missing or invalid names
- invalid departments
- duplicated professor and laboratory pairs
- invalid publication years
- publications connected to excluded laboratories

The importer creates a report in:

```text
import_reports/
```

Only publication records are currently added to the paper table. Presentations, patents, and books remain in the raw crawler data because the recommendation system currently uses publication text.

Before importing real data into a production database, run a dry run and create a backup.

---

## Admission Data

The admission API supports source-labeled events and ICS export.

No real admission schedule is guaranteed by the fixture data.

Verified admission data can be imported after checking an official university source. A dry run should be completed before the real import.

Users should always confirm important deadlines on the official university or department website.

---

## Testing

### Backend

Run these commands from `backend`:

```bash
ruff format --check .
ruff check .
pytest
```

Backend tests use SQLite and do not require network access.

### Frontend

Run these commands from `frontend_v2`:

```bash
npm test
npm run lint
npx tsc --noEmit
npm run test:e2e
```

For the release smoke test:

```bash
npm run test:e2e:release
```

The release smoke test requires the frontend and backend to be running with the required environment variables.

---

## Current Limitations

This is still an MVP and there are several limitations.

- CV analysis is rule-based.
- OCR is not supported.
- Image-only PDFs cannot be analyzed.
- Recommendation quality depends on the available keywords and publication data.
- Some datasets are fictional fixtures for development.
- Admission information must be checked manually before it is treated as official.
- Contact email drafts must be reviewed before use.
- The current crawler mainly focuses on POSTECH data.
- The project does not support every university yet.

---

## Future Work

Possible next steps include:

- improving research keyword normalization
- adding semantic search
- supporting more universities
- expanding verified crawler data
- improving professor and publication matching
- adding better recommendation feedback
- supporting more CV layouts
- adding optional OCR support
- improving contact email personalization
- adding deployment monitoring and automated releases

---

## Development Notes

The root README gives a general overview of the project.

More detailed instructions are available in:

- `backend/README.md`
- `frontend_v2/README.md`
- `docs/`

When changing an API contract, update both the backend implementation and the frontend BFF route.

---

## Disclaimer

Ddacksaeu is a student project made to support graduate school research and application preparation.

Recommendation results are only supporting information. Users should review the original laboratory page, professor page, publication source, and official admission page before making a decision.

The project does not guarantee admission, professor availability, recruitment status, or the accuracy of externally collected information.

---

## License

No open-source license has been added yet.

Unless a license file is added, the source code remains under the repository owner's default copyright.
라이브러리
/
README.md


# Ddacksaeu

Ddacksaeu is a web service for students who are preparing for graduate school applications.

The main purpose of this project is to make the lab search process easier. Instead of checking many university and laboratory pages one by one, users can search for laboratories, review professor and publication information, upload a CV, and receive recommendations based on their research interests and experience.

The project also includes tools for saving laboratories, writing contact email drafts, and organizing admission schedules.

This repository was developed as a hackathon MVP, but the current version has both a working frontend and backend structure.

---

## Main Features

### Laboratory Search

Users can search laboratories and review information such as:

- university and department
- professor
- research keywords
- recent publications
- laboratory details
- data source information

The backend can use either fictional fixture data or imported POSTECH crawler data.

### CV Analysis

Users can upload a CV in one of the following formats:

- PDF
- DOCX
- TXT

The backend extracts sections and keywords from the document and saves a structured analysis result for the user.

The current analyzer is rule-based. It does not use OCR, so image-only PDF files are not supported.

The maximum upload size is 10 MB.

### Lab Recommendations

After uploading a CV, users can receive laboratory recommendations.

The recommendation score is calculated with several parts:

| Component | Weight |
| --- | ---: |
| Research keyword match | 35 |
| CV and lab similarity | 30 |
| Recent publication relevance | 20 |
| User preference match | 10 |
| Data freshness | 5 |
| **Total** | **100** |

The recommendation system uses keyword normalization, TF-IDF, cosine similarity, and lexical overlap.

It also shows supporting information such as matched keywords, missing keywords, score details, and suggested next actions. This makes it easier for the user to understand why a laboratory was recommended.

The current recommendation system runs locally and does not require an external LLM or embedding API.

### Saved Laboratories

Signed-in users can save laboratories that they want to review later.

This feature is connected to the backend API, so saved items are linked to each user account.

### Contact Email Draft

Users can prepare a contact email draft for a professor.

The feature is designed to help users organize basic information before contacting a laboratory. Users should still review and edit the draft before sending it.

### Admission Calendar

The admission calendar helps users organize graduate school deadlines and related events.

Admission events can be filtered by:

- date range
- university
- department
- event type

The backend also supports ICS export, so the schedule can be added to a calendar application.

Only verified admission information should be imported into the real dataset. The repository does not claim that fixture dates are official admission dates.

### User Dashboard

The frontend includes:

- sign in and account setup
- personalized dashboard
- laboratory search
- laboratory detail pages
- CV analysis
- recommendation results
- saved laboratories
- contact email drafts
- admission scheduler
- profile page

---

## How It Works

```text
User
  |
  v
Next.js Frontend
  |
  |  /api/backend/*
  v
Next.js BFF Route
  |
  v
FastAPI Backend
  |
  +-- Authentication
  +-- CV Analysis
  +-- Laboratory Search
  +-- Recommendations
  +-- Saved Laboratories
  +-- Email Drafts
  +-- Admission Calendar
  |
  v
SQLAlchemy
  |
  +-- SQLite for local development and tests
  +-- PostgreSQL for Docker or production
```

The frontend does not store the backend authentication token in browser storage. It uses the Next.js backend-for-frontend route and an HttpOnly session cookie.

---

## Tech Stack

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- Ky
- Zod
- Vitest
- Playwright
- ESLint

### Backend

- Python 3.11+
- FastAPI
- SQLAlchemy 2
- Alembic
- Pydantic
- scikit-learn
- PyPDF
- python-docx
- Ruff
- Pytest

### Database and Deployment

- SQLite
- PostgreSQL
- Docker
- Docker Compose

---

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── config/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── migrations/
│   ├── scripts/
│   ├── tests/
│   ├── README.md
│   └── pyproject.toml
│
├── frontend_v2/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── public/
│   ├── tests/
│   ├── README.md
│   └── package.json
│
├── Crawler/
├── data/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

Some folders may contain development data, crawler outputs, fixtures, or internal documentation.

---

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Ddacksaeu/Ddacksaeu_web.git
cd Ddacksaeu_web
```

---

## Backend Setup

Run the following commands from the `backend` directory.

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### macOS or Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Apply the database migrations:

```bash
alembic upgrade head
```

After migration, choose one data source.

### Option A: Fictional Fixture Data

```bash
python -m scripts.seed
```

The fixture data is only for local development and testing. It does not represent real professor, publication, email, or admission information.

### Option B: POSTECH Crawler Data

First, check the import without changing the database:

```bash
python -m scripts.import_postech --dry-run
```

Then import the validated data:

```bash
python -m scripts.import_postech --max-publications-per-lab 10
```

Do not use fixture data and POSTECH crawler data together unless mixed data is intentionally allowed.

Start the backend:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend URLs:

- API health check: `http://127.0.0.1:8000/api/v1/health`
- OpenAPI documentation: `http://127.0.0.1:8000/api/v1/docs`

---

## Frontend Setup

Open another terminal.

```bash
cd frontend_v2
npm install
```

Create a local environment file:

```bash
cp .env.example .env.local
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env.local
```

Make sure the frontend can access the backend.

```env
BACKEND_API_ORIGIN=http://127.0.0.1:8000
```

Start the frontend:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

For a production build:

```bash
npm run build
npm run start
```

---

## Environment Variables

The backend uses the root `.env.example` as a reference.

| Variable | Default | Description |
| --- | --- | --- |
| `APP_ENV` | `development` | Application environment |
| `BACKEND_HOST` | `127.0.0.1` | Backend host |
| `BACKEND_PORT` | `8000` | Backend port |
| `DATABASE_URL` | `sqlite+pysqlite:///./ddacksaeu.db` | Database connection |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins |
| `LOG_LEVEL` | `INFO` | Backend log level |
| `DOCUMENT_UPLOAD_DIR` | `.document_uploads` | Private upload directory |
| `DOCUMENT_MAX_UPLOAD_BYTES` | `10485760` | Maximum CV upload size |

The application does not automatically load backend `.env` files. Environment variables must be set in the process environment. Docker Compose can use a local untracked `.env` file for variable interpolation.

For production, set a secure `OWNER_SESSION_SECRET` with at least 16 characters for the frontend session.

---

## Docker

From the repository root, set a PostgreSQL password and start the services.

### Windows PowerShell

```powershell
$env:POSTGRES_PASSWORD = "<local-development-password>"
docker compose up --build
```

### macOS or Linux

```bash
export POSTGRES_PASSWORD="<local-development-password>"
docker compose up --build
```

The backend container applies Alembic migrations before starting Uvicorn.

---

## API Overview

The backend API is versioned under:

```text
/api/v1
```

Main API groups include:

| API Group | Purpose |
| --- | --- |
| Authentication | User registration, login, and session-related functions |
| Profile | User profile and preferences |
| Laboratories | Lab search and lab detail information |
| Documents | CV upload, analysis, latest result, and history |
| Recommendations | Saved recommendation results and recomputation |
| Saved Labs | Save or remove laboratories |
| Email Drafts | Prepare contact email drafts |
| Admissions | Admission events and ICS export |
| Health | Backend status check |

The frontend accesses the FastAPI backend through:

```text
/api/backend/*
```

For example:

```text
http://localhost:3000/api/backend/health
```

---

## CV Data and Privacy

Uploaded CV files are stored with a random private storage key.

The backend does not save the full extracted CV text as a database field. It saves the structured analysis result and derived keyword search text.

CV text should not be written to application logs.

This project does not send CV data to an external AI service in the current version.

---

## Recommendation Details

The recommendation result is deterministic. Running the same version with the same data should produce the same result.

If one score component has no available data, that component receives zero and the response includes a warning. The remaining score weights are not automatically increased.

Recommendation evidence may include:

- matched research terms
- missing research terms
- CV-to-lab similarity
- recent publication evidence
- user preference evidence
- data origin
- data freshness
- a suggested next action

Crawler-imported laboratories and fixture laboratories use the same recommendation fields.

Recommendation weights can be changed in:

```text
backend/app/config/recommendation_weights.py
```

The total weight must remain 100.

---

## Data Import Notes

The POSTECH importer validates crawler records before adding them to the database.

Records may be skipped when they have problems such as:

- invalid URLs
- missing or invalid names
- invalid departments
- duplicated professor and laboratory pairs
- invalid publication years
- publications connected to excluded laboratories

The importer creates a report in:

```text
import_reports/
```

Only publication records are currently added to the paper table. Presentations, patents, and books remain in the raw crawler data because the recommendation system currently uses publication text.

Before importing real data into a production database, run a dry run and create a backup.

---

## Admission Data

The admission API supports source-labeled events and ICS export.

No real admission schedule is guaranteed by the fixture data.

Verified admission data can be imported after checking an official university source. A dry run should be completed before the real import.

Users should always confirm important deadlines on the official university or department website.

---

## Testing

### Backend

Run these commands from `backend`:

```bash
ruff format --check .
ruff check .
pytest
```

Backend tests use SQLite and do not require network access.

### Frontend

Run these commands from `frontend_v2`:

```bash
npm test
npm run lint
npx tsc --noEmit
npm run test:e2e
```

For the release smoke test:

```bash
npm run test:e2e:release
```

The release smoke test requires the frontend and backend to be running with the required environment variables.

---

## Current Limitations

This is still an MVP and there are several limitations.

- CV analysis is rule-based.
- OCR is not supported.
- Image-only PDFs cannot be analyzed.
- Recommendation quality depends on the available keywords and publication data.
- Some datasets are fictional fixtures for development.
- Admission information must be checked manually before it is treated as official.
- Contact email drafts must be reviewed before use.
- The current crawler mainly focuses on POSTECH data.
- The project does not support every university yet.

---

## Future Work

Possible next steps include:

- improving research keyword normalization
- adding semantic search
- supporting more universities
- expanding verified crawler data
- improving professor and publication matching
- adding better recommendation feedback
- supporting more CV layouts
- adding optional OCR support
- improving contact email personalization
- adding deployment monitoring and automated releases

---

## Development Notes

The root README gives a general overview of the project.

More detailed instructions are available in:

- `backend/README.md`
- `frontend_v2/README.md`
- `docs/`

When changing an API contract, update both the backend implementation and the frontend BFF route.

---

## Disclaimer

Ddacksaeu is a student project made to support graduate school research and application preparation.

Recommendation results are only supporting information. Users should review the original laboratory page, professor page, publication source, and official admission page before making a decision.

The project does not guarantee admission, professor availability, recruitment status, or the accuracy of externally collected information.

---

## License

No open-source license has been added yet.

Unless a license file is added, the source code remains under the repository owner's default copyright.
