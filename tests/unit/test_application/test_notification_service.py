from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from src.application.dto.notification_dto import SendNotificationDTO
from src.application.ports.notification_client import NotificationClient
from src.application.services.notification_service import NotificationService
from src.domain.models import NotificationType

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_notification_client():
    client = Mock(spec=NotificationClient)
    client.send_notification = AsyncMock()
    return client


@pytest.fixture
def service(mock_notification_client):
    return NotificationService(client=mock_notification_client)


class TestSendNotification:
    """Tests for NotificationService.send_notification."""

    @pytest.mark.parametrize(
        "notification_type, expected_message",
        [
            (
                NotificationType.ORDER_CREATED,
                "Your order has been created and requires payment",
            ),
            (
                NotificationType.ORDER_PAID,
                "Your order has been successfully paid and ready for shipment",
            ),
            (
                NotificationType.ORDER_SHIPPED,
                "Your order has been sent for delivery",
            ),
            (
                NotificationType.ORDER_CANCELLED,
                "Your order has been cancelled",
            ),
        ],
    )
    async def test_sends_notification_with_correct_message(
        self,
        service,
        mock_notification_client,
        notification_type,
        expected_message,
    ):
        order_id = uuid4()

        await service.send_notification(order_id, notification_type)

        mock_notification_client.send_notification.assert_awaited_once()
        dto: SendNotificationDTO = mock_notification_client.send_notification.await_args.args[0]
        assert isinstance(dto, SendNotificationDTO)
        assert dto.message == expected_message
        assert dto.reference_id == order_id
        assert dto.idempotency_key is not None

    async def test_generates_unique_idempotency_key_per_call(
        self, service, mock_notification_client
    ):
        order_id = uuid4()
        notification_type = NotificationType.ORDER_PAID

        await service.send_notification(order_id, notification_type)
        await service.send_notification(order_id, notification_type)

        assert mock_notification_client.send_notification.await_count == 2
        first_dto: SendNotificationDTO = mock_notification_client.send_notification.await_args_list[
            0
        ].args[0]
        second_dto: SendNotificationDTO = (
            mock_notification_client.send_notification.await_args_list[1].args[0]
        )
        assert first_dto.idempotency_key != second_dto.idempotency_key

    async def test_does_not_send_for_unknown_notification_type(
        self, service, mock_notification_client
    ):
        order_id = uuid4()

        # Simulate an unknown enum-like value not present in _MESSAGES
        unknown_type = "unknown_notification_type"

        await service.send_notification(order_id, unknown_type)

        mock_notification_client.send_notification.assert_not_awaited()

    async def test_does_not_raise_when_client_fails(self, service, mock_notification_client):
        order_id = uuid4()
        mock_notification_client.send_notification.side_effect = RuntimeError(
            "notification service is down"
        )

        # Should not raise
        await service.send_notification(order_id, NotificationType.ORDER_SHIPPED)

        mock_notification_client.send_notification.assert_awaited_once()

    async def test_returns_none_on_success(self, service):
        order_id = uuid4()

        result = await service.send_notification(order_id, NotificationType.ORDER_PAID)

        assert result is None

    async def test_returns_none_on_client_failure(self, service, mock_notification_client):
        order_id = uuid4()
        mock_notification_client.send_notification.side_effect = RuntimeError("boom")

        result = await service.send_notification(order_id, NotificationType.ORDER_PAID)

        assert result is None

    async def test_passes_uuid_order_id_as_reference_id(self, service, mock_notification_client):
        order_id = UUID("bdece4e4-5936-43fb-913a-9c3f195c4f43")

        await service.send_notification(order_id, NotificationType.ORDER_CREATED)

        dto: SendNotificationDTO = mock_notification_client.send_notification.await_args.args[0]
        assert dto.reference_id == order_id
