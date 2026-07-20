# 프론트엔드-백엔드 연결 매핑

조사 기준은 현재 `frontend/src` 구현이다. `frontend/`는 이번 설계 단계에서 수정하지 않는다. `mock-data.ts`의 모든 연구실, 교수, 이메일, 논문, 일정은 **fixture/mock**이며 실존 정보로 가정하지 않는다.

## Authentication update (MVP, 2026-07-18)

Personal routes use the authenticated JWT subject, never a client-supplied `user_id`.
`POST /auth/signup` accepts `email`, `password`, and `name`; `POST /auth/login` accepts
`email` and `password`; both return a bearer token. The frontend stores this session locally
and attaches `Authorization: Bearer <token>` through its shared API client. `/me`, document
analysis, recommendations, and email-draft requests require this token. Lab discovery stays
public, but only an authenticated request receives that user's favorite/recommendation fields.

| Frontend surface | API | Identity source |
| --- | --- | --- |
| `/login`, `/signup` | `POST /auth/login`, `POST /auth/signup` | Returned JWT |
| `/profile`, `/favorites`, `/calendar` | `/me/*` | JWT `sub` |
| `/recommendations` | `POST /documents/analyze`, `/recommendations/*` | JWT `sub` |
| `/lab/$id/email` | `POST /email/draft` | JWT `sub` |

## Frontend_v2 authentication and lab discovery integration (planned)

`frontend_v2` is the Next.js UI selected for the next integration slice. It
uses server-side route handlers as a BFF: the backend JWT is stored only in an
HttpOnly same-site cookie, and browser code calls `/api/backend/*` rather than
the FastAPI origin directly. This keeps the backend origin and bearer token out
of browser storage.

| Frontend_v2 surface | BFF route | Backend API |
| --- | --- | --- |
| Login and sign-up | `POST /api/auth/login`, `POST /api/auth/signup` | `POST /auth/login`, `POST /auth/signup` |
| Sign-out | `POST /api/auth/logout` | Clears local session cookie only |
| Professor search | `GET /api/backend/labs` | `GET /labs` |
| Professor detail | `GET /api/backend/labs/{id}` | `GET /labs/{id}` |
| Saved professors | `GET`, `PUT`, `DELETE /api/backend/me/favorites/*` | `/me/favorites/*` |

The existing owner-cookie `/api/profile`, CV, calendar, and contact draft
flows remain separate until their API contracts are migrated in later slices.

## Frontend_v2 complete user flow (2026-07-19)

`frontend_v2` now uses the existing `/api/backend/[...path]` BFF for all
personal API calls. The browser never receives the backend JWT: the BFF reads
the HttpOnly session cookie and forwards a Bearer header server-side. A `401`
is preserved for the UI to direct the user to `/login`; it is never converted
into an empty result.

| Surface | BFF route | Backend API | Notes |
| --- | --- | --- | --- |
| Profile | `/api/backend/me/profile` | `GET`, `PATCH /me/profile` | Only API-defined profile fields are editable. |
| Latest CV | `/api/backend/documents/latest` | `GET /documents/latest` | A 404 means no analysis yet. |
| Saved labs | `/api/backend/me/favorites` | `GET /me/favorites` | Lab details are fetched from the real lab catalogue. |
| Personal dates | `/api/backend/me/calendar-events` | `GET`, `POST /me/calendar-events`; `PATCH`, `DELETE /me/calendar-events/{id}` | User-owned events are validated and persisted. |
| Admissions | `/api/backend/admissions` | `GET /admissions` | Empty data stays empty; no display fixture is substituted. |
| ICS export | `/api/backend/admissions/export.ics` | `GET /admissions/export.ics` | BFF preserves calendar content type and download disposition. |
| Contact draft | `/api/backend/email/draft` | `POST /email/draft` | Generates an editable draft only; it never sends email. |

## 현재 라우트와 필요한 API

| 화면 | 현재 데이터·상태 | MVP에서 바로 구현할 API | 해커톤 이후 구현 또는 확장 |
| --- | --- | --- | --- |
| Backend foundation | No frontend integration in this stage | `GET /api/v1/health` only | Existing resource APIs remain planned; frontend keeps fixture/mock state |
| `/` 연구실 탐색 | `LABS`를 브라우저에서 검색·필터·정렬 | `GET /labs` | 서버 전문 검색, 무한 스크롤 |
| `/lab/$id` 상세 | loader가 `LABS.find`, 유사 연구실도 브라우저 계산 | `GET /labs/{lab_id}`, `GET /labs/{lab_id}/similar`, 관심/일정 API | 서버 비교·관련 논문 탐색 |
| `/recommendations` | `DEMO_CV`, 타이머, `LABS` 점수 계산 | 문서 업로드·분석·추천 API | 분석 작업 폴링/SSE, 추천 이력 |
| `/favorites` | 전역 메모리 `favorites`, `compareIds` | 관심 목록 조회·저장·해제 | 비교 조합 저장·공유 |
| `/calendar` | 전역 메모리 `INITIAL_EVENTS` | 일정 목록·생성·삭제 | 학교 공식 일정 수집·알림 |
| `/profile` | 전역 메모리 `USER_PROFILE`, `cv` | 프로필 조회·수정, `GET /me/document-analyses/latest` | 실제 계정·다중 기기 동기화 |
| `/lab/$id/email` | `makeDraft`, `makeCorrections`, 타이머 기반 AI 도구 | 템플릿/선택적 LLM 초안 생성만 | 맞춤법·문체·번역·초안 저장, 실제 첨부·발송 |

현재 UI에 **없는 것으로 확인된 기능**: 로그인·회원가입, 실제 메일 발송, 실제 파일 업로드/저장, 실제 크롤링, 서버 API 호출, 서버 측 페이지네이션, 공식 입시 일정 데이터, 알림, 추천 이력. 이 기능들은 존재한다고 가정하지 않는다.

## Mock 필드와 제안 DB 필드

| 현재 mock 타입/필드 | 제안 API 필드 | 제안 DB 위치 | 비고 |
| --- | --- | --- | --- |
| `Lab.id` | `id` | `labs.id` | 안정적인 slug 유지 |
| `name`, `professor`, `department`, `field` | `name`, `professorName`, `department`, `field` | `labs` | API는 camelCase, DB는 snake_case |
| `summary` | `summary`, `summaryOrigin` | `labs.summary_text`, `summary_origin` | LLM 요약 여부를 노출 |
| `keywords`, `recentTopics`, `requirements` | 동일한 배열 | `lab_facts` | 각 값의 출처 보존 |
| `members` | `{ professor, phd, ms }` | `lab_facts` | `member_count` 사실을 조립 |
| `homepage`, `location`, `email`, `updatedAt` | `homepageUrl`, `location`, `contactEmail`, `updatedAt` | `labs` | 검증 전에는 null |
| `papers[]` | `papers[]` + 출처 메타 | `papers` | MVP는 `papers.lab_id` 단일 연결 |
| `UserProfile.*` | `UserProfile.*` | `user_profiles` | 배열은 순서를 보존 |
| `CalendarEvent.*` | `CalendarEvent.*` | `calendar_events` | `kind` enum 검증 |
| `favorites: string[]` | `labIds: string[]` | `favorites` | 비교 선택은 UI 임시 상태 |
| `CVAnalysis` | `DocumentAnalysis` | `document_analyses` | 생성/추출 origin 포함 |

## 점수와 추천 근거

현재 점수는 서버 데이터가 아니다.

- `Lab.matchScore`는 fixture에 고정된 0~100 값이고, 탐색 카드·상세·비교 화면에서 그대로 보인다.
- `/recommendations`는 `40 + (키워드 일치 수 × 12) + round(Lab.matchScore × 0.3)`을 99점으로 제한해 별도 점수를 만든다.
- 상세 화면의 강조 키워드는 사용자 프로필이 아니라 `Computer Vision`, `Multimodal`, `Diffusion Model` 상수와 비교한다.

백엔드는 `Recommendation.score`와 실제 겹친 `reasons`, 비교 불가 항목 `missingTerms`, `scoreStatus`, `scoringVersion`을 반환한다. 프로필 또는 연구실 태그가 부족하면 `score=null`으로 두며 고정 점수나 추정 점수를 만들지 않는다. 목록 탐색 API에는 사용자별 점수를 넣지 않아 로그인 도입 후 캐시가 섞이지 않게 한다.

## 현재 타입과 API 응답의 불일치

