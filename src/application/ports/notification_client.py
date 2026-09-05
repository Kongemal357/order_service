from abc import ABC, abstractmethod

from src.application.dto.notification_dto import SendNotificationDTO


class NotificationClient(ABC):
    """
    Port for Notification Service client operations.
    """

    @abstractmethod
    async def send_notification(self, dto: SendNotificationDTO) -> None:
        pass
