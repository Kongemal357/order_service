from dataclasses import dataclass
from uuid import UUID

from src.domain.models import Order


@dataclass(frozen=True)
class OrderPaidEventDTO:
    """DTO for ORDER.PAID event."""

    event_type: str = "order.paid"
    order_id: UUID = None
    item_id: UUID = None
    quantity: int = None
    idempotency_key: str = None

    def to_dict(self) -> dict:
        """Convert to dictionary for Kafka."""
        return {
            "event_type": self.event_type,
            "order_id": str(self.order_id),
            "item_id": str(self.item_id),
            "quantity": self.quantity,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_order(cls, order: "Order", idempotency_key: str) -> "OrderPaidEventDTO":
        """Create from order domain model."""
        return cls(
            order_id=order.id,
            item_id=order.item_id,
            quantity=order.quantity,
            idempotency_key=idempotency_key,
        )

    @classmethod
    def from_payload(cls, payload: dict) -> "OrderPaidEventDTO":
        """Create DTO from outbox payload."""
        return cls(
            order_id=UUID(payload["order_id"]),
            item_id=UUID(payload["item_id"]),
            quantity=payload["quantity"],
            idempotency_key=payload["idempotency_key"],
        )


@dataclass(frozen=True)
class OrderShippedEventDTO:
    """DTO for ORDER.SHIPPED event."""

    event_type: str = "order.shipped"
    order_id: UUID = None
    item_id: UUID = None
    quantity: int = None
    shipment_id: UUID = None
    idempotency_key: str = None

    @classmethod
    def from_dict(cls, data: dict) -> "OrderShippedEventDTO":
        """Create from Kafka message."""
        return cls(
            order_id=UUID(data["order_id"]),
            item_id=UUID(data["item_id"]),
            quantity=data["quantity"],
            shipment_id=UUID(data["shipment_id"]),
            idempotency_key=data.get("idempotency_key"),
        )


@dataclass(frozen=True)
class OrderCancelledEventDTO:
    """DTO for ORDER.CANCELLED event."""

    event_type: str = "order.cancelled"
    order_id: UUID = None
    item_id: UUID = None
    quantity: int = None
    reason: str = None
    idempotency_key: str = None

    @classmethod
    def from_dict(cls, data: dict) -> "OrderCancelledEventDTO":
        """Create from Kafka message."""
        return cls(
            order_id=UUID(data["order_id"]),
            item_id=UUID(data["item_id"]),
            quantity=data["quantity"],
            reason=data.get("reason", "No reason provided"),
            idempotency_key=data.get("idempotency_key"),
        )