- 프론트 `Lab`은 `matchScore`를 연구실 자체 속성으로 요구하지만, API의 점수는 사용자·분석별 추천 결과다. `Lab`과 `Recommendation`을 분리해야 한다.
- 프론트는 `professor`, `homepage`, `email`, `updatedAt`을 non-null 문자열로 가정한다. 검증 전 사실은 API에서 null일 수 있으므로 nullable 렌더링이 필요하다.
- 프론트 `CVAnalysis`에는 분석 출처, 상태, 문서 ID, 실패 정보가 없다. API 모델은 이를 반환한다.
- `CalendarEvent.id`는 현재 클라이언트 난수지만 서버는 안정적인 ID를 발급한다.
- `UserProfile`의 상태·과정은 현재 임의 문자열이므로 API enum/허용 목록과 정렬해야 한다.
- 이메일 화면은 `Lab`의 이메일과 논문이 항상 있다고 가정하고, 전화번호까지 초안에 하드코딩한다. 실제 API는 미확인 이메일을 null로 반환하고, 연락처는 프로필에 없는 한 생성하지 않는다.

## API 교체 대상 파일

| 파일 | 교체 내용 |
| --- | --- |
| `frontend/src/lib/mock-data.ts` | 실사용 `LABS`, `USER_PROFILE`, `INITIAL_EVENTS` 의존 제거; suggestion/label 같은 UI 상수만 유지 |
| `frontend/src/lib/app-state.tsx` | 메모리 프로필·관심·일정·CV 상태를 TanStack Query 데이터와 mutation으로 교체; 비교 선택만 로컬 유지 |
| `frontend/src/routes/index.tsx` | `GET /labs` 쿼리와 서버 필터·정렬·페이지네이션 연결 |
| `frontend/src/routes/lab.$id.tsx` | loader의 mock 조회를 상세·유사 API로 교체; 관심/일정 mutation 연결 |
| `frontend/src/routes/recommendations.tsx` | 가짜 업로드·타이머·점수 계산을 문서/분석/추천 요청으로 교체 |
| `frontend/src/routes/favorites.tsx` | 관심 목록 query와 저장/해제 mutation 연결 |
| `frontend/src/routes/calendar.tsx` | 이벤트 query와 생성/삭제 mutation 연결 |
| `frontend/src/routes/profile.tsx` | 프로필 query/mutation과 분석 결과 상태 연결 |
| `frontend/src/routes/lab.$id.email.tsx` | `makeDraft`를 초안 API로 교체; AI 보조 도구는 후속 API 도입 전 mock임을 유지 |
| `frontend/src/components/lab/LabCard.tsx` | `Lab`과 `Recommendation` 분리, null 출처/점수 상태 렌더링 |
| `frontend/src/components/layout/AppShell.tsx` | 하드코딩 사용자 카드 대신 프로필 query 결과 사용 |

## 화면별 상태 요구

| 화면 | 로딩 | 성공 | 빈 결과 | 오류 |
| --- | --- | --- | --- | --- |
| 탐색 | 필터 변경 시 카드 skeleton | 목록·총개수 | 현재의 필터 초기화 안내 유지 | 재시도와 검색 조건 유지 |
| 상세 | 상세 skeleton | 사실 출처·확인 시점과 함께 표시 | 해당 없음은 404 화면 | 오류 경계 외에 API 재시도 제공 |
| 추천 | 업로드/분석/추천 단계를 실제 상태로 표시 | 점수·근거·데이터 품질 표시 | 추천 불가 사유와 프로필 보완 안내 | 분석 실패 원인·재시도; mock 결과로 대체 금지 |
| 관심 | 카드 skeleton | 저장 목록 | 현재 빈 상태 유지 | 저장/해제 rollback과 toast |
| 캘린더 | 월 범위 skeleton | 일정 표시 | 현재 “예정된 일정 없음” 유지 | 생성/삭제 실패 시 입력·목록 복구 |
| 프로필 | 프로필 skeleton | 저장된 프로필·분석 결과 | 분석 없음 안내 유지 | 저장 실패 시 편집값 유지 |
| 이메일 | 초안 생성 spinner | 편집 가능한 초안과 생성 방식 표시 | 수신 이메일/사실 부족 안내 | 템플릿 대체 또는 명시적 재시도; 발송은 하지 않음 |

## 백엔드 구현 뒤 예상 프론트 수정

