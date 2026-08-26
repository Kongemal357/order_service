from abc import ABC, abstractmethod
from uuid import UUID

from src.application.dto.catalog_dto import CatalogItemDTO


class CatalogClient(ABC):
    """Port for Catalog Service client operations."""

    @abstractmethod
    async def get_item(self, item_id: UUID) -> CatalogItemDTO:
        pass