from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from src.domain.exceptions import DomainError


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

    def cancel(self, reason: str = "Cancelled") -> None:
        """Transition order to CANCELLED status."""
        if self.status in (OrderStatus.SHIPPED, OrderStatus.CANCELLED):
            raise DomainError(f"Cannot cancel order {self.id} with status {self.status}")
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class CatalogItem:
    """Domain representation of a catalog item."""

    id: UUID
    name: str
    price: str
    available_qty: int
    created_at: datetime