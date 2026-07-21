# Ddacksaeu

**Find research labs that match your background and understand why they match.**

Ddacksaeu is a graduate-school preparation web service that connects professor and lab search, local CV analysis, explainable recommendations, outreach email drafting, and admission planning in one workflow.

> Built for OpenAI Build Week 2026 with Codex and GPT-5.6.

---

## Why We Built It

Graduate-school applicants often need to compare department pages, lab websites, professor profiles, publication lists, and admission deadlines separately. Even after collecting the information, it is still difficult to answer one practical question: **How well does my background match this lab, and what should I do next?**

Ddacksaeu was built around three principles:

1. recommendations should include visible evidence;
2. missing or unverified information should not be guessed;
3. each result should lead to a useful next step.

---

## Main User Flow

```text
1. Sign in and complete a research profile
2. Upload a CV
3. Review the local CV analysis
4. Search professors and laboratories
5. Generate explainable research matches
6. Save promising professors
7. Prepare and review a personalized outreach email
8. Organize admission deadlines
```

---

## What Makes Ddacksaeu Different

### Explainable Research Matching

Each recommendation is divided into weighted components instead of returning only a general statement.

Users can review matched and missing terms, CV similarity, publication evidence, user preference evidence, data origin, data freshness, and a suggested next action.

The score is presented as **research overlap**, not admission probability.

### Deterministic Scoring

The recommendation engine uses local keyword normalization, TF-IDF, cosine similarity, lexical overlap, publication matching, user preferences, and data freshness.

The same data and code version produce the same ranking, making the results easier to compare and inspect.

### Source-Aware Data

Professor and lab records can include their origin and source information. The application does not treat unverified recruitment status or fixture admission dates as official.

### Local CV Processing

CV analysis runs on the backend without sending CV text to an external AI service. The backend stores a structured result and derived search information rather than the complete extracted CV text as a normal database field.

---

## Main Features

### Professor and Laboratory Search

Users can review:

- university and department
- professor and laboratory
- research field and keywords
- recent publications
- laboratory homepage
- source information

The backend supports fictional fixture data for development and a separate validated POSTECH crawler import.

### CV Analysis

Authenticated users can upload:

- PDF
- DOCX
- TXT

The maximum file size is 10 MB.

The analyzer extracts structured information such as research interests, skills, education-related sections, experience, projects, and keywords used for matching.

The current analyzer is local and rule-based. OCR is not included, so scanned or image-only PDF files are not supported.

### Explainable Lab Recommendations

After a CV analysis is completed, users can receive laboratory recommendations.

| Component | Weight |
| --- | ---: |
| Research keyword match | 35 |
| CV and lab similarity | 30 |
| Recent publication relevance | 20 |
| User preference match | 10 |
| Data freshness | 5 |
| **Total** | **100** |

If one component has no usable data, that component receives zero and the response includes a warning. The remaining weights are not silently redistributed.

Recommendation weights are defined in:

```text
backend/app/config/recommendation_weights.py
```

### Saved Professors and Labs

Signed-in users can save professors or laboratories and review them later. Saved items are connected to the user account through the backend API.

### Personalized Outreach Email

After selecting a laboratory, users can generate a personalized outreach email draft.

The draft uses:

- professor and laboratory information
- the user's profile
- research interests
- relevant skills and project experience
- recent publications related to the selected laboratory

The generated email includes a subject, greeting, research background, motivation, and closing message.

Users can edit the draft before copying or sending it.

### Admission Calendar

Admission events can be filtered by date range, university, department, and event type. The backend also supports ICS export.

Real deadlines should only be imported after checking an official university or department source.

### Dashboard and Profile

The frontend includes sign-in, account setup, research profile, CV analysis history, lab search, recommendation results, saved professors, outreach drafts, admission planning, and readiness tracking.

---

## How We Used Codex and GPT-5.6

Codex was used throughout implementation rather than only for code completion.

```text
1. Inspect the existing repository
2. Identify the files connected to a feature
3. Break the feature into smaller changes
4. Implement or update the code
5. Review modified files
6. Run linting and tests
7. Fix integration problems
8. Verify the complete frontend-backend flow
```

