# 보안

## 상태 표기

이 문서는 현재 foundation에 적용된 통제와 후속 기능의 요구사항을 구분한다.

- **현재 적용**: 현재 코드·Compose·CI에서 동작하거나 강제되는 통제.
- **MVP에서 적용 예정**: API 기능을 추가할 때 함께 구현해야 하는 통제.
- **배포 전 필요**: 운영 공개 전에 검증하거나 추가해야 하는 통제.

현재 서버에는 인증, 업로드, 크롤링, OpenAI 호출, 추천, 이메일 발송이 없다.
완료되지 않은 통제를 구현된 것처럼 취급하지 않는다.

## 비밀정보와 환경변수

### 현재 적용

- `.env`는 Git ignore 대상이며 커밋하지 않는다. 실제 값은 프로세스 환경변수,
  배포 secret 또는 Docker Compose의 untracked local `.env`로만 공급한다.
- Pydantic Settings는 `env_file=None`이므로 `.env`를 앱이 직접 읽지 않는다.
  `.env.example`에는 빈 `OPENAI_API_KEY`와 비밀이 아닌 설정 예시만 둔다.
- Docker Compose의 PostgreSQL 비밀번호는 필수 `POSTGRES_PASSWORD` 환경변수이며,
  기본 비밀번호를 코드나 Compose 파일에 두지 않는다.
- frontend에는 OpenAI API 키나 다른 서버 전용 키를 넣지 않는다. 현재 OpenAI
  호출 코드도 존재하지 않는다.
- 현재 스키마에는 password 컬럼이 없으며 password를 평문 또는 해시로 저장하는
  인증 기능도 아직 없다. 향후 인증이 생겨도 password 평문 저장은 금지한다.

### 배포 전 필요

- 배포 플랫폼의 secret manager와 최소 권한 접근 정책을 사용하고, 키 회전·폐기
  절차를 문서화한다.
- CI 로그, error tracker, container inspect 결과에 `DATABASE_URL`이나 비밀 값이
  남지 않는지 점검한다.

## 로그, 오류, request ID

### 현재 적용

- request log는 UTC timestamp, level, logger, message, request ID를 JSON으로
  기록한다. 일반 request log에는 method, path, status만 기록하며 request body,
  업로드 본문, 비밀번호, API 키를 기록하지 않는다.
- 오류 응답은 `{ "error": { "code", "message" } }` 형태다. 500 응답에는 내부
  stack trace나 예외 상세를 반환하지 않는다.
- request ID는 지원·추적을 위한 상관관계 식별자다. UUID를 사용해야 하며 이름,
  이메일, 문서 ID, CV 내용 등 개인정보를 넣어서는 안 된다. 현재 클라이언트가
  `X-Request-ID`를 보낼 수 있으므로 호출자도 이 규칙을 지켜야 한다.

### 배포 전 필요

- 처리되지 않은 예외의 stack trace가 logging backend에 전달될 때 비밀·개인정보가
  포함되지 않는지 점검하고, 민감한 값은 redaction한다.
- request ID의 형식·길이를 검증하거나 서버 생성 UUID만 허용할지 결정한다.

## 네트워크와 CORS

### 현재 적용

- development 기본 CORS origin은 `http://localhost:5173` 하나다.
- test와 production은 기본 CORS origin이 없고, `CORS_ORIGINS=*`는 설정 검증에서
  거부된다. 설정된 origin이 없으면 CORS middleware 자체를 등록하지 않는다.
- Docker Compose는 backend를 PostgreSQL healthcheck 이후 시작하고, DB 포트는
  host에 공개하지 않는다. backend의 HTTP port만 공개한다.

### 배포 전 필요

- 운영 도메인만 `CORS_ORIGINS`에 허용하고 TLS, reverse proxy, 보안 header,
  rate limiting과 observability 설정을 검토한다.

## 데이터, DB, fixture

### 현재 적용

- SQLAlchemy 모델과 migration은 DB별 문자열 조합 SQL을 사용하지 않는다. 향후
  repository query도 SQLAlchemy parameter binding/ORM 표현식을 사용해 SQL injection을
  피해야 한다.
