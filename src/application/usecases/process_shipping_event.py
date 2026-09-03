import logging

from src.application.dto.event_dto import OrderCancelledEventDTO, OrderShippedEventDTO
from src.application.ports.inbox_repository import InboxRepository
from src.application.ports.uow import UnitOfWork
from src.domain.exceptions import OrderNotFoundError
from src.domain.models import InboxRecord, OrderStatus
from src.infrastructure.messaging.retry_handler import RetryHandler

logger = logging.getLogger(__name__)


class ProcessShippingEventUseCase:
    """
    Use case for processing shipping events from Kafka.
    Uses Inbox pattern for idempotency.
    """

    def __init__(
            self,
            uow_factory: UnitOfWork,
            retry_handler: RetryHandler,
    ):
        self.uow_factory = uow_factory
        self.retry_handler = retry_handler

    @staticmethod
    async def _is_processed(
        idempotency_key: str,
        inbox_repo: InboxRepository,
    ) -> bool:
        """Check if event was already processed."""
        if not idempotency_key:
            return False
        record = await inbox_repo.get_by_idempotency_key(idempotency_key)
        return record is not None

    async def process_shipped(
            self,
            event_dto: OrderShippedEventDTO,
            retry_count: int = 0,
    ) -> None:
        """
        Process order.shipped event.
        If processing fails with a retryable error, sends to retry topic.
        """
        logger.info(
            f"Processing order.shipped event: order={event_dto.order_id}, "
            f"shipment={event_dto.shipment_id}"
        )
        try:
            async with self.uow_factory() as uow:
                # Check inbox (idempotency)
                if await self._is_processed(event_dto.idempotency_key, uow.inbox_repo):
                    logger.info(f"Event already processed: {event_dto.idempotency_key}")
                    return

                order = await uow.order_repo.get_by_id(event_dto.order_id)
                if not order:
                    raise OrderNotFoundError(f"Order {event_dto.order_id} not found")

                if order.status == OrderStatus.PAID:
                    order.mark_shipped()
                    await uow.order_repo.update(order)
                else:
                    logger.warning(f"Cannot ship order {order.id} with status {order.status}")

                # Save inbox record
                inbox = InboxRecord.create(
                    event_id=str(event_dto.shipment_id),
                    idempotency_key=event_dto.idempotency_key,
                    event_type="order.shipped",
                )
                await uow.inbox_repo.save(inbox)
                await uow.commit()

            logger.info(f"Order {event_dto.order_id} marked as SHIPPED")

        except OrderNotFoundError:
            # Заказ не найден — не ретраим
            logger.error(f"Order not found: {event_dto.order_id}")
            raise

        except Exception as e:
            # ⚠Retryable error → send to retry topic
            logger.warning(f"Retryable error processing shipped event: {e}")

            await self.retry_handler.send_to_retry(
                event_data={
                    "event_type": "order.shipped",
                    "order_id": str(event_dto.order_id),
                    "item_id": str(event_dto.item_id),
                    "quantity": event_dto.quantity,
                    "shipment_id": str(event_dto.shipment_id),
                    "idempotency_key": event_dto.idempotency_key,
                },
                retry_count=retry_count + 1,
                error=str(e),
            )

    async def process_cancelled(
            self,
            event_dto: OrderCancelledEventDTO,
        retry_count: int = 0,
    ) -> None:
        """Process order.cancelled event."""
        logger.info(
            f"Processing order.cancelled event: order={event_dto.order_id}, "
            f"reason={event_dto.reason}"
        )
        try:
            async with self.uow_factory() as uow:
                # Check inbox (idempotency)
                if await self._is_processed(event_dto.idempotency_key, uow.inbox_repo):
                    logger.info(f"Event already processed: {event_dto.idempotency_key}")
                    return

                order = await uow.order_repo.get_by_id(event_dto.order_id)
                if not order:
                    raise OrderNotFoundError(f"Order {event_dto.order_id} not found")

                status_changed = False
                if order.status not in (OrderStatus.SHIPPED, OrderStatus.CANCELLED):
                    order.cancel()
                    status_changed = True
                    await uow.order_repo.update(order)
                else:
                    logger.warning(f"Cannot cancel order {order.id} with status {order.status}")

                # Save inbox record
                inbox = InboxRecord.create(
                    event_id=str(event_dto.order_id),
                    idempotency_key=event_dto.idempotency_key,
                    event_type="order.cancelled",
                )
                await uow.inbox_repo.save(inbox)
                await uow.commit()

            if status_changed:
                logger.info(f"Order {event_dto.order_id} marked as CANCELLED")
            else:
                logger.info(f"Order {event_dto.order_id} already in terminal state, inbox saved")

        except OrderNotFoundError:
            logger.error(f"Order not found: {event_dto.order_id}")
            raise

        except Exception as e:
            logger.warning(f"Retryable error processing cancelled event: {e}")

            await self.retry_handler.send_to_retry(
                event_data={
                    "event_type": "order.cancelled",
                    "order_id": str(event_dto.order_id),
                    "item_id": str(event_dto.item_id),
                    "quantity": event_dto.quantity,
                    "reason": event_dto.reason,
                    "idempotency_key": event_dto.idempotency_key,
                },
                retry_count=retry_count + 1,
                error=str(e),
            )
