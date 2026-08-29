"""
Payment Service HTTP client implementation.
"""

import logging
from decimal import Decimal
from urllib.parse import urljoin
from uuid import UUID

import httpx

from src.application.dto.payment_dto import CreatePaymentDTO, PaymentResponseDTO
from src.application.ports.payment_client import PaymentClient as PaymentClientPort
from src.domain.exceptions import PaymentError
from src.settings import settings

logger = logging.getLogger(__name__)


class PaymentHTTPClient(PaymentClientPort):
    """
    HTTP client for Payment Service.
    """

    def __init__(self):
        self.base_url = settings.CAPASHINO_BASE_URL.rstrip("/")
        self.api_key = settings.CAPASHINO_API_KEY
        self.timeout = 10.0

        if not self.api_key:
            logger.warning("CAPASHINO_API_KEY is not set! Payment requests will fail.")

    async def create_payment(self, dto: CreatePaymentDTO) -> PaymentResponseDTO:
        url = urljoin(self.base_url, "/api/payments")
        headers = {"X-API-Key": self.api_key}

        payload = {
            "order_id": str(dto.order_id),
            "amount": str(dto.amount),
            "callback_url": dto.callback_url,
            "idempotency_key": dto.idempotency_key,
        }

        logger.debug(f"Creating payment: order={dto.order_id}, amount={dto.amount}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()
                logger.debug(f"Payment response: {data}")

                return PaymentResponseDTO(
                    id=UUID(data["id"]),
                    order_id=UUID(data["order_id"]),
                    amount=Decimal(data["amount"]),
                    status=data["status"],
                    idempotency_key=data["idempotency_key"],
                    created_at=data["created_at"],
                )

        except httpx.TimeoutException as e:
            logger.error(f"Payment Service timeout: {e}")
            raise PaymentError(f"Payment Service timeout: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Payment Service HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise PaymentError(
                f"Payment Service error: {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Unexpected error creating payment: {e}")
            raise PaymentError(f"Failed to create payment: {e}")
