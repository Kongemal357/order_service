from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.application.dto import CreateOrderDTO
from src.application.dto.payment_dto import PaymentCallbackDTO
from src.domain.models import OrderStatus, PaymentStatus


class CreateOrderRequest(BaseModel):
    """Request schema for creating an order."""

    user_id: str = Field(..., description="ID of the user placing the order")
    item_id: UUID = Field(..., description="ID of the item to order")
    quantity: int = Field(..., gt=0, description="Quantity to order (must be > 0)")
    idempotency_key: str = Field(..., description="Unique key for idempotency")

    def to_dto(self) -> CreateOrderDTO:
        return CreateOrderDTO(
            user_id=self.user_id,
            item_id=self.item_id,
            quantity=self.quantity,
            idempotency_key=self.idempotency_key,
        )


class OrderResponse(BaseModel):
    """Response schema for order data."""

    id: UUID
    user_id: str
    quantity: int
    item_id: UUID
    status: OrderStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class PaymentCallbackRequest(BaseModel):
    """Request schema for payment callback."""

    payment_id: UUID = Field(..., description="Payment ID")
    order_id: UUID = Field(..., description="Order ID")
    status: PaymentStatus = Field(..., description="Payment status: succeeded/failed")
    amount: Decimal = Field(..., description="Payment amount")
    error_message: str | None = Field(None, description="Error message if failed")

    def to_dto(self) -> PaymentCallbackDTO:
        return PaymentCallbackDTO(
            payment_id=self.payment_id,
            order_id=self.order_id,
            status=self.status,
            amount=self.amount,
            error_message=self.error_message,
        )


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str
