from fastapi import APIRouter, Request

from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="Service health")
def health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="ddacksaeu-backend",
        version=request.app.state.settings.app_version,
    )
