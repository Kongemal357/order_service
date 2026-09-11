import logging
from urllib.parse import urljoin

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.application.dto.notification_dto import SendNotificationDTO
from src.application.ports.notification_client import NotificationClient
from src.domain.exceptions import NotificationError
from src.settings import settings

logger = logging.getLogger(__name__)


class _RetryableHTTPError(Exception):
    """Internal to NotificationHTTPClient. Transient HTTP failure (5xx, timeout, network)."""


class _PermanentHTTPError(Exception):
    """Internal to NotificationHTTPClient. Permanent HTTP failure (4xx)."""


class NotificationHTTPClient(NotificationClient):
    """
    HTTP client for Notification Service.
    Retries transient failures (5xx, timeouts, network) and converts
    all failures into the domain-level NotificationError.
    """

    def __init__(self):
        self.base_url = settings.CAPASHINO_BASE_URL.rstrip("/")
        self.api_key = settings.CAPASHINO_API_KEY
        self.timeout = 5.0

    async def send_notification(self, dto: SendNotificationDTO) -> None:
        try:
            await self._send_with_retry(dto)
        except (_RetryableHTTPError, _PermanentHTTPError) as e:
            raise NotificationError(str(e)) from e

    @retry(
        retry=retry_if_exception_type(_RetryableHTTPError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _send_with_retry(self, dto: SendNotificationDTO) -> None:
        url = urljoin(self.base_url, "/api/notifications")
        headers = {"X-API-Key": self.api_key}

        payload = {
            "message": dto.message,
            "reference_id": str(dto.reference_id),
            "idempotency_key": str(dto.idempotency_key),
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
            raise _RetryableHTTPError(f"Notification timeout for order {dto.reference_id}")

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            logger.error(
                "Notification HTTP error\n"
                "  URL: %s\n"
                "  Status: %s\n"
                "  Reference: %s\n"
                "  Request payload: %s\n"
                "  Response body: %s\n"
                "  Response headers: %s",
                e.request.url,
                status,
                dto.reference_id,
                payload,
                e.response.text,
                dict(e.response.headers),
            )
            if 500 <= status < 600:
                raise _RetryableHTTPError(f"Notification server error: {status}")
            raise _PermanentHTTPError(f"Notification client error: {status}")

        except httpx.RequestError as e:
            logger.error(
                "Notification request error\n"
                "  URL: %s\n"
                "  Reference: %s\n"
                "  Error type: %s\n"
                "  Error: %s",
                e.request.url,
                dto.reference_id,
                type(e).__name__,
                str(e),
            )
            raise _RetryableHTTPError(f"Notification request error: {e}")

        except Exception as e:
            logger.exception(f"Unexpected notification error for order {dto.reference_id}")
            raise _PermanentHTTPError(f"Unexpected notification error: {e}")
