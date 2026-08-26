import logging
from urllib.parse import urljoin
from uuid import UUID

import httpx

from src.domain.models import CatalogItem
from src.domain.exceptions import CatalogServiceError
from src.application.ports.catalog_client import CatalogClient as CatalogClientPort
from src.settings import settings

logger = logging.getLogger(__name__)


class CatalogHTTPClient(CatalogClientPort):
    """ HTTP client for Catalog Service. """

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or settings.CAPASHINO_BASE_URL
        self.api_key = api_key or settings.CAPASHINO_API_KEY
        self.timeout = 10.0

    async def get_item(self, item_id: UUID) -> CatalogItem:
        """ Fetch an item from Catalog Service."""

        url = urljoin(self.base_url, f"api/catalog/items/{item_id}")
        headers = {"X-API-Key": self.api_key}

        logger.debug(f"Fetching catalog item: {item_id}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                logger.debug(f"Catalog response: {data}")

                return CatalogItem(
                    id=UUID(data["id"]),
                    name=data["name"],
                    price=data["price"],
                    available_qty=data["available_qty"],
                    created_at=data["created_at"],
                )

        except httpx.TimeoutException as e:
            logger.error(f"Catalog Service timeout: {e}")
            raise CatalogServiceError(f"Catalog Service timeout: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Catalog Service HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 404:
                raise CatalogServiceError(f"Item {item_id} not found")
            raise CatalogServiceError(f"Catalog Service error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected error fetching catalog item: {e}")
            raise CatalogServiceError(f"Failed to fetch catalog item: {e}")