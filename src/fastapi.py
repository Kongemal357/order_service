import logging

from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI
from src.presentation.api.routes.orders import router
from src.settings import settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    logger.info("Creating FastAPI application")

    app = FastAPI(
        title=settings.SERVICE_NAME,
        version="1.0.0",
        description="Order Service with Clean Architecture",
        redirect_slashes=False,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(router)

    # Health check
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": settings.SERVICE_NAME,
            "debug": settings.DEBUG,
        }

    return app
