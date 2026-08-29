import pytest

from src.domain.exceptions import DomainError
from src.domain.models import Order, OrderStatus


class TestOrder:
    """Tests for Order domain entity."""

    def test_create_order(self, sample_order_data):
        """Test order creation factory method."""
        order = Order.create(
            user_id=sample_order_data["user_id"],
            item_id=sample_order_data["item_id"],
            quantity=sample_order_data["quantity"],
            idempotency_key=sample_order_data["idempotency_key"],
        )

        assert order.user_id == sample_order_data["user_id"]
        assert order.item_id == sample_order_data["item_id"]
        assert order.quantity == sample_order_data["quantity"]
        assert order.status == OrderStatus.NEW
        assert order.idempotency_key == sample_order_data["idempotency_key"]
        assert order.id is not None
        assert order.created_at is not None
        assert order.updated_at is not None

    def test_create_order_without_idempotency_key(self, sample_order_data):
        """Test order creation without idempotency key."""
        order = Order.create(
            user_id=sample_order_data["user_id"],
            item_id=sample_order_data["item_id"],
            quantity=sample_order_data["quantity"],
            idempotency_key=None,
        )

        assert order.idempotency_key is None

    def test_mark_paid(self, sample_order):
        """Test marking order as paid."""
        sample_order.mark_paid()

        assert sample_order.status == OrderStatus.PAID
        assert sample_order.updated_at is not None

    def test_mark_paid_from_wrong_status(self, sample_order):
        """Test marking order as paid from wrong status."""
        sample_order.mark_paid()  # First mark as paid
        sample_order.updated_at = None  # Reset for test

        with pytest.raises(DomainError, match="Cannot mark order"):
            sample_order.mark_paid()

    def test_mark_shipped(self, sample_order):
        """Test marking order as shipped."""
        sample_order.mark_paid()
        sample_order.mark_shipped()

        assert sample_order.status == OrderStatus.SHIPPED

    def test_mark_shipped_without_paid(self, sample_order):
        """Test marking order as shipped without paying."""
        with pytest.raises(DomainError, match="Cannot mark order"):
            sample_order.mark_shipped()

    def test_cancel(self, sample_order):
        """Test cancelling an order."""
        sample_order.cancel("Test reason")

        assert sample_order.status == OrderStatus.CANCELLED

    def test_cancel_shipped_order(self, sample_order):
        """Test cancelling a shipped order."""
        sample_order.mark_paid()
        sample_order.mark_shipped()

        with pytest.raises(DomainError, match="Cannot cancel order"):
            sample_order.cancel()
