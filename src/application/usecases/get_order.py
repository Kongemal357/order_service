import logging
from uuid import UUID

from src.application.dto import OrderResponseDTO
from src.application.ports import UnitOfWork
from src.domain.exceptions import OrderNotFoundError

logger = logging.getLogger(__name__)


class GetOrderUseCase:
    """Use case for retrieving an order by ID."""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, order_id: UUID) -> OrderResponseDTO:
        logger.info(f"Getting order: {order_id}")

        async with self.uow as uow:
            # Get order from repository
            order = await uow.order_repo.get_by_id(order_id)

            if not order:
                logger.warning(f"Order not found: {order_id}")
                raise OrderNotFoundError(f"Order {order_id} not found")

            logger.info(f"Order found: {order_id}")

            # Return DTO
            return OrderResponseDTO.from_domain(order)