- SQLite는 foreign key PRAGMA를 적용하고, PostgreSQL 운영 연결은
  `postgresql+psycopg` URL로 구성한다.
- seed는 `Fixture` 식별자와 `origin="fixture"`를 사용한다. 실제 학교, 교수,
  이메일, 논문, 사용자 개인정보가 아니며 재실행해도 중복 생성하지 않는다.

### MVP에서 적용 예정

- 연구실·교수·논문·일정의 운영 데이터는 출처 URL과 마지막 확인 시점 없이는
  적재하지 않는다. LLM 생성 텍스트는 원문 추출 사실과 구분한다.
- 사용자 프로필, 관심 연구실, 일정은 실제 인증·권한·사용자 격리가 구현되기 전
  데모 데이터로만 취급한다.

## 업로드 문서와 개인정보

### 현재 상태

`uploaded_documents`와 `document_analyses` 모델은 migration에만 존재한다. 파일
업로드 endpoint, 파일 저장, CV 분석은 구현되지 않았으므로 현재 CV·포트폴리오
본문을 수집하거나 처리하지 않는다.

### MVP에서 적용 예정

- PDF/DOCX allowlist, MIME type과 실제 파일 서명 확인, 최대 10MB 제한, 안전한
  서버 생성 storage key, 원본 파일명 정규화를 구현한다.
- 파일 본문, 연락처, 학력, 경력 등 CV/포트폴리오 개인정보를 request log, 일반
  오류, 분석 프롬프트, fixture에 기록하지 않는다.
- 비공개 저장 위치, 접근 제어, 보존·삭제 정책, malware scan 실패 처리와 사용자
  고지를 설계한다.

## 비신뢰 입력, 크롤링, LLM

### 현재 상태

크롤러와 OpenAI/LLM 호출은 구현되지 않았다. 따라서 외부 HTML, 문서 내부 명령,
프롬프트를 신뢰하거나 실행하는 코드는 없다.

### MVP에서 적용 예정

- 크롤링 HTML·PDF·문서의 모든 텍스트를 비신뢰 데이터로 취급한다. 문서 안의
  명령은 시스템 지침이나 도구 호출 권한을 변경하지 못한다.
- LLM을 도입하면 신뢰된 시스템 지침과 비신뢰 원문을 분리하고, 도구 권한을
  allowlist로 제한하며, 생성 결과를 사실·출처 데이터와 구분해 사용자 검토를
  거치게 한다. 이는 prompt injection 방어의 기본 원칙이다.
- SSRF 방지를 위해 수집 URL은 `http`/`https` allowlist, DNS 재해석 방지, private,
  loopback, link-local IP 차단, redirect 재검증, timeout·응답 크기 제한을 적용한다.

## 인증과 권한

### 현재 상태

실제 로그인, OAuth, session, 권한 검사는 구현되지 않았다. seed의 `demo-user`는
개발 fixture일 뿐 인증 주체가 아니다. 현재 foundation은 인터넷 공개나 실제
사용자 데이터 격리를 위한 준비가 완료된 상태가 아니다.

### 배포 전 필요

- 인증된 사용자 ID를 서버 세션/토큰에서 도출하고, 모든 사용자 소유 리소스에
  authorization check를 적용한다.
- password 기반 인증을 채택한다면 검증된 password hashing 알고리즘, reset·lockout,
  session 만료와 CSRF 정책을 적용한다. password 평문은 어떤 로그·DB·응답에도
  저장하지 않는다.

## 배포 전 보안 체크리스트

- [ ] production `APP_ENV`, 좁은 `CORS_ORIGINS`, HTTPS 종료 지점과 security header 확인
- [ ] secret manager, 키 회전, CI/로그/이미지의 비밀 스캔 확인
- [ ] 인증·권한·rate limiting·감사 로그와 개인정보 보존/삭제 정책 구현
- [ ] 업로드 allowlist·크기·서명·malware scan·비공개 저장 검증
- [ ] crawler SSRF 보호, robots/이용약관 검토, timeout·redirect·크기 제한 적용
- [ ] LLM prompt injection 경계, 사실/생성 결과 표기, 사용자 검토 단계 확인
- [ ] PostgreSQL backup, 최소 권한 DB 계정, migration rollback 절차, dependency 취약점 점검
