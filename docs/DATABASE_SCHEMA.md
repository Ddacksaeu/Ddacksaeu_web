# 데이터베이스 스키마 설계

## 범위와 원칙

현재 `frontend/src/lib/mock-data.ts`의 연구실·사용자·일정 값은 모두 **mock/fixture**다. 특히 교수 이메일, 논문, 입시 일정, 학교 정보는 실데이터로 이관하지 않으며, 출처가 확인된 데이터만 운영 DB에 넣는다.

| 결정 | MVP에서 바로 구현 | 해커톤 이후 구현 또는 확장 | MVP에 적합한 이유 |
| --- | --- | --- | --- |
| 사용자 식별 | 고정 `demo-user` 레코드 1개 | OAuth/이메일 로그인, 다중 사용자 | 로그인 흐름 없이 프론트의 개인화 화면을 연결할 수 있다. |
| DB | SQLite는 로컬 개발·테스트, PostgreSQL은 운영 | 운영 데이터 이관 자동화 | SQLite의 외래 키, JSON, 날짜, 동시성 동작은 PostgreSQL과 다르므로 공통 SQLAlchemy 타입과 애플리케이션 검증만 사용한다. |
| ORM 실행 방식 | 동기 SQLAlchemy 세션 | 비동기 SQLAlchemy | CRUD·문서 분석 요청이 적은 MVP는 단순한 동기 트랜잭션이 오류 경계와 테스트를 단순화한다. |
| CV 파일 | 서버의 비공개 로컬 영속 볼륨에 `storage_key`로 저장 | S3 등 외부 객체 스토리지 | 단일 데모 배포에는 추가 계정·권한·인프라가 필요 없다. 무상태 다중 인스턴스가 필요해지면 외부 스토리지로 전환한다. |
| 연구실 수집 | 수동 입력 또는 별도 수집 스크립트 결과를 검토 후 반영 | 예약 크롤러·변경 감지 | 사용자 API 요청 중 크롤링하면 응답 지연과 출처 검증 실패가 생긴다. |
| 논문-연구실 연결 | `papers.lab_id` 단일 연결 | `paper_labs` 다대다 | 현재 UI는 연구실 상세의 소속 논문만 표시한다. 공동 소속을 실제로 다룰 때만 관계 테이블을 추가한다. |

## MVP에서 바로 구현

### `users`

| 열 | 형식 | 설명 |
| --- | --- | --- |
| `id` | string PK | MVP는 `demo-user` 고정 값 |
| `created_at`, `updated_at` | UTC datetime | 감사용 시각 |

### `user_profiles`

| 열 | 형식 | 설명 |
| --- | --- | --- |
| `user_id` | string PK/FK | `users.id` |
| `name`, `affiliation`, `status`, `program` | string | 현재 프론트 `UserProfile` 기본 필드 |
| `interests_json`, `skills_json`, `methodologies_json`, `projects_json` | JSON 호환 text/JSON | 순서가 UI에 의미가 있는 문자열 목록 |
| `updated_at` | UTC datetime | 프로필 수정 시각 |

SQLite와 PostgreSQL 양쪽에서 배열 동작을 동일하게 유지하기 위해 MVP는 배열 검색을 DB에 위임하지 않는다. 추천 로직이 목록을 읽어 정규화·비교하며, PostgreSQL 전용 배열/JSON 연산자는 확장 시점까지 사용하지 않는다.

### `labs`

| 열 | 형식 | 설명 |
| --- | --- | --- |
| `id` | string PK | URL에 쓰는 안정적인 slug |
| `name`, `professor_name`, `department`, `field` | string | 탐색·상세·비교 기본 정보 |
| `homepage_url`, `location`, `contact_email` | nullable string | 검증된 출처가 있을 때만 저장 |
| `summary_text` | nullable text | 연구실 설명 |
| `summary_origin` | enum | `source_extracted`, `llm_generated`, `manual`, `fixture` |
| `source_url`, `source_checked_at` | nullable URL/UTC datetime | 대표 출처와 마지막 확인 시각 |
| `created_at`, `updated_at` | UTC datetime | 레코드 시각 |

`summary_origin=llm_generated`인 요약은 API에서 그대로 표기한다. UI는 원문 사실이 아닌 요약임을 표시할 수 있어야 한다.

### `lab_facts`

