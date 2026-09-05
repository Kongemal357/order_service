import logging
from urllib.parse import urljoin

import httpx

from src.application.dto.notification_dto import SendNotificationDTO
from src.application.ports.notification_client import NotificationClient as NotificationClientPort
from src.domain.exceptions import NotificationError
from src.settings import settings

logger = logging.getLogger(__name__)


class NotificationHTTPClient(NotificationClientPort):
    """
    HTTP client for Notification Service.
    Sends notifications with idempotency key.
    """

    def __init__(self):
        self.base_url = settings.CAPASHINO_BASE_URL.rstrip("/")
        self.api_key = settings.CAPASHINO_API_KEY
        self.timeout = 5.0

    async def send_notification(self, dto: SendNotificationDTO) -> None:
        url = urljoin(self.base_url, "/api/notifications")
        headers = {"X-API-Key": self.api_key}

        payload = {
            "message": dto.message,
            "reference_id": str(dto.reference_id),
            "idempotency_key": dto.idempotency_key,
        }

        logger.debug(
            f"Sending notification: reference={dto.reference_id}, key={dto.idempotency_key}"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"Notification sent for order {dto.reference_id}")

        except httpx.TimeoutException:
            logger.warning(f"Notification timeout for order {dto.reference_id}")
            raise NotificationError(f"Notification timeout for order {dto.reference_id}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Notification error: {e.response.status_code} - {e.response.text}")
            raise NotificationError(f"Notification error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected notification error: {e}")
            raise NotificationError(f"Unexpected notification error: {e}")
