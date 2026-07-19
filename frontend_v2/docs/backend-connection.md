# Backend connection

`frontend_v2` is independently runnable at `http://localhost:3000`.
Its existing owner-scoped profile endpoint remains at `/api/profile`; it does
not share or overwrite the legacy `frontend/` application's API routes.

To connect to the repository's FastAPI backend, create `frontend_v2/.env.local`
from `.env.example` and set the server-only origin:

```dotenv
BACKEND_API_ORIGIN=http://127.0.0.1:8000
```

Next.js proxies versioned backend requests through the same origin:

| Frontend_v2 URL | Backend URL |
| --- | --- |
| `GET /api/backend/health` | `GET /api/v1/health` |
| `GET /api/backend/labs` | `GET /api/v1/labs` |
| `GET /api/backend/labs/{id}` | `GET /api/v1/labs/{id}` |
| `GET /api/backend/labs/{id}/similar` | `GET /api/v1/labs/{id}/similar` |
| `GET /api/backend/recommendations` | `GET /api/v1/recommendations` |
| `GET`, `PUT`, `DELETE /api/backend/me/favorites/*` | `/api/v1/me/favorites/*` |
| `POST /api/backend/documents/analyze` | `POST /api/v1/documents/analyze` |
| `GET /api/backend/documents/latest` | `GET /api/v1/documents/latest` |
| `GET /api/backend/documents` | `GET /api/v1/documents` |

The default matches `backend`'s local Uvicorn address. Start the backend first
with `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
from the `backend` directory, then run `npm run dev` from `frontend_v2`.

This proxy avoids exposing server configuration in `NEXT_PUBLIC_*` variables
and avoids browser CORS coupling. It reads the HttpOnly
`ddacksaeu_session` cookie server-side and forwards it as a backend Bearer
token. The browser never receives or stores that token.
