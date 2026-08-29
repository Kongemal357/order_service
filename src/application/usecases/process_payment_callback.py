import logging

from src.application.dto.order_dto import OrderResponseDTO
from src.application.dto.payment_dto import PaymentCallbackDTO
from src.application.ports.uow import UnitOfWork
from src.domain.exceptions import DomainError, OrderNotFoundError
from src.domain.models import OrderStatus, PaymentStatus

logger = logging.getLogger(__name__)


class ProcessPaymentCallbackUseCase:
    """Use case for processing payment callback from Payment Service."""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, dto: PaymentCallbackDTO) -> OrderResponseDTO:
        logger.info(
            f"Processing payment callback: order={dto.order_id}, "
            f"payment={dto.payment_id}, status={dto.status}"
        )

        async with self.uow as uow:
            # Get order
            order = await uow.order_repo.get_by_id(dto.order_id)
            if not order:
                logger.warning(f"Order not found: {dto.order_id}")
                raise OrderNotFoundError(f"Order {dto.order_id} not found")

            # Idempotency check by payment_id
            if order.payment_id == dto.payment_id:
                # Check if already processed (final state)
                if order.status in (OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.CANCELLED):
                    logger.info(
                        f"Payment {dto.payment_id} already processed, order status: {order.status}"
                    )
                    return OrderResponseDTO.from_domain(order)

            # Verify payment_id matches
            if order.payment_id != dto.payment_id:
                logger.error(
                    f"Payment ID mismatch: expected {order.payment_id}, got {dto.payment_id}"
                )
                raise DomainError(f"Payment ID mismatch for order {order.id}")

            # Update order based on payment status
            if dto.status == PaymentStatus.SUCCEEDED:
                logger.info(f"Payment succeeded for order {order.id}")
                order.mark_paid()
            else:
                reason = dto.error_message or "Payment failed"
                logger.info(f"Payment failed for order {order.id}: {reason}")
                order.cancel()

            # Save changes
            await uow.order_repo.update(order)
            await uow.commit()

            logger.info(f"Order {order.id} updated to {order.status}")
            return OrderResponseDTO.from_domain(order)
