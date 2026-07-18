# 백엔드 로드맵

## MVP 결정 기록

| 주제 | MVP에서 바로 구현 | 해커톤 이후 구현 또는 확장 | 결정 이유 |
| --- | --- | --- | --- |
| 인증 | `demo-user` 하나를 서버에서 사용 | 실제 계정·OAuth·다중 사용자 | 로그인·권한 화면 없이 현재 UI를 실제 저장소에 연결한다. |
| 파일 저장 | 비공개 로컬 영속 볼륨 | 외부 객체 스토리지 | 데모 규모에는 외부 서비스 설정이 불필요하다. |
| 데이터 수집 | 수동 검수한 seed/fixture 또는 별도 명령 | 예약 크롤러·재시도·변경 감지 | HTTP 요청 중 크롤링하지 않아 응답 시간과 데이터 신뢰성을 보장한다. |
| ORM | 동기 SQLAlchemy | 비동기 SQLAlchemy | 작은 CRUD와 짧은 분석 요청에 가장 단순하다. |
| DB | SQLite 개발·테스트, PostgreSQL 운영 | 자동 이관·성능 튜닝 | DB 특화 SQL을 피하고 양쪽을 검증해 호환 위험을 낮춘다. |
| 추천 | 설명 가능한 규칙 기반 점수 | 학습형/개인화 모델 | 근거를 보여 주고 데이터 부족 시 점수를 보류할 수 있다. |
| 이메일 | 템플릿 초안, 선택적 서버 LLM 대체 | 도구별 AI 편집·저장·발송 | 발송 없이도 사용자 검토 가능한 핵심 흐름을 제공한다. |

Redis, Celery, Kubernetes는 MVP에 넣지 않는다. 비동기 작업·수평 확장·큐 재시도가 실제 병목으로 확인될 때 도입 여부를 재검토한다.

## 구현 순서

### MVP에서 바로 구현

1. FastAPI 프로젝트 뼈대, 환경변수 검증, 동기 SQLAlchemy 세션, SQLite 테스트 설정을 만든다.
2. `users`, `user_profiles`, `labs`, `lab_facts`, `papers`, `favorites`, `calendar_events` 모델·검증 스키마를 구현한다.
3. 출처 URL·마지막 확인 시점·origin을 가진 검수된 fixture만 적재한다. 현재 프론트 mock은 실데이터로 승격하지 않는다.
4. 연구실 탐색/상세/유사 목록, 프로필, 관심, 일정 API를 구현하고 API 계약 단위 테스트를 작성한다.
5. 로컬 비공개 파일 저장과 PDF/DOCX 형식·용량 검증을 구현한다. 분석은 실패를 명시하고 민감 텍스트를 로그에 남기지 않는다.
6. 설명 가능한 추천 규칙과 `insufficient_data` 응답을 구현한다.
7. 컨택 이메일 템플릿 초안 API를 구현한다. LLM 사용 시 키는 `backend/` 환경에서만 읽고, 생성 결과·원문 사실·출처를 응답에서 구분한다.
8. SQLite와 PostgreSQL 호환 테스트, API 테스트, lint, build를 실행한 뒤 프론트 API 연결 작업을 시작한다.

### 해커톤 이후 구현 또는 확장

1. 실제 인증·권한·사용자 데이터 삭제 정책을 추가한다.
2. 운영자 검수 화면과 수집 파이프라인을 만들고, 원문 스냅샷·크롤링 이력·변경 감지를 저장한다.
3. 논문-연구실 다대다, 교수·기관·모집 공고 등 데이터 모델을 확장한다.
4. 외부 스토리지, 비동기 분석 큐, 재시도와 관측성을 실제 부하 요구에 맞춰 도입한다.
5. 추천 이력·피드백·공정성 점검과 이메일 AI 도구·초안 이력을 추가한다.

## 완료 기준

- 문서에 없는 필드는 API 응답에 추측으로 추가하지 않는다.
- 운영 데이터는 모든 연구실·논문·일정 사실에 출처 URL과 마지막 확인 시점이 있다.
- LLM 텍스트는 `llm_generated`로 식별되고, 원문 추출 사실과 혼합 표시되지 않는다.
- 프로필 정보·업로드 문서·서버 API 키는 브라우저 번들, 일반 로그, 저장소에 노출되지 않는다.
- SQLite와 PostgreSQL에서 핵심 CRUD 및 날짜·JSON·외래키 동작을 검증한다.
## Completed: database and fixture seed foundation (2026-07-18)

- Added normalized institution, department, professor, and keyword relations.
- Added constraint-checked recommendation and crawl execution records.
- Added fixture-only seed data for Seoul National University, KAIST, and
  POSTECH labels, using fictional departments, professors, labs, publications,
  and admission dates.
- Deferred: CRUD/search API routes, actual crawling, recommendation scoring,
  authentication, and frontend integration.

## Completed: admission calendar API (2026-07-18)

- Added provenance-backed, fixture-labelled admission event filtering and ICS export.
- Added the reversible admission-event migration for time ranges and estimate status.

## Completed: deterministic recommendation API (2026-07-18)

- Added explicit recomputation and read-only retrieval using the existing
  `recommendations` table.
- Added explainable weighted scoring, confidence reduction for incomplete data,
  deterministic ordering, and semantic-provider fallback.
- Deferred durable per-keyword weight storage because neither `user_keywords`
  nor `document_analyses` persists CV weight maps.
