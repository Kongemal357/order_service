import logging
from decimal import Decimal
from urllib.parse import urljoin
from uuid import uuid4

from src.application.dto import CreateOrderDTO, OrderResponseDTO
from src.application.dto.payment_dto import CreatePaymentDTO
from src.application.ports import CatalogClient, UnitOfWork
from src.application.ports.payment_client import PaymentClient
from src.application.services.notification_service import NotificationService
from src.domain.exceptions import (
    CatalogServiceError,
    InsufficientStockError,
    PaymentError,
)
from src.domain.models import NotificationType, Order, OrderStatus
from src.settings import settings

logger = logging.getLogger(__name__)


class CreateOrderUseCase:
    """
    Use case for creating a new order.
    """

    def __init__(
        self,
        uow_factory: UnitOfWork,
        catalog_client: CatalogClient,
        payment_client: PaymentClient,
        notification_service: NotificationService,
    ):
        self.uow_factory = uow_factory
        self.catalog_client = catalog_client
        self.payment_client = payment_client
        self.notification_service = notification_service

    async def execute(self, dto: CreateOrderDTO) -> OrderResponseDTO:
        logger.info(f"Creating order: user={dto.user_id}, item={dto.item_id}")

        # Check idempotency
        async with self.uow_factory() as uow:
            existing_order = await uow.order_repo.get_by_idempotency_key(dto.idempotency_key)
            if existing_order:
                logger.info("Idempotent request: returning existing order")
                return OrderResponseDTO.from_domain(existing_order)

        # Validate item availability
        try:
            catalog_item = await self.catalog_client.get_item(dto.item_id)
        except CatalogServiceError as e:
            logger.error(f"Catalog Service error: {e}")
            raise

        if catalog_item.available_qty < dto.quantity:
            raise InsufficientStockError(
                f"Not enough stock. Available: {catalog_item.available_qty}"
            )

        # Create and save order
        async with self.uow_factory() as uow:
            order = Order.create(
                user_id=dto.user_id,
                item_id=dto.item_id,
                quantity=dto.quantity,
                item_price=Decimal(catalog_item.price),
                idempotency_key=dto.idempotency_key,
            )
            await uow.order_repo.save(order)
            await uow.commit()
            logger.info(f"Order saved: {order.id}")

        # Send notification
        await self.notification_service.send_notification(
            order.id,
            order.user_id,
            NotificationType.ORDER_CREATED,
        )

        # Create payment
        try:
            callback_url = urljoin(settings.INTERNAL_HOSTNAME, "/api/orders/payment-callback")
            payment_dto = CreatePaymentDTO(
                order_id=order.id,
                amount=order.total_amount.amount,
                callback_url=callback_url,
                idempotency_key=str(uuid4()),
            )

            payment_response = await self.payment_client.create_payment(payment_dto)
            logger.info(f"Payment created: {payment_response.id}")

        except PaymentError as e:
            logger.error(f"Payment failed: {e}")

            # Cancel order with failed payment
            async with self.uow_factory() as uow:
                order = await uow.order_repo.get_by_id(order.id)
                if order and order.status == OrderStatus.NEW:
                    order.cancel()
                    await uow.order_repo.update(order)
                    await uow.commit()
                    logger.info(f"Order cancelled due to payment failure: {order.id}")

            # Send notification
            await self.notification_service.send_notification(
                order.id,
                order.user_id,
                NotificationType.ORDER_CANCELLED,
            )
            raise

        # Update order's payment_id
        async with self.uow_factory() as uow:
            order = await uow.order_repo.get_by_id(order.id)
            order.set_payment_id(payment_response.id)
            await uow.order_repo.update(order)
            await uow.commit()
            logger.info(f"Order updated with payment_id: {order.id}")

        return OrderResponseDTO.from_domain(order)
