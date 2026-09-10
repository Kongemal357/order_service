import logging
from typing import Awaitable, Callable, List

from src.application.usecases.save_inbox_event import SaveInboxEventUseCase

logger = logging.getLogger(__name__)


def create_shipping_events_handler(
    save_inbox_use_case: SaveInboxEventUseCase,
) -> Callable[[List[dict]], Awaitable[None]]:
    """
    Create handler for shipping events from Kafka.
    Returns a callable that accepts only data_list.
    """

    async def handle_shipping_events_batch(data_list: List[dict]) -> None:
        """Handle batch of shipping events from Kafka."""
        if not data_list:
            return

        logger.info(f"Processing batch of {len(data_list)} shipping events")

        for data in data_list:
            try:
                await save_inbox_use_case.execute(data)
            except Exception as e:
                logger.error(f"Error saving event to inbox: {e}")

    return handle_shipping_events_batch
