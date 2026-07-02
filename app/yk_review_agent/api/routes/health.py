from fastapi import APIRouter

from yk_review_agent.core.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "demo_mode": settings.demo_mode,
    }