Codex helped with repository navigation, API routes, frontend-backend integration, Pydantic schemas, SQLAlchemy models, Alembic migrations, crawler validation, CV processing, recommendation evidence, email drafting and review logic, error handling, testing, and documentation.

GPT-5.6 was used inside Codex for implementation support, debugging, review, and documentation.

The team reviewed AI-assisted changes, ran tests, corrected errors, and made the final product decisions.

### Runtime Note

GPT-5.6 was used during development.

The shipped CV analyzer, recommendation engine, and email tools do not call GPT-5.6 or the OpenAI API at runtime. They use local parsing, deterministic scoring, and controlled rule-based generation.

More details are available in `docs/OPENAI_USAGE.md`.

---

## Build Week Implementation Highlights

The Build Week submission demonstrates a connected workflow across the frontend, backend, database, and local processing services.

Key implementation areas include:

- frontend and FastAPI integration
- authenticated user flows
- PDF, DOCX, and TXT CV processing
- explainable recommendation scoring
- professor, lab, and publication data handling
- POSTECH crawler import validation
- personalized bilingual outreach drafts
- outreach email review and scoring
- admission filtering and ICS export
- backend, frontend, and end-to-end tests

---

## Architecture

```text
User Browser
     |
     v
Next.js 16 Frontend
     |
     | /api/backend/*
     v
Next.js BFF Routes
     |
     v
FastAPI Backend
     |
     +-- Authentication
     +-- User Profile
     +-- CV Upload and Analysis
     +-- Professor and Lab Search
     +-- Recommendations
     +-- Saved Items
     +-- Email Draft and Review
     +-- Admission Calendar
     |
     v
SQLAlchemy 2
     |
     +-- SQLite for local development and tests
     +-- PostgreSQL for Docker or production
```

The frontend uses a backend-for-frontend layer, so the backend authentication token is not stored directly in browser local storage.

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

---

## Running the Project Locally

Requirements:

- Python 3.11 or newer
- Node.js
- npm

Start the backend first.

### 1. Clone the Repository

```bash
git clone https://github.com/Ddacksaeu/Ddacksaeu_web.git
cd Ddacksaeu_web
```

### 2. Backend Setup

#### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

#### macOS or Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Apply migrations:

```bash
alembic upgrade head
```

Choose one data source.

#### Fictional Fixtures

```bash
python -m scripts.seed
```

#### POSTECH Crawler Data

```bash
python -m scripts.import_postech --dry-run
python -m scripts.import_postech --max-publications-per-lab 10
```

Do not mix fixtures and crawler data unless that is intentional.

Start the API:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Health check: `http://127.0.0.1:8000/api/v1/health`
- OpenAPI docs: `http://127.0.0.1:8000/api/v1/docs`

### 3. Frontend Setup

Open a second terminal from the repository root.

```bash
cd frontend_v2
npm install
```

Copy the environment file.

#### macOS or Linux

```bash
cp .env.example .env.local
```

#### Windows PowerShell

```powershell
Copy-Item .env.example .env.local
```

Set:

```env
BACKEND_API_ORIGIN=http://127.0.0.1:8000
```

Start the frontend:

```bash
npm run dev
```

Open `http://localhost:3000`.

For a production build:

```bash
npm run build
npm run start
```

---

## Environment Variables

| Variable | Example | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Application environment |
| `BACKEND_HOST` | `127.0.0.1` | Backend bind host |
| `BACKEND_PORT` | `8000` | Backend port |
| `DATABASE_URL` | `sqlite+pysqlite:///./ddacksaeu.db` | Database connection |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origin |
| `LOG_LEVEL` | `INFO` | Backend log level |
| `DOCUMENT_UPLOAD_DIR` | `.document_uploads` | Private CV upload directory |
| `DOCUMENT_MAX_UPLOAD_BYTES` | `10485760` | Maximum CV file size |
| `BACKEND_API_ORIGIN` | `http://127.0.0.1:8000` | Frontend-to-backend origin |
| `OWNER_SESSION_SECRET` | long random string | Frontend session secret |

