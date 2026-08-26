import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from src.fastapi import create_app
from src.settings import settings


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def run_migrations():
    """Run Alembic migrations."""
    logger = logging.getLogger(__name__)

    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations applied successfully")
    except ImportError:
        logger.warning(" Alembic not installed, skipping migrations")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise


def main():
    """Run the application."""
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info(f"Starting {settings.SERVICE_NAME}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    run_migrations()
    app = create_app()

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="debug" if settings.DEBUG else "info",
    )


if __name__ == "__main__":
    main()