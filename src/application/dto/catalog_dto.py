from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.models import CatalogItem


@dataclass(frozen=True)
class CatalogItemDTO:
    """DTO for catalog item data."""
    id: UUID
    name: str
    price: str
    available_qty: int
    created_at: datetime

    @classmethod
    def from_domain(cls, item: CatalogItem) -> "CatalogItemDTO":
        """Create DTO from Domain CatalogItem model."""
        return cls(
            id=item.id,
            name=item.name,
            price=item.price,
            available_qty=item.available_qty,
            created_at=item.created_at,
        )

    def to_domain(self) -> CatalogItem:
        """Convert DTO back to Domain CatalogItem model."""
        return CatalogItem(
            id=self.id,
            name=self.name,
            price=self.price,
            available_qty=self.available_qty,
            created_at=self.created_at,
        )