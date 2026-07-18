# 브랜치 전략

## 기본 원칙

- `main`은 언제나 실행 가능한 안정 상태만 유지합니다.
- 기능 개발은 `feat/...` 브랜치에서 진행합니다.
- 설정·도구·문서 중심 작업은 `chore/...` 브랜치에서 진행합니다.
- 버그 수정은 `fix/...` 브랜치에서 진행합니다.
- `frontend`, `backend` 장기 브랜치는 운영하지 않습니다.
- 프론트엔드와 백엔드의 동시 통합 검증이 필요할 때만 `integration/frontend-backend` 브랜치를 사용합니다.

## 예시

- `feat/lab-search`
- `chore/monorepo-bootstrap`
- `fix/recommendation-response`
- `integration/frontend-backend`

작업 완료 후 검토·검증을 거쳐 `main`에 병합합니다.
