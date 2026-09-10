import asyncio
import logging
from typing import Optional

from src.application.usecases.process_inbox import ProcessInboxUseCase

logger = logging.getLogger(__name__)


class InboxWorker:
    """
    Background worker that periodically processes pending inbox events.
    """

    def __init__(
        self,
        process_inbox_use_case: ProcessInboxUseCase,
        interval_seconds: int = 5,
        batch_size: int = 100,
    ):
        self.process_inbox_use_case = process_inbox_use_case
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the worker."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(
            f"Inbox worker started (interval={self.interval_seconds}s, batch={self.batch_size})"
        )

    async def stop(self):
        """Stop the worker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Inbox worker stopped")

    async def _run(self):
        """Main worker loop."""
        while self._running:
            try:
                processed = await self.process_inbox_use_case.execute(limit=self.batch_size)

                if processed > 0:
                    logger.debug(f"Processed {processed} inbox events")

                await asyncio.sleep(self.interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing inbox events: {e}")
                await asyncio.sleep(self.interval_seconds)
