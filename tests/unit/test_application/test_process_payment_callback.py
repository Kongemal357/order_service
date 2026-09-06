from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from src.application.dto.payment_dto import PaymentCallbackDTO
from src.application.usecases.process_payment_callback import ProcessPaymentCallbackUseCase
from src.domain.exceptions import DomainError, OrderNotFoundError
from src.domain.models import Order, OrderStatus, PaymentStatus

pytestmark = pytest.mark.asyncio


@pytest.fixture
def payment_callback_dto():
    return PaymentCallbackDTO(
        payment_id=uuid4(),
        order_id=uuid4(),
        status=PaymentStatus.SUCCEEDED,
        amount=Decimal("100.00"),
        error_message=None,
    )


@pytest.fixture
def payment_callback_failed_dto():
    return PaymentCallbackDTO(
        payment_id=uuid4(),
        order_id=uuid4(),
        status=PaymentStatus.FAILED,
        amount=Decimal("100.00"),
        error_message="Insufficient funds",
    )


class TestProcessPaymentCallbackUseCase:
    async def test_callback_success(
        self,
        payment_callback_dto,
        mock_uow_factory,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            id=payment_callback_dto.order_id,
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            status=OrderStatus.NEW,
            payment_id=payment_callback_dto.payment_id,
            created_at=now,
            updated_at=now,
            idempotency_key=None,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = order

        use_case = ProcessPaymentCallbackUseCase(
            uow_factory=mock_uow_factory,
            notification_service=mock_notification_service,
        )

        result = await use_case.execute(payment_callback_dto)

        assert result.status == OrderStatus.PAID.value
        mock_uow.order_repo.update.assert_called()
        mock_uow.outbox_repo.save.assert_called()
        mock_notification_service.send_notification.assert_called()

    async def test_callback_failed(
        self,
        payment_callback_failed_dto,
        mock_uow_factory,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            id=payment_callback_failed_dto.order_id,
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            status=OrderStatus.NEW,
            payment_id=payment_callback_failed_dto.payment_id,
            created_at=now,
            updated_at=now,
            idempotency_key=None,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = order

        use_case = ProcessPaymentCallbackUseCase(
            uow_factory=mock_uow_factory,
            notification_service=mock_notification_service,
        )

        result = await use_case.execute(payment_callback_failed_dto)

        assert result.status == OrderStatus.CANCELLED.value
        mock_uow.order_repo.update.assert_called()

    async def test_callback_payment_id_mismatch(
        self,
        payment_callback_dto,
        mock_uow_factory,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            id=payment_callback_dto.order_id,
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            status=OrderStatus.NEW,
            payment_id=uuid4(),
            created_at=now,
            updated_at=now,
            idempotency_key=None,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = order

        use_case = ProcessPaymentCallbackUseCase(
            uow_factory=mock_uow_factory,
            notification_service=mock_notification_service,
        )

        with pytest.raises(DomainError, match="Payment ID mismatch"):
            await use_case.execute(payment_callback_dto)

    async def test_callback_order_not_found(
        self,
        payment_callback_dto,
        mock_uow_factory,
        mock_notification_service,
    ):
        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = None

        use_case = ProcessPaymentCallbackUseCase(
            uow_factory=mock_uow_factory,
            notification_service=mock_notification_service,
        )

        with pytest.raises(OrderNotFoundError):
            await use_case.execute(payment_callback_dto)

    async def test_callback_already_processed(
        self,
        payment_callback_dto,
        mock_uow_factory,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            id=payment_callback_dto.order_id,
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            status=OrderStatus.PAID,
            payment_id=payment_callback_dto.payment_id,
            created_at=now,
            updated_at=now,
            idempotency_key=None,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = order

        use_case = ProcessPaymentCallbackUseCase(
            uow_factory=mock_uow_factory,
            notification_service=mock_notification_service,
        )

        result = await use_case.execute(payment_callback_dto)

        assert result.status == OrderStatus.PAID.value
        mock_uow.order_repo.update.assert_not_called()
        mock_uow.outbox_repo.save.assert_not_called()

    async def test_callback_saves_outbox_event(
        self,
        payment_callback_dto,
        mock_uow_factory,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            id=payment_callback_dto.order_id,
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            status=OrderStatus.NEW,
            payment_id=payment_callback_dto.payment_id,
            created_at=now,
            updated_at=now,
            idempotency_key=None,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = order

        use_case = ProcessPaymentCallbackUseCase(
            uow_factory=mock_uow_factory,
            notification_service=mock_notification_service,
        )

        await use_case.execute(payment_callback_dto)

        mock_uow.outbox_repo.save.assert_called_once()
        call_args = mock_uow.outbox_repo.save.call_args[0][0]
        assert call_args.event_type == "order.paid"
        assert call_args.status.value == "pending"
