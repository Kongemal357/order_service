import logging

from src.application.dto.event_dto import OrderCancelledEventDTO, OrderShippedEventDTO
from src.application.ports.uow import UnitOfWorkFactory
from src.domain.models import EventType, InboxRecord

logger = logging.getLogger(__name__)


class SaveInboxEventUseCase:
    """
    Use case for saving incoming Kafka event to inbox.
    """

    def __init__(self, uow_factory: UnitOfWorkFactory):
        self.uow_factory = uow_factory

    async def execute(self, data: dict) -> bool:
        event_type_str = data.get("event_type")

        try:
            event_type = EventType(event_type_str)
        except ValueError:
            logger.warning(f"Unknown event type: {event_type_str}")
            return False

        if event_type == EventType.ORDER_SHIPPED:
            try:
                dto = OrderShippedEventDTO.from_dict(data)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Invalid order.shipped payload: {data} - {e}")
                return False
            event_id = f"{event_type.value}_{dto.shipment_id}"
        elif event_type == EventType.ORDER_CANCELLED:
            try:
                dto = OrderCancelledEventDTO.from_dict(data)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Invalid order.cancelled payload: {data} - {e}")
                return False
            event_id = f"{event_type.value}_{dto.order_id}"
        else:
            logger.warning(f"Unhandled event type: {event_type}")
            return False

        if not dto.order_id:
            logger.warning(f"No order_id in event: {data}")
            return False

        async with self.uow_factory() as uow:
            record = InboxRecord.create(
                event_id=event_id,
                event_type=event_type,
                payload=data,
            )

            saved = await uow.inbox_repo.save(record)
            await uow.commit()

            if saved is None:
                logger.debug(f"Duplicate event: {event_id}, skipping")
                return False

            logger.debug(f"Saved to inbox: {event_id}")
            return True
