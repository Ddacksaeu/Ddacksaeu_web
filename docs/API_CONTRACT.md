# API 계약 초안

기본 경로는 `/api/v1`이다. MVP는 인증 대신 서버가 `demo-user` 컨텍스트를 사용한다. 실제 로그인·사용자 ID를 프론트가 전달하는 방식은 **해커톤 이후 구현 또는 확장**으로 미룬다.

모든 오류 응답은 `{ "error": { "code": "...", "message": "..." } }` 형식이며, 검증 실패는 `422`, 존재하지 않는 리소스는 `404`, 파일 형식/크기 위반은 `413` 또는 `415`를 사용한다. 성공 응답의 시각은 ISO 8601 UTC이고, 일정 날짜는 `YYYY-MM-DD`다.

## MVP에서 바로 구현

### 연구실 탐색

| API | 용도 | 핵심 요청/응답 |
| --- | --- | --- |
| `GET /labs` | 탐색 화면 목록 | query: `q`, `department`, 반복 `field`, `sort=recent\|name`, `page`, `page_size`; response: `{ items: LabListItem[], page, pageSize, total }` |
| `GET /labs/{lab_id}` | 상세 화면 | response: `LabDetail`과 `source` 메타데이터 |
| `GET /labs/{lab_id}/similar` | 상세의 유사 연구실 | response: `{ items: LabListItem[] }`; 동일 분야를 우선하되 근거가 없으면 빈 목록 |

`LabListItem`은 `id`, `name`, `professorName`, `department`, `field`, `summary`, `keywords`, `recentTopics`, `homepageUrl`, `updatedAt`, `dataQuality`를 포함한다. 목록 API는 사용자별 추천 점수를 포함하지 않는다.

`LabDetail`은 목록 필드에 `location`, `contactEmail`, `papers`, `members`, `requirements`, `facts[]`를 더한다. 각 `facts[]`와 `papers[]`는 `sourceUrl`, `sourceCheckedAt`, `origin`을 포함하며, 이메일·논문·위치가 검증되지 않았으면 `null` 또는 빈 배열이다.

### 프로필, 관심 연구실, 일정

| API | 용도 | 핵심 요청/응답 |
| --- | --- | --- |
| `GET /me/profile` | 프로필 초기 로드 | `UserProfile` |
| `PATCH /me/profile` | 프로필 저장 | 변경 가능한 이름·소속·상태·과정·문자열 목록; 저장된 `UserProfile` |
| `GET /me/favorites` | 관심 목록 | `{ labIds: string[] }` |
| `PUT /me/favorites/{lab_id}` | 관심 저장 | `204` |
| `DELETE /me/favorites/{lab_id}` | 관심 해제 | `204` |
| `GET /me/calendar-events` | 일정 목록 | query: `from`, `to`; `{ items: CalendarEvent[] }` |
| `POST /me/calendar-events` | 일정 생성 | `title`, `kind`, `date`, nullable `labId`, nullable `memo`; 생성 이벤트 |
| `DELETE /me/calendar-events/{event_id}` | 일정 삭제 | `204` |

`UserProfile`은 프론트와 같은 `name`, `affiliation`, `status`, `program`, `interests`, `skills`, `methodologies`, `projects`를 반환한다. `CalendarEvent`는 `id`, `title`, `kind`, `date`, optional `labId`, optional `memo`를 반환한다.

### CV 분석과 추천

| API | 용도 | 핵심 요청/응답 |
| --- | --- | --- |
| `POST /me/documents` | CV/자소서 업로드 | `multipart/form-data`의 `file`; PDF/DOCX, 최대 10MB; `{ documentId, status: "uploaded" }` |
| `POST /me/document-analyses` | 업로드 문서 분석 | `{ documentId }`; MVP는 짧은 요청만 동기로 처리하고 `{ analysisId, status, analysis }` 반환 |
| `GET /me/document-analyses/latest` | 프로필의 최근 분석 결과 | 최신 성공 분석 또는 `204 No Content` |
| `POST /me/recommendations` | 프로필·분석 기반 추천 | optional `{ analysisId }`; `{ items: Recommendation[], insufficientData }` |

`analysis`는 `keywords`, `skills`, `methodologies`, `projects`, `completeness`, `origin`을 포함한다. `origin`이 `llm_generated`이면 추출 사실이 아닌 제안임을 UI가 표시한다. 분석 실패는 부분 mock을 만들지 않고 `status=failed`와 오류 코드를 반환한다.

`Recommendation`은 `{ lab, score, scoreStatus, reasons, missingTerms, scoringVersion }`이다. `lab`에는 목록 정보만 들어가며 `score`를 연구실 원본 필드에 섞지 않는다. `reasons`는 실제로 겹친 키워드·분야만 반환하고, `missingTerms`는 구조화된 연구실 태그가 있어 비교 가능한 경우에만 반환한다.

추천 점수 v1은 다음처럼 계산한다.

- 정규화한 프로필 관심사와 CV 키워드의 실제 겹침: 최대 70점.
- 연구실 `field`가 프로필 관심사와 직접 일치: 20점.
- 구조화된 지원 역량 태그와 사용자의 기술 일치: 최대 10점.
- 태그가 없는 연구실 또는 관심사·CV 키워드가 모두 없는 프로필은 `score=null`, `scoreStatus="insufficient_data"`으로 반환한다. 임의의 기본 점수는 만들지 않는다.
- 동점은 마지막 확인 시점 내림차순, 이후 이름순이다. `scoringVersion`을 함께 반환해 규칙 변경을 추적한다.

### 컨택 이메일 초안

| API | 용도 | 핵심 요청/응답 |
| --- | --- | --- |
| `POST /labs/{lab_id}/email-drafts` | 편집 가능한 초안 생성 | `{ language, tone, length, purpose }`; `{ subject, body, generationMode, sourceFactIds, warning }` |

MVP는 서버의 검증된 연구실 사실과 사용자 프로필만으로 템플릿 초안을 생성한다. 서버에 LLM 키가 안전하게 설정된 경우에도 `generationMode="llm_generated"`와 사용한 `sourceFactIds`를 반환하고, 키가 없거나 호출에 실패하면 `generationMode="template"`으로 안전하게 대체한다. 메일 발송 API는 제공하지 않는다.

## 해커톤 이후 구현 또는 확장

- OAuth/세션, 실제 사용자 인증, 권한 검사.
- 연구실 CRUD·수집 실행 API, 운영자 권한, 크롤링 상태 조회.
- 비동기 문서 분석의 작업 ID·폴링/SSE, 대용량 파일, 외부 스토리지 signed URL.
- 추천 이력 저장, 피드백, 개인별 재학습.
- 맞춤법·문체·중복·요약·번역 등 이메일 AI 도구별 API와 초안 저장 이력.
- 실제 메일 전송 및 첨부 전달. 발송 책임·동의·보안 요구가 커서 MVP에서 제외한다.

## 프론트 반영 원칙

TanStack Query를 데이터 로딩·재시도·캐시 무효화에 사용한다. API 키와 LLM 호출은 브라우저에서 하지 않는다. 상태 코드는 `loading`, `success`, `empty`, `error`를 화면별로 명시적으로 렌더링하며, 서버 오류 시 기존 mock 결과로 조용히 대체하지 않는다.
## Data foundation status (2026-07-18)

No new HTTP routes are implemented in this revision. Future lab filters will
be sourced from normalized university, department, professor, and keyword
records. Future recommendation responses will expose the persisted score
breakdown and reason from `recommendations`; these are fixture data only until
a separately scoped calculation service is implemented. Crawl and admission
tables are provenance records and do not enable crawling or admission APIs.