`frontend/` 변경은 후속 통합 작업에서만 수행한다. API 클라이언트와 응답 스키마를 추가하고, TanStack Query의 query key·mutation invalidation을 정한 뒤 위 교체 대상 파일을 단계적으로 수정한다. 특히 `Lab.matchScore` 제거와 nullable 연구실 사실 처리, 기존 mock 상태의 제거는 한 번에 검증한다.
## Database extension status (2026-07-18)

The database layer preserves the existing UI-facing `labs`, `favorites`,
`calendar_events`, and document tables while adding normalized institutional,
keyword, recommendation, crawl, and admission-event records. This is a data
foundation change only: the frontend remains unchanged and continues to use
its Lovable mock state until a later API-integration task.

| Frontend need | Database source | API status |
| --- | --- | --- |
| Lab university, department, professor filters | `universities`, `departments`, `professors`, `labs` | Planned |
| Korean/English interest terms and lab topics | `keywords`, `user_keywords`, `lab_keywords` | Planned |
| Per-user lab ranking with explanation | `recommendations` | Planned |
| Admission-calendar source records | `admission_events` | Planned |
| Crawl provenance and execution status | `crawl_sources`, `crawl_runs` | Planned |

`Lab.matchScore` in the current frontend mock is not persisted on `labs`.
Future API responses must read a user-specific `Recommendation` instead. All
records inserted by the development seed are explicitly fictional fixtures.

## POSTECH crawler import mapping (2026-07-19)

`Crawler/data/labs.csv` is the raw authoritative input for the catalogue:
`researcher_id -> professors.id`, `department_id -> departments.id`, and
`lab_id -> labs.id`. `research_summary`, `primary_field`, and semicolon-delimited
`keywords` populate the existing search/recommendation fields. The importer maps
`research_outputs.csv` only to `papers` because the current recommendation service
uses paper title, abstract/summary, and keyword text; source outputs are attached by
`lab_id`. Every imported lab and paper carries `source_url`, checked/crawled time,
`source_type=postech_csv`, an `import_batch_id`, and `validation_status=valid`.

`GET /api/v1/labs`, `GET /api/v1/labs/{id}`, and `GET /api/v1/labs/{id}/similar`
already query ORM entities rather than fixtures, so they use POSTECH data whenever
the selected database is imported. `GET /api/v1/recommendations` reads the same
labs, keywords, and limited recent papers without changing recommendation weights.
The raw catalogue has same-name professors in different departments, so the professor
identity constraint is `(university_id, department_id, name)` rather than university/name.

## Lab search API implementation (2026-07-18)

`GET /api/v1/labs` supports independent and composable `university`,
`department`, repeated `field`, `q`, `professor_name`, and `lab_name` filters.
The `q` filter matches lab, professor, field, summary, and Korean or English
keyword terms. It uses the MVP `demo-user` context to expose `isFavorite` and
the optional persisted `recommendationScore`, without deriving scores from
frontend fixture data.

Results accept `sort=score|recent`, `page`, and `page_size`, and return
`items`, `page`, `pageSize`, and `total`. `GET /api/v1/labs/{lab_id}` returns
the same list fields plus provenance-backed facts and papers. This is a
backend-only implementation; no frontend files are changed.

## Search and detail frontend integration (in progress, 2026-07-18)

This integration replaces only the research-lab explorer and detail-page mock
lookups. Profile, favorites, calendar, recommendations, and email state remain
separate work items, so their local UI state is not treated as persisted data.

| Frontend concern | API contract used in this task | Rendering rule |
| --- | --- | --- |
| Explorer search and filters | `GET /api/v1/labs?q=&department=&field=&sort=score|recent&page=&page_size=` | Filter changes preserve the current query; API loading, empty, and retry states are explicit. |
| Lab detail | `GET /api/v1/labs/{lab_id}` | Missing contact, homepage, facts, or papers are rendered as unavailable, not invented from mock data. |
| Similar labs | `GET /api/v1/labs/{lab_id}/similar?limit=3` | Server selects related labs using the same field first, then shared keyword terms; the current lab is never returned. |
| Match score | Nullable `recommendationScore` on a lab response | The UI shows a score only when the API supplied a persisted value. It never derives a score from fixture data. |
| Provenance | `sourceUrl`, `sourceCheckedAt`, fact and paper provenance | Fixture origins and verification timestamps remain visible to the user. |

The frontend uses `VITE_API_BASE_URL` (default
`http://127.0.0.1:8000/api/v1`) for this public API location. No server secret
or OpenAI key is exposed to the browser.

## Document-analysis API (2026-07-18)

The current frontend remains unchanged and has no live upload integration.
The backend now exposes `POST /api/v1/documents/analyze` as
`multipart/form-data` with required `user_id` and `file` fields. It accepts a
PDF CV or portfolio up to 10 MiB, rejects non-PDF, empty, scanned/no-text, and
text-insufficient files, keeps the original in a private server directory, and
returns a Pydantic-validated structured analysis. `OPENAI_API_KEY` and the
analysis prompt remain server-only. The existing schema stores the uploaded
document plus keywords, skills, research interests (as methodologies), and
projects; a later migration is required to persist every additional returned
analysis field for retrieval.

## Local CV structure, lab matching, and email review (2026-07-20)

The active `frontend_v2` flow uses deterministic server-side analysis and does
not require or call OpenAI. Uploaded PDF, DOCX, or TXT content is separated into
education, work experience, research experience, projects, skills, and research
interests. Only those structured fields and concise evidence snippets are shown;
the extracted full CV text is never returned to the browser.

| Frontend_v2 surface | BFF route | Backend API | Behavior |
| --- | --- | --- | --- |
| `/cv` | `/api/backend/documents/analyze` | `POST /documents/analyze` | Local section parsing, controlled-vocabulary keyword extraction, and category feedback. |
| `/cv` recommendations | `/api/backend/recommendations` | `GET /recommendations` | Ranks labs with normalized CV keywords, research interests, lab keywords, and available paper text. |
| `/contact` | `/api/backend/email/review` | `POST /email/review` | Reviews the user's current subject/body for mechanics, flow, and professor/lab fit; returns suggestions and a locally corrected draft but never sends it. |

The email draft endpoint remains available for a starter template. Both draft
and review work without a server API key; no secret is exposed to the frontend.

CV analysis additionally separates `work_experience` and
`campus_community_involvement` from research and project entries. Section
headings such as internships, leadership, volunteering, awards/activities,
publications, profile, and additional information are routed independently so
their text does not leak into the preceding section. Skills and research terms
are prioritized when they appear in explicit Skills, Interests, Research, or
Projects sections.

The local email draft service reads the authenticated user's latest structured
CV analysis and the selected lab's stored public data. It selects a recent
publication with the strongest lexical overlap, references the lab homepage
when one is available, and connects those facts to a real CV project or skill.
The response exposes the publication, homepage, and CV evidence used in
`personalizationNotes`; it never infers personality or claims that are absent
from sourced lab data.

## CV analysis and recommendation frontend integration (in progress, 2026-07-18)

The recommendation screen uses the MVP `demo-user` context until authentication
is introduced. Its browser workflow is synchronous and has no mock fallback:

1. Upload one text-based PDF (maximum 10 MiB) to
   `POST /api/v1/documents/analyze` using `multipart/form-data` with
   `user_id=demo-user`.
2. Render the returned structured analysis, clearly labelling it as an
   AI-generated extraction for user review.
3. Call `POST /api/v1/recommendations/recompute?user_id=demo-user`, then show
   server-provided score, confidence, matched/missing keywords, score
   breakdown, and action. A failed request displays its API error and offers a
   retry; it never substitutes demo results.

The frontend accepts only `.pdf` files for this flow because the current
backend intentionally rejects DOCX. The browser sends no OpenAI key and does
not persist the original document outside the selected upload request.

## Profile, favorites, and personal calendar integration (in progress, 2026-07-18)

The MVP continues to use the server-owned `demo-user` context. The frontend
must not send an arbitrary user identifier for these personal resources.

| UI state | API contract | Client behavior |
| --- | --- | --- |
| Profile | `GET /api/v1/me/profile`, `PATCH /api/v1/me/profile` | Load on app start; retain the edit value and report an error if a save fails. |
| Saved labs | `GET /api/v1/me/favorites`, `PUT` and `DELETE /api/v1/me/favorites/{lab_id}` | Optimistically update the heart, then roll back on failure. |
| Personal calendar | `GET /api/v1/me/calendar-events?from=&to=`, `POST /api/v1/me/calendar-events`, `DELETE /api/v1/me/calendar-events/{event_id}` | Replace the in-memory event list with server records; restore the event if deletion fails. |

Profile arrays preserve ordering. Calendar event `kind` is validated against the
existing UI event kinds, while `labId` and `memo` remain optional. Comparison
selection remains local-only because no server-side comparison collection is
defined yet.

## Admission calendar API implementation (2026-07-18)

`GET /api/v1/admissions` and `GET /api/v1/admissions/export.ics` are backend-only;
the frontend remains unchanged.
The legacy `admission_events` schema stored only `title`, a single
`event_date`, `source_url`, `source_checked_at`, and `origin`. The migration
preserves existing dates as UTC midnight and marks migrated fixture events as
estimated rather than presenting them as confirmed schedules.

The approved migration adds these fields:

| Required API field/function | Required persisted data |
| --- | --- |
| `event_type` filter | non-null, validated `event_type` |
| `start_at`, `end_at`, date ordering, deadline calculation, ICS DTSTART/DTEND | timezone-aware `start_at` and nullable `end_at` (or an explicit all-day date/range representation) |
| `application_url` | nullable `application_url` |
| `description` | nullable `description` |
| `is_estimated` | non-null boolean `is_estimated` |
| source and last-verification display | existing `source_url` and `source_checked_at`, exposed as `last_verified_at` |

The existing development admission record remains an explicitly fictional
fixture. No real dates, event types, URLs, descriptions, or estimate flags may
be inferred from it. After the schema migration, fixture seed rows must retain
`origin="fixture"` and be labelled as fixture data in every API response.

## Explainable CV recommendations (Phase 3, 2026-07-19)

`GET /api/v1/recommendations` is calculated for the authenticated user at
request time. It requires that user's latest completed local CV analysis; when
none exists it returns `409` and never reads another user's analysis. The
Next.js professor catalogue calls it through `GET /api/backend/recommendations`,
so the browser never receives the backend JWT.

The response is deliberately not persisted. Each item includes `total_score`,
matched and missing keywords, component scores, factual evidence, warnings,
data completeness, and the lab data origin. Component maxima are configured in
`backend/app/config/recommendation_weights.py`: keyword overlap 35, CV/lab
TF-IDF 30, recent-paper TF-IDF 20, preferences 10, and freshness 5.

Unavailable source data contributes zero to its own component and is reported
as unavailable; it is never silently redistributed. The implementation uses
only local normalization, scikit-learn TF-IDF, and rule templates. No LLM,
embedding API, or OpenAI API is called by this recommendation flow. Fixture
labs continue to work and are explicitly labelled in the response/UI.

## Previous recommendation API implementation (2026-07-18)

## frontend_v2 real POSTECH API connection (2026-07-19)

`frontend_v2` renders the lab catalogue, keyword search, lab detail, similar
labs, saved labs, and CV recommendations through the same-origin Next.js BFF.
The BFF reads the HTTP-only `ddacksaeu_session` cookie and forwards the Bearer
token server-side; no browser storage contains a token and
`BACKEND_API_ORIGIN` remains server-only.

| Surface | BFF route | Backend route | UI rule |
| --- | --- | --- | --- |
| Catalogue/search | `GET /api/backend/labs?q=&page=&page_size=` | `GET /api/v1/labs` | Explicit loading, empty, and retry states. |
| Detail | `GET /api/backend/labs/{lab_id}` | `GET /api/v1/labs/{lab_id}` | URL ID is used; 404 is a not-found page. |
| Similar labs | `GET /api/backend/labs/{lab_id}/similar` | `GET /api/v1/labs/{lab_id}/similar` | Empty data is informational. |
| Recommendations | `GET /api/backend/recommendations` | `GET /api/v1/recommendations` | Server scores and evidence are rendered unchanged; 409 means no analyzed CV. |
| Saved labs | `GET`, `PUT`, `DELETE /api/backend/me/favorites/*` | `/api/v1/me/favorites/*` | Failed mutations retain prior state. |
| Admission ICS | `GET /api/backend/admissions/export.ics` | `GET /admissions/export.ics` | The BFF preserves `Content-Type` and `Content-Disposition`; browser download names the file. |

The backend now exposes `GET /api/v1/recommendations` for persisted results
and `POST /api/v1/recommendations/recompute` for explicit refresh. The Lovable
frontend remains unchanged. The response keeps labs separate from per-user
scores and provides score breakdown, evidence, confidence, matched/missing
terms, and a template action for later integration.
