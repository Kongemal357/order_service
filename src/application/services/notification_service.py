import logging
from uuid import UUID

from src.application.dto.notification_dto import SendNotificationDTO
from src.application.ports.notification_client import NotificationClient
from src.domain.models import NotificationType

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications with predefined templates.

    Handles idempotency by generating unique idempotency keys.
    Errors are logged but not raised (non-blocking).
    """

    _MESSAGES = {
        NotificationType.ORDER_CREATED: "Your order has been created and requires payment",
        NotificationType.ORDER_PAID: "Your order has been successfully paid and ready for shipment",
        NotificationType.ORDER_SHIPPED: "Your order has been sent for delivery",
        NotificationType.ORDER_CANCELLED: "Your order has been cancelled",
    }

    def __init__(self, client: NotificationClient):
        self.client = client

    async def send_notification(
        self,
        order_id: UUID,
        user_id: str,
        notification_type: NotificationType,
    ) -> None:
        message = self._MESSAGES.get(notification_type)
        if not message:
            logger.warning(f"Unknown notification type: {notification_type}")
            return

        idempotency_key = f"{notification_type.value}_{order_id}"

        try:
            dto = SendNotificationDTO(
                user_id=user_id,
                message=message,
                reference_id=order_id,
                idempotency_key=idempotency_key,
            )
            await self.client.send_notification(dto)
            logger.info(f"Notification sent for order {order_id}: {notification_type.value}")

        except Exception as e:
            logger.error(
                f"Failed to send {notification_type.value} notification for order {order_id}: {e}"
            )
