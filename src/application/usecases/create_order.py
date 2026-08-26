import logging

from src.application.dto import CreateOrderDTO, OrderResponseDTO
from src.application.ports import CatalogClient, UnitOfWork
from src.domain.exceptions import (
    CatalogServiceError,
    InsufficientStockError,
)
from src.domain.models import Order

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

    def __init__(self, uow: UnitOfWork, catalog_client: CatalogClient):
        self.uow = uow
        self.catalog_client = catalog_client

    async def execute(self, dto: CreateOrderDTO) -> OrderResponseDTO:
        logger.info(
            f"Creating order: user={dto.user_id}, item={dto.item_id}, "
            f"qty={dto.quantity}, key={dto.idempotency_key}"
        )

        async with self.uow as uow:
            # Check idempotency
            existing_order = await uow.order_repo.get_by_idempotency_key(dto.idempotency_key)
            if existing_order:
                logger.info(f"Idempotent request: returning existing order {existing_order.id}")
                return OrderResponseDTO.from_domain(existing_order)

            # Validate item availability via Catalog Service
            logger.info(f"Checking item availability via Catalog Service: {dto.item_id}")
            try:
                catalog_item_dto = await self.catalog_client.get_item(dto.item_id)
            except CatalogServiceError as e:
                logger.error(f"Catalog Service error: {e}")
                raise

            if catalog_item_dto.available_qty < dto.quantity:
                logger.warning(
                    f"Insufficient stock: requested={dto.quantity}, "
                    f"available={catalog_item_dto.available_qty}"
                )
                raise InsufficientStockError(
                    f"Not enough stock. Available: {catalog_item_dto.available_qty}, "
                    f"Requested: {dto.quantity}"
                )

            # Create and save order
            order = Order.create(
                user_id=dto.user_id,
                item_id=dto.item_id,
                quantity=dto.quantity,
                idempotency_key=dto.idempotency_key,
            )

            logger.info(f"Saving order: {order.id}")
            saved_order = await uow.order_repo.save(order)
            await uow.commit()

            logger.info(f"Order created successfully: {saved_order.id}")

            # Return DTO (not domain model)
            return OrderResponseDTO.from_domain(saved_order)
