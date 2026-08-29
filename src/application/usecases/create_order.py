import logging
from decimal import Decimal
from urllib.parse import urljoin
from uuid import uuid4

from src.application.dto import CreateOrderDTO, OrderResponseDTO
from src.application.dto.payment_dto import CreatePaymentDTO
from src.application.ports import CatalogClient, UnitOfWork
from src.application.ports.payment_client import PaymentClient
from src.domain.exceptions import (
    CatalogServiceError,
    InsufficientStockError,
    PaymentError,
)
from src.domain.models import Order, OrderStatus
from src.settings import settings

logger = logging.getLogger(__name__)


class CreateOrderUseCase:
    """
    Use case for creating a new order.

    Flow:
    1. Check idempotency - if order with same key exists, return it
    2. Validate item availability via Catalog Service
    3. Create and save the order
    4. Return order data as DTO
    """

    def __init__(
        self,
        uow: UnitOfWork,
        catalog_client: CatalogClient,
        payment_client: PaymentClient,
    ):
        self.uow = uow
        self.catalog_client = catalog_client
        self.payment_client = payment_client

    async def execute(self, dto: CreateOrderDTO) -> OrderResponseDTO:
        logger.info(f"Creating order: user={dto.user_id}, item={dto.item_id}")

        async with self.uow as uow:
            existing_order = await uow.order_repo.get_by_idempotency_key(dto.idempotency_key)
            if existing_order:
                logger.info("Idempotent request: returning existing order")
                return OrderResponseDTO.from_domain(existing_order)

        try:
            catalog_item = await self.catalog_client.get_item(dto.item_id)
        except CatalogServiceError as e:
            logger.error(f"Catalog Service error: {e}")
            raise

        if catalog_item.available_qty < dto.quantity:
            raise InsufficientStockError(
                f"Not enough stock. Available: {catalog_item.available_qty}"
            )

        total_amount = Decimal(catalog_item.price) * dto.quantity

        async with self.uow as uow:
            order = Order.create(
                user_id=dto.user_id,
                item_id=dto.item_id,
                quantity=dto.quantity,
                idempotency_key=dto.idempotency_key,
            )
            await uow.order_repo.save(order)
            await uow.commit()
            logger.info(f"Order saved: {order.id}")

        try:
            callback_url = urljoin(settings.INTERNAL_HOSTNAME, "/api/orders/payment-callback")
            payment_dto = CreatePaymentDTO(
                order_id=order.id,
                amount=total_amount,
                callback_url=callback_url,
                idempotency_key=str(uuid4()),
            )

            payment_response = await self.payment_client.create_payment(payment_dto)
            logger.info(f"Payment created: {payment_response.id}")

        except PaymentError as e:
            logger.error(f"Payment failed: {e}")

            async with self.uow as uow:
                order = await uow.order_repo.get_by_id(order.id)
                if order and order.status == OrderStatus.NEW:
                    order.cancel()
                    await uow.order_repo.update(order)
                    await uow.commit()
                    logger.info(f"Order cancelled due to payment failure: {order.id}")
            raise

        async with self.uow as uow:
            order = await uow.order_repo.get_by_id(order.id)
            order.set_payment_id(payment_response.id)
            await uow.order_repo.update(order)
            await uow.commit()
            logger.info(f"Order updated with payment_id: {order.id}")

        return OrderResponseDTO.from_domain(order)
