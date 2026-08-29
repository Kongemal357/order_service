class DomainError(Exception):
    """Base domain exception."""

    pass


class InsufficientStockError(DomainError):
    """Raised when requested quantity exceeds available stock."""

    pass


class OrderNotFoundError(DomainError):
    """Raised when an order is not found."""

    pass


class OrderAlreadyExistsError(DomainError):
    """Raised when an order with the same idempotency key already exists."""

    pass


class CatalogServiceError(DomainError):
    """Raised when Catalog Service returns an error."""

    pass


class PaymentError(DomainError):
    """Raised when Payment Service returns an error."""

    pass


class PaymentAlreadyProcessedError(DomainError):
    """Raised when a payment callback is received multiple times."""

    pass
