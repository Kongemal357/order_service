import logging

from src.application.dto.event_dto import OrderCancelledEventDTO, OrderShippedEventDTO
from src.application.ports.uow import UnitOfWorkFactory
from src.application.usecases.process_shipping_event import ProcessShippingEventUseCase
from src.domain.models import EventType

logger = logging.getLogger(__name__)


class ProcessInboxUseCase:
    """
    Use case for processing pending inbox events.
    Runs periodically to process events from inbox.
    """

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        shipping_use_case: ProcessShippingEventUseCase,
    ):
        self.uow_factory = uow_factory
        self.shipping_use_case = shipping_use_case

    async def execute(self, limit: int = 100) -> int:
        logger.info(f"Processing inbox events (limit={limit})")

        processed_events = 0

        async with self.uow_factory() as uow:
            events = await uow.inbox_repo.get_pending(limit)

        if not events:
            logger.debug("No pending inbox events")
            return processed_events

        logger.info(f"Found {len(events)} pending inbox events")

        for event in events:
            use_case_result = False

            async with self.uow_factory() as uow:
                try:
                    if event.event_type == EventType.ORDER_SHIPPED:
                        dto = OrderShippedEventDTO.from_payload(event.payload)
                        use_case_result = await self.shipping_use_case.process_shipped(dto, uow)
                        processed_events += 1

                    elif event.event_type == EventType.ORDER_CANCELLED:
                        dto = OrderCancelledEventDTO.from_payload(event.payload)
                        use_case_result = await self.shipping_use_case.process_cancelled(dto, uow)
                        processed_events += 1

                    else:
                        logger.warning(f"Unknown event type: {event.event_type}")

                    await uow.inbox_repo.mark_processed(event.id)

                except Exception as e:
                    logger.error(f"Failed to process event {event.id}: {e}")

                await uow.commit()
                logger.info("Transaction committed")

            try:
                if use_case_result:
                    await self.shipping_use_case.send_notifications(
                        order_id=event.payload["order_id"],
                        event_type=event.event_type,
                    )
            except Exception as e:
                logger.error(f"Failed to send notification for event {event.id}: {e}")

        logger.info(f"Processed {processed_events} inbox events")
        return processed_events
