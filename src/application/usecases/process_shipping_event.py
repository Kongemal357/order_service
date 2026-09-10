import logging
from uuid import UUID

from src.application.dto.event_dto import OrderCancelledEventDTO, OrderShippedEventDTO
from src.application.ports.uow import UnitOfWork
from src.application.services.notification_service import NotificationService
from src.domain.exceptions import OrderNotFoundError
from src.domain.models import EventType, NotificationType, OrderStatus

logger = logging.getLogger(__name__)


class ProcessShippingEventUseCase:
    """
    Use case for processing shipping events.
    Called by Inbox Worker, not directly from Kafka.
    """

    def __init__(
        self,
        notification_service: NotificationService,
    ):
        self.notification_service = notification_service

    async def process_shipped(
        self,
        event_dto: OrderShippedEventDTO,
        uow: UnitOfWork,
    ) -> None | bool:
        """Process order.shipped event using existing UoW."""
        order = await uow.order_repo.get_by_id(event_dto.order_id)
        if not order:
            raise OrderNotFoundError(f"Order {event_dto.order_id} not found")

        if order.status == OrderStatus.PAID:
            order.mark_shipped()
            await uow.order_repo.update(order)
            return True
        else:
            logger.warning(f"Cannot ship order {order.id} with status {order.status}")
            return False

    async def process_cancelled(
        self,
        event_dto: OrderCancelledEventDTO,
        uow: UnitOfWork,
    ) -> bool:
        """Process order.cancelled event using existing UoW."""
        order = await uow.order_repo.get_by_id(event_dto.order_id)
        if not order:
            raise OrderNotFoundError(f"Order {event_dto.order_id} not found")

        if order.status not in (OrderStatus.SHIPPED, OrderStatus.CANCELLED):
            order.cancel()
            await uow.order_repo.update(order)
            return True
        else:
            logger.warning(f"Cannot cancel order {order.id} with status {order.status}")
            return False

    async def send_notifications(self, order_id: UUID, event_type: EventType) -> None:
        """Send notification after transaction."""
        if event_type == EventType.ORDER_SHIPPED:
            await self.notification_service.send_notification(
                order_id,
                NotificationType.ORDER_SHIPPED,
            )
        elif event_type == EventType.ORDER_CANCELLED:
            await self.notification_service.send_notification(
                order_id,
                NotificationType.ORDER_CANCELLED,
            )