Use a secure `OWNER_SESSION_SECRET` of at least 16 characters in production.

Do not commit passwords, API keys, private CVs, or production secrets.

---

## Database Reset

From `backend`, stop the server and delete the local SQLite file.

### Windows PowerShell

```powershell
Remove-Item .\ddacksaeu.db
```

### macOS or Linux

```bash
rm ddacksaeu.db
```

Recreate and seed:

```bash
alembic upgrade head
python -m scripts.seed
```

### Docker with PostgreSQL

From the repository root:

```powershell
$env:POSTGRES_PASSWORD = "<local-development-password>"
docker compose up --build
```

On macOS or Linux:

```bash
export POSTGRES_PASSWORD="<local-development-password>"
docker compose up --build
```

---

## Sample CV

Save this as `sample_cv.txt` and upload it from the profile or CV page.

```text
Eilleen An
Computer Science Student

EDUCATION
Bachelor of Science in Computer Science
Expected Graduation: May 2029

RESEARCH INTERESTS
Machine Learning, Computer Vision, Human-Computer Interaction

EXPERIENCE
Research Assistant
Developed an OpenCV-based defect detection pipeline for 3D-printed food structures.
Worked with image segmentation, contour analysis, morphology, ROI detection, and JSON-based configuration.

PROJECTS
Graduate Lab Discovery Platform
Built a Next.js and FastAPI application for CV analysis, lab search, recommendations, and email drafting.

SKILLS
Python, TypeScript, React, Next.js, FastAPI, OpenCV, SQL, Git
```

---

## API Overview

The backend API is versioned under `/api/v1`. The frontend accesses it through `/api/backend/*`.

| API Group | Purpose |
| --- | --- |
| Authentication | Registration, login, and access |
| Profile | User profile and research preferences |
| Laboratories | Search and detail information |
| Documents | CV upload, analysis, latest result, and history |
| Recommendations | Results and recomputation |
| Saved Items | Saved professors and laboratories |
| Email | Draft generation and draft review |
| Admissions | Events and ICS export |
| Health | Backend status |

Important endpoints:

```text
GET  /api/v1/health
POST /api/v1/documents/analyze
GET  /api/v1/documents/latest
GET  /api/v1/documents
GET  /api/v1/recommendations
POST /api/v1/recommendations/recompute
POST /api/v1/email/draft
POST /api/v1/email/review
GET  /api/v1/admissions
GET  /api/v1/admissions/export.ics
```

Current schemas are available at `http://127.0.0.1:8000/api/v1/docs`.

---

## Testing

### Backend

```bash
cd backend
ruff format --check .
ruff check .
pytest
```

### Frontend

```bash
cd frontend_v2
npm test
npm run lint
npx tsc --noEmit
npm run test:e2e
```

Release smoke test:

```bash
npm run test:e2e:release
```

---

## Known Limitations

Ddacksaeu is still an MVP.

- CV analysis is rule-based.
- OCR is not supported.
- Image-only PDFs cannot be analyzed.
- Recommendation quality depends on available keywords and publication data.
- Email generation is controlled and template-based rather than generative.
- Email review focuses on mechanical quality, personalization signals, structure, and clear requests.
- Some development datasets are fictional fixtures.
- Admission information must be checked against an official source.
- The crawler mainly focuses on POSTECH.
- The project does not support every university.
- Research-match scores are not admission predictions.
- Professor availability and recruitment status can change.

---

## Future Work

- improve keyword normalization
- add semantic search
- support more universities
- expand verified crawler data
- improve professor and publication matching
- support more CV layouts
- add optional OCR
- add more flexible outreach email controls
- improve email tone and clarity analysis
- add deployment monitoring
- add automated release checks

---

## Disclaimer

Ddacksaeu is a student project for graduate-school research and application preparation.

Recommendations and email suggestions are supporting information only. Before making a decision or contacting a professor, users should review the original lab page, professor page, recent publications, official admission page, final email content, and attachments.

The project does not guarantee admission, professor availability, recruitment status, or the accuracy of information collected from outside sources.

---

## License

No open-source license has been added yet.

Unless a license file is added, the source code remains under the repository owner's default copyright.
