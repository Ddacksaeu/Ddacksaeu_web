# OpenAI, Codex, and GPT-5.6 Usage

## Overview

This project used Codex as a development assistant. GPT-5.6 was the model used
inside those Codex-assisted development sessions. This is separate from the
running Dacksaeu product: the repository contains no direct OpenAI API,
GPT-5.6, LLM, or embedding call site in the application code. The CV-analysis
and recommendation flows are deterministic server-side implementations.

The team remained responsible for requirements, data-model and product
decisions, code review, correction, testing, release checks, and the final
submission. AI-generated suggestions were never treated as final without
human inspection.

## How Codex Was Used

### Repository inspection and planning

Codex helped inspect the monorepo and trace existing interfaces before changes
were made. The main references were `docs/PROJECT_STRUCTURE.md`,
`docs/FRONTEND_BACKEND_MAPPING.md`, `backend/app/api/v1/`, and the
`frontend_v2/src/features/` modules. This work established which responsibilities
belonged in the FastAPI backend, which belonged in the Next.js application,
and which existing Lovable UI surfaces should remain intact.

### Backend development

Codex assisted with implementation and review of the FastAPI API surface,
including document analysis (`backend/app/api/v1/documents.py` and
`backend/app/services/document_analysis/`), recommendations
(`backend/app/api/v1/recommendations.py` and
`backend/app/services/recommendations.py`), email drafts, and the POSTECH
importer. The team chose an explainable scoring design with fixed weights in
`backend/app/config/recommendation_weights.py` and explicit unavailable-data
warnings rather than score reweighting.

### Frontend-backend integration and debugging

Codex helped connect browser flows to the backend through
`frontend_v2/app/api/backend/[...path]/route.ts`. The BFF reads the session
server-side and forwards authorization to FastAPI so the browser does not hold
the backend bearer token. It also preserves multipart upload bodies and
upstream error responses, and returns a distinct `503` when the backend cannot
be reached. Related coverage is in
`frontend_v2/src/features/profile/backend-documents-route.test.ts`.

### Testing, validation, and documentation

Codex assisted in reading and improving targeted test coverage, including
`backend/tests/test_document_analysis.py`, `backend/tests/test_recommendations.py`,
and `frontend_v2/tests/e2e/release-smoke.spec.ts`. It also helped reconcile
implementation behavior with the frontend/backend mapping, security notes,
README, and this submission documentation.

## How GPT-5.6 Was Used

### GPT-5.6 inside Codex

GPT-5.6 supported the Codex-assisted development work described above:
repository analysis, implementation suggestions, debugging hypotheses, test
interpretation, and documentation drafting. It was a development tool, not an
autonomous owner of the project.

### GPT-5.6 or OpenAI API inside the product

Neither GPT-5.6 nor an OpenAI API is directly called by the shipped application
flows in this repository. A source search finds no OpenAI client or API-call
implementation under `backend/` or `frontend_v2/`. In particular, the CV
result UI states that analysis is local to the server, and the backend README
describes local parsing and keyword rules rather than a paid external API.

### Features that do not depend on GPT-5.6

- CV analysis uses local document-text extraction, section parsing, controlled
  vocabulary, and deterministic feedback rules.
- Recommendations use normalized keyword overlap, scikit-learn TF-IDF,
  explicit preference checks, and freshness thresholds.
- The BFF, authentication/session behavior, saved labs, calendar/ICS export,
  and email-draft API do not require GPT-5.6 or an OpenAI key.

## Representative Development Examples

### Explainable recommendations

- **Problem:** A recommendation needed to be understandable and safe when a
  lab or CV lacks source data.
- **How Codex/GPT-5.6 helped:** It assisted with reviewing the scoring service
  and its component breakdown in `backend/app/services/recommendations.py`.
- **Human review or correction:** The team fixed the rubric at 35/30/20/10/5,
  required weights to total 100, and chose zero plus a warning for unavailable
  components instead of reallocating weight.
- **Final verified result:** `backend/tests/test_recommendations.py` checks the
  total, normalization, freshness thresholds, and CV-required API behavior.

### CV upload through the BFF

- **Problem:** The browser needed to upload a CV through a same-origin route
  without exposing backend credentials or losing validation errors.
- **How Codex/GPT-5.6 helped:** It assisted in tracing the request path and
  reviewing the proxy behavior.
- **Human review or correction:** The team retained the BFF boundary, forwarded
  multipart requests unchanged, and preserved upstream status codes.
- **Final verified result:** The BFF test verifies the forwarded Bearer token,
  multipart body, `422` propagation, and safe `503` fallback.

### Release-flow validation

- **Problem:** Individual APIs could pass tests while the supported applicant
  journey still failed across pages.
- **How Codex/GPT-5.6 helped:** It assisted with inspecting the end-to-end
  workflow and its dependencies.
- **Human review or correction:** The team kept a focused release smoke suite
  rather than treating legacy visual-demo tests as release evidence.
- **Final verified result:** `frontend_v2/tests/e2e/release-smoke.spec.ts`
  covers sign-up, CV analysis, recommendations, saved labs, an outreach draft,
  calendar changes, ICS export, and sign-out.

## Verification and Guardrails

- Team members manually reviewed and corrected AI-assisted changes.
- Backend tests cover deterministic document analysis and recommendation
  behavior; frontend tests cover BFF routing; the Playwright release smoke test
  covers the supported end-to-end flow.
- The repository documents lint and test commands in `README.md` and
  `backend/README.md`.
- The application does not place server-only credentials in frontend code.
- Recommendation evidence and data-origin labels distinguish source-backed
  facts from unavailable information; the recommendation flow does not send
  CV data to an OpenAI service.
- This document was checked against the current code paths and repository
  history; it does not claim product-side GPT-5.6 or OpenAI API use.

## Limitations

The repository records code and tests, not a complete transcript of every
Codex conversation or every intermediate suggestion. It therefore documents
the verified development areas and implementation outcomes rather than
attributing every individual line of code to an AI tool. No product-side
OpenAI API fallback, demo mode, or API-call telemetry is documented because no
such integration exists in the current codebase.

## Codex Feedback Session

The representative `/feedback` Codex Session ID is provided separately through
the Devpost submission form.