| 열 | 형식 | 설명 |
| --- | --- | --- |
| `id` | string PK | 사실 식별자 |
| `lab_id` | FK | 대상 연구실 |
| `fact_type` | enum | `keyword`, `recent_topic`, `requirement`, `member_count` |
| `value_text`, `value_number`, `audience` | nullable | 문자열 사실 또는 인원 수와 대상(`professor`/`phd`/`ms`) |
| `origin` | enum | `source_extracted`, `manual`, `fixture`; LLM 생성값 금지 |
| `source_url`, `source_checked_at` | URL/UTC datetime | 각 사실의 근거 |

연구 키워드, 최근 주제, 지원 역량, 구성원 수는 이 테이블에서 API 응답 구조로 조립한다. 현재 mock에 있는 값을 실데이터처럼 넣지 않는다.

### `papers`

| 열 | 형식 | 설명 |
| --- | --- | --- |
| `id` | string PK | 논문 식별자 |
| `lab_id` | FK | MVP의 단일 연구실 연결 |
| `title`, `venue`, `published_year` | string/string/int | 상세 화면 표시 값 |
| `keywords_json` | JSON 호환 text/JSON | 논문 키워드 |
| `paper_url`, `source_url`, `source_checked_at` | nullable URL/URL/UTC datetime | 논문·수집 근거 |

### `favorites`

`user_id`와 `lab_id` 복합 PK, `created_at`을 가진다. 현재 프론트의 문자열 ID 목록을 영속화한다.

### `calendar_events`

| 열 | 형식 | 설명 |
| --- | --- | --- |
| `id` | string PK | 일정 식별자 |
| `user_id` | FK | 소유자 |
| `title`, `kind`, `event_date`, `memo` | string/enum/date/nullable text | 현재 `CalendarEvent` 필드 |
| `lab_id` | nullable FK | 관련 연구실 |
| `created_at`, `updated_at` | UTC datetime | 기록 시각 |

`kind`는 `apply`, `contact`, `docs`, `interview`만 허용한다. 실입시 일정은 출처가 있는 별도 일정으로 확장하기 전까지 사용자가 만든 개인 일정으로만 취급한다.

### `uploaded_documents`

`id`, `user_id`, `original_filename`, `content_type`, `byte_size`, `storage_key`, `uploaded_at`, `status`를 가진다. 허용 형식은 PDF/DOCX, 최대 크기는 API 계약에서 정한다. 파일 본문·연락처 등 민감한 추출 텍스트를 일반 로그에 기록하지 않는다.

### `document_analyses`

`id`, `document_id`, `status`, `keywords_json`, `skills_json`, `methodologies_json`, `projects_json`, `completeness`, `analysis_origin`, `created_at`, `error_code`를 가진다. `analysis_origin`은 `deterministic` 또는 `llm_generated`이며, 분석 결과는 사용자가 편집할 수 있는 제안으로만 제공한다.

## 해커톤 이후 구현 또는 확장

- `auth_identities`, `sessions`: 실제 인증과 사용자 격리.
- `institutions`, `departments`, `professors`, `lab_members`: 기관·구성원 정규화.
- `paper_labs`: 공동 연구·복수 연구실 논문 연결.
- `source_snapshots`, `crawl_runs`: 크롤링 원문, 실패 이력, 변경 감지.
- `recommendation_runs`, `recommendation_items`: 추천 이력·재현성·사용자 피드백.
- `email_drafts`, `generation_audits`: 초안 저장·LLM 프롬프트 버전·사용자 승인 이력.
- 외부 객체 스토리지, 파일 바이러스 검사, 삭제 보존 정책, 비동기 분석 큐.

## 무결성과 이관 주의점

- 모든 FK는 SQLite에서 명시적으로 활성화해 테스트하고 PostgreSQL에서도 동일한 삭제 정책을 적용한다.
- UUID는 DB 종속 타입 대신 문자열로 먼저 다루거나, 양 DB가 지원하는 SQLAlchemy 타입으로 추상화한다.
- 시간은 UTC로 저장하고 날짜 일정은 date로 저장한다. SQLite의 느슨한 타입 강제를 보완하려고 Pydantic/API 계층에서 enum·길이·날짜 형식을 검증한다.
- fixture는 `origin=fixture`로만 적재하고 운영 데이터와 섞지 않는다.
