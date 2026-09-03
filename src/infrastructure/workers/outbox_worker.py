import asyncio
import logging
from typing import Optional

from src.application.usecases.process_outbox import ProcessOutboxUseCase

logger = logging.getLogger(__name__)


class OutboxWorker:
    """
    Background worker that periodically processes pending outbox events.
    """

    def __init__(
        self,
        process_outbox_use_case: ProcessOutboxUseCase,
        interval_seconds: int = 5,
        batch_size: int = 100,
    ):
        self.process_outbox_use_case = process_outbox_use_case
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
            f"Outbox worker started (interval={self.interval_seconds}s, batch={self.batch_size})"
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
        logger.info("Outbox worker stopped")

    async def _run(self):
        """Main worker loop."""
        while self._running:
            try:
                processed = await self.process_outbox_use_case.execute(limit=self.batch_size)

                if processed > 0:
                    logger.debug(f"Processed {processed} outbox events")

                # Wait for next iteration
                await asyncio.sleep(self.interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing outbox events: {e}")
                await asyncio.sleep(self.interval_seconds)
