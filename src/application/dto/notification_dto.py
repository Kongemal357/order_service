from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SendNotificationDTO:
    """DTO for sending a notification."""

    user_id: str
    message: str
    reference_id: UUID
    idempotency_key: str
