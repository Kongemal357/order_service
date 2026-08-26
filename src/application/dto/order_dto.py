from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.domain.models import Order, OrderStatus


@dataclass(frozen=True)
class CreateOrderDTO:
    """DTO for creating a new order."""

    user_id: str
    item_id: UUID
    quantity: int
    idempotency_key: str

    def __post_init__(self):
        """Validate DTO data after initialization."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        if not self.user_id:
            raise ValueError("User ID cannot be empty")
        if not self.idempotency_key:
            raise ValueError("Idempotency key cannot be empty")


@dataclass(frozen=True)
class OrderResponseDTO:
    """DTO for returning order data from Application layer."""

    id: UUID
    user_id: str
    item_id: UUID
    quantity: int
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    idempotency_key: Optional[str] = None

    @classmethod
    def from_domain(cls, order: Order) -> "OrderResponseDTO":
        """Create DTO from Domain Order model."""
        return cls(
            id=order.id,
            user_id=order.user_id,
            item_id=order.item_id,
            quantity=order.quantity,
            status=order.status,
            created_at=order.created_at,
            updated_at=order.updated_at,
            idempotency_key=order.idempotency_key,
        )

    def to_domain(self) -> Order:
        """Convert DTO back to Domain Order model."""
        return Order(
            id=self.id,
            user_id=self.user_id,
            item_id=self.item_id,
            quantity=self.quantity,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            idempotency_key=self.idempotency_key,
        )
