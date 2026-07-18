# 작업 규칙

- 변경 전에는 현재 저장소 구조와 기존 코드를 먼저 조사한다.
- `frontend/`와 `backend/`의 책임과 의존성 경계를 지킨다.
- 기존 Lovable UI를 임의로 삭제하거나 전면 교체하지 않는다.
- OpenAI API 키를 `frontend/`에 넣지 않는다.
- 비밀키와 `.env` 파일을 커밋하지 않는다.
- 기능 구현 후 관련 `test`, `lint`, `build`를 실행한다.
