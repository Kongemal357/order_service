"""
Data Transfer Objects for payment-related operations.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from src.domain.models import PaymentStatus


@dataclass(frozen=True)
class CreatePaymentDTO:
    """DTO for creating a payment."""

    order_id: UUID
    amount: Decimal
    callback_url: str
    idempotency_key: str


@dataclass(frozen=True)
class PaymentResponseDTO:
    """DTO for payment response."""

    id: UUID
    order_id: UUID
    amount: Decimal
    status: PaymentStatus
    idempotency_key: str
    created_at: str


@dataclass(frozen=True)
class PaymentCallbackDTO:
    """DTO for payment callback from Payments Service."""

    payment_id: UUID
    order_id: UUID
    status: PaymentStatus
    amount: Decimal
    error_message: Optional[str] = None
