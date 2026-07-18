# 딱새우 (Dacksaue)

대학원 진학 희망자가 연구 관심사와 조건에 맞는 연구실을 탐색·추천받을 수 있도록 만드는 서비스입니다.

## 예정 구조

```text
.
├── frontend/  # Lovable에서 생성·관리하는 React/TypeScript 애플리케이션
├── backend/   # Python FastAPI 애플리케이션
├── docs/      # 프로젝트 운영 및 설계 문서
├── AGENTS.md  # 자동화 작업 규칙
└── .env.example
```

## 개발 시작 위치

- 프론트엔드: `frontend/`에서 Lovable 기반 React/TypeScript 프로젝트를 관리하고 실행합니다. 현재 연구실 탐색, 맞춤 추천, 관심 연구실, 캘린더, 프로필, 컨택 이메일 화면이 mock 데이터로 구현되어 있습니다.
- 백엔드: `backend/`에서 FastAPI 애플리케이션을 관리하고 실행합니다. 아직 의존성·실행 설정은 추가하지 않았습니다.

브랜치 운영 기준은 `docs/BRANCH_STRATEGY.md`, 디렉터리 역할은 `docs/PROJECT_STRUCTURE.md`, 프론트-백엔드 연결 설계는 `docs/FRONTEND_BACKEND_MAPPING.md`를 참고하세요.
