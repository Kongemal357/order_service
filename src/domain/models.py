from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from src.domain.exceptions import DomainError


class PaymentStatus(StrEnum):
    """Payment status."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class OrderStatus(StrEnum):
    """Order status enumeration."""

    NEW = "NEW"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"


@dataclass
class Order:
    """Domain aggregate representing an order."""

    id: UUID
    user_id: str
    item_id: UUID
    quantity: int
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    idempotency_key: str | None = None
    payment_id: UUID | None = None

    @classmethod
    def create(
        cls,
        user_id: str,
        item_id: UUID,
        quantity: int,
        idempotency_key: str,
    ) -> "Order":
        """Factory method to create a new order with NEW status."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return cls(
            id=uuid4(),
            user_id=user_id,
            item_id=item_id,
            quantity=quantity,
            status=OrderStatus.NEW,
            created_at=now,
            updated_at=now,
            idempotency_key=idempotency_key,
        )

    def mark_paid(self) -> None:
        """Transition order to PAID status."""
        if self.status != OrderStatus.NEW:
            raise DomainError(f"Cannot mark order {self.id} as paid from status {self.status}")
        self.status = OrderStatus.PAID
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def mark_shipped(self) -> None:
        """Transition order to SHIPPED status."""
        if self.status != OrderStatus.PAID:
            raise DomainError(f"Cannot mark order {self.id} as shipped from status {self.status}")
        self.status = OrderStatus.SHIPPED
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def cancel(self) -> None:
        """Transition order to CANCELLED status."""
        if self.status == OrderStatus.CANCELLED:
            raise DomainError(f"Order {self.id} is already cancelled")
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def set_payment_id(self, payment_id: UUID) -> None:
        """Set payment ID when payment is created."""
        self.payment_id = payment_id
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class CatalogItem:
    """Domain representation of a catalog item."""

    id: UUID
    name: str
    price: str
    available_qty: int
    created_at: datetime


class OutboxStatus(StrEnum):
    """Status of outbox event."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass
class OutboxEvent:
    """Outbox event for reliable event publishing."""

    id: UUID
    event_type: str
    payload: dict[str, Any]
    idempotency_key: str
    status: OutboxStatus
    created_at: datetime
    sent_at: datetime | None = None

    @classmethod
    def create(
        cls,
        event_type: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> "OutboxEvent":
        return cls(
            id=uuid4(),
            event_type=event_type,
            payload=payload,
            idempotency_key=idempotency_key,
            status=OutboxStatus.PENDING,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            sent_at=None,
        )

    def mark_sent(self) -> None:
        """Mark event as sent."""
        self.status = OutboxStatus.SENT
        self.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def mark_failed(self) -> None:
        """Mark event as failed."""
        self.status = OutboxStatus.FAILED


@dataclass
class InboxRecord:
    """Inbox record for idempotent event processing."""

    id: UUID
    event_id: str
    idempotency_key: str
    event_type: str
    processed_at: datetime

    @classmethod
    def create(
        cls,
        event_id: str,
        idempotency_key: str,
        event_type: str,
    ) -> "InboxRecord":
        return cls(
            id=uuid4(),
            event_id=event_id,
            idempotency_key=idempotency_key,
            event_type=event_type,
            processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
