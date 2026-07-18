# 프로젝트 구조

```text
repository-root/
├── frontend/              # Lovable 기반 React/TypeScript 프론트엔드
├── backend/               # Python FastAPI 백엔드
├── docs/                  # 운영 및 설계 문서
│   ├── API_CONTRACT.md
│   ├── BACKEND_ROADMAP.md
│   ├── BRANCH_STRATEGY.md
│   ├── DATABASE_SCHEMA.md
│   ├── FRONTEND_BACKEND_MAPPING.md
│   └── PROJECT_STRUCTURE.md
├── AGENTS.md              # 자동화 작업 규칙
├── README.md              # 프로젝트 안내
├── .gitignore             # 로컬·생성 파일 제외 규칙
└── .env.example           # 환경변수 이름 예시
```

## 디렉터리 책임

### `frontend/`

Lovable에서 생성한 React/TypeScript UI를 둡니다. 브라우저에 노출되는 코드에는 비밀값이나 서버 전용 API 키를 포함하지 않습니다.

### `backend/`

FastAPI 애플리케이션, 서버 전용 설정, 외부 API 연동을 둡니다. 실제 비밀값은 커밋하지 않는 `.env` 또는 배포 환경의 시크릿으로 관리합니다.

### `docs/`

브랜치 정책, 구조 결정, API 계약 등 협업에 필요한 문서를 둡니다.
