from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from yk_review_agent.api.routes.chat import router as chat_router
from yk_review_agent.api.routes.demo import router as demo_router
from yk_review_agent.api.routes.health import router as health_router
from yk_review_agent.api.routes.sessions import router as sessions_router
from yk_review_agent.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix=settings.api_prefix, tags=["health"])
    app.include_router(demo_router, prefix=settings.api_prefix, tags=["demo"])
    app.include_router(sessions_router, prefix=settings.api_prefix, tags=["sessions"])
    app.include_router(chat_router, prefix=settings.api_prefix, tags=["chat"])

    return app


app = create_app()
