from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from src.application.dto import CreateOrderDTO
from src.domain.models import OrderStatus


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



class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str