import logging
from uuid import uuid4

from src.application.dto.event_dto import OrderPaidEventDTO
from src.application.dto.order_dto import OrderResponseDTO
from src.application.dto.payment_dto import PaymentCallbackDTO
from src.application.ports.uow import UnitOfWork
from src.domain.exceptions import DomainError, OrderNotFoundError
from src.domain.models import OrderStatus, OutboxEvent, PaymentStatus

logger = logging.getLogger(__name__)


class ProcessPaymentCallbackUseCase:
    """
    Use case for processing payment callback from Payment Service.
    After updating order status, saves event to outbox for publishing.
    """

    def __init__(
        self,
        uow_factory: UnitOfWork,
    ):
        self.uow_factory = uow_factory

    async def execute(self, dto: PaymentCallbackDTO) -> OrderResponseDTO:
        logger.info(
            f"Processing payment callback: order={dto.order_id}, "
            f"payment={dto.payment_id}, status={dto.status}"
        )

        async with self.uow_factory() as uow:
            # Get order
            order = await uow.order_repo.get_by_id(dto.order_id)
            if not order:
                logger.warning(f"Order not found: {dto.order_id}")
                raise OrderNotFoundError(f"Order {dto.order_id} not found")

            # Idempotency check by payment_id
            if order.payment_id == dto.payment_id:
                # Already processed → return existing order
                if order.status in (OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.CANCELLED):
                    logger.info(
                        f"Payment {dto.payment_id} already processed, "
                        f"order {order.id} in final state: {order.status}"
                    )
                    return OrderResponseDTO.from_domain(order)
                # payment_id matches but status not final → continue to update
                logger.warning(
                    f"Payment {dto.payment_id} already associated with order {order.id}, "
                    f"but order status is {order.status}. Updating..."
                )

            # Verify payment_id matches
            elif order.payment_id is None:
                # Callback arrived before we saved payment_id → set it now
                logger.warning(f"Order {order.id} has no payment_id, setting to {dto.payment_id}")
                order.set_payment_id(dto.payment_id)
                await uow.order_repo.update(order)

            elif order.payment_id != dto.payment_id:
                # Payment ID mismatch → error
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

            await uow.order_repo.update(order)

            # Save outbox event (only if paid)
            if order.status == OrderStatus.PAID:
                idempotency_key = str(uuid4())
                event_dto = OrderPaidEventDTO.from_order(order, idempotency_key)

                outbox_event = OutboxEvent.create(
                    event_type="order.paid",
                    payload=event_dto.to_dict(),
                    idempotency_key=idempotency_key,
                )
                await uow.outbox_repo.save(outbox_event)
                logger.info(f"Outbox event saved: {outbox_event.id}")

            # Commit and return
            await uow.commit()

            logger.info(f"Order {order.id} updated to {order.status}")
            return OrderResponseDTO.from_domain(order)
