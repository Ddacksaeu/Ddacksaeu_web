from fastapi import APIRouter

from app.api.v1.admissions import router as admissions_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.labs import router as labs_router
from app.api.v1.recommendations import router as recommendations_router

router = APIRouter()
router.include_router(health_router)
router.include_router(admissions_router)
router.include_router(labs_router)
router.include_router(documents_router)
router.include_router(recommendations_router)
