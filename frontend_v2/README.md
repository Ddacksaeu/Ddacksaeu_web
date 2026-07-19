# 딱새우

대학원 지원자가 관심 분야에 맞는 교수를 찾고, CV 분석부터 컨택 메일과 입시 일정까지 한 흐름에서 준비하는 해커톤 MVP입니다.

## 주요 화면

- 로그인 및 초기 설정
- 개인화 대시보드
- 교수 탐색과 교수 상세
- CV·포트폴리오 분석
- 컨택 메일 초안
- 입시 스케줄러
- 마이페이지

현재 교수·논문·모집 정보와 AI 결과는 데모 데이터입니다. 실제 크롤러와 AI 연동은 후속 단계이며, 화면의 모집 여부는 반드시 원문에서 확인해야 합니다.

## 로컬 실행

```bash
npm install
npm run dev
```

브라우저에서 `http://localhost:3000`을 엽니다. 프로덕션 모드에서는 `.env.example`을 참고해 16자 이상의 `OWNER_SESSION_SECRET`을 지정하세요.

```bash
npm run build
npm run start
```

## Backend connection

The independently running Next.js app keeps its local profile API at
`/api/profile`. To reach this repository's FastAPI backend, configure
`BACKEND_API_ORIGIN` in `.env.local`; the backend API is then available through
`/api/backend/*` (for example, `http://localhost:3000/api/backend/health`).
See [docs/backend-connection.md](docs/backend-connection.md) for the local
startup commands and the routing contract.

## CV analysis

After signing in, open **Profile** to upload a PDF, DOCX, or TXT CV (up to
10 MB) and view the latest result plus recent analysis history. The browser
uses the existing `/api/backend/documents/*` BFF proxy, which reads the
HttpOnly session cookie and forwards authentication to FastAPI; no backend
token is stored in browser storage.

Analysis is local rule-based processing on the backend. No external AI API or
OCR is used, so image-only PDFs cannot be analyzed; use a text-based PDF,
DOCX, or TXT file instead. Start the backend with its documented environment
and migrations before using this screen. Current history is limited to the
metadata returned by the API; it has no detail-selection route.

## 검증

```bash
npm test
npm run lint
npx tsc --noEmit
npx playwright test
```
