from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.models import EventType, InboxRecord, InboxStatus


@dataclass(frozen=True)
class InboxWithUserDTO:
    """DTO for inbox record with user_id from joined order."""

    id: UUID
    event_id: str
    event_type: EventType
    payload: dict[str, Any]
    status: InboxStatus
    user_id: str
    processed_at: datetime | None = None
    created_at: datetime | None = None

    @classmethod
    def from_model(
        cls,
        inbox_model: "InboxRecord",
        user_id: str,
    ) -> "InboxWithUserDTO":
        """Create DTO from SQLAlchemy model and user_id."""
        return cls(
            id=inbox_model.id,
            event_id=inbox_model.event_id,
            event_type=EventType(inbox_model.event_type),
            payload=inbox_model.payload,
            status=InboxStatus(inbox_model.status),
            user_id=user_id,
            processed_at=inbox_model.processed_at,
            created_at=inbox_model.created_at,
        )
