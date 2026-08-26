from typing import AsyncGenerator

from fastapi import Depends

from src.application.ports import UnitOfWork, CatalogClient
from src.application.usecases import CreateOrderUseCase, GetOrderUseCase
from src.infrastructure.http.catalog_client import CatalogHTTPClient
from src.infrastructure.persistence.uow import SQLAlchemyUnitOfWork


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """Dependency for Unit of Work."""
    async with SQLAlchemyUnitOfWork() as uow:
        yield uow


def get_catalog_client() -> CatalogClient:
    """Dependency for Catalog Service client."""
    return CatalogHTTPClient()


async def get_create_order_use_case(
    uow: UnitOfWork = Depends(get_uow),
    catalog_client: CatalogClient = Depends(get_catalog_client),
) -> CreateOrderUseCase:
    """Dependency for create order use case."""
    return CreateOrderUseCase(uow, catalog_client)


async def get_get_order_use_case(
    uow: UnitOfWork = Depends(get_uow),
) -> GetOrderUseCase:
    """Dependency for get order use case."""
    return GetOrderUseCase(uow)