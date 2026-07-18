# 프론트엔드-백엔드 연결 매핑

조사 기준은 현재 `frontend/src` 구현이다. `frontend/`는 이번 설계 단계에서 수정하지 않는다. `mock-data.ts`의 모든 연구실, 교수, 이메일, 논문, 일정은 **fixture/mock**이며 실존 정보로 가정하지 않는다.

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
