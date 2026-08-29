from typing import AsyncGenerator

from fastapi import Depends
from src.application.ports import CatalogClient, UnitOfWork
from src.application.ports.payment_client import PaymentClient
from src.application.usecases import CreateOrderUseCase, GetOrderUseCase
from src.application.usecases.process_payment_callback import ProcessPaymentCallbackUseCase
from src.infrastructure.http.catalog_client import CatalogHTTPClient
from src.infrastructure.http.payment_client import PaymentHTTPClient
from src.infrastructure.persistence.uow import SQLAlchemyUnitOfWork


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """Dependency for Unit of Work."""
    async with SQLAlchemyUnitOfWork() as uow:
        yield uow


def get_catalog_client() -> CatalogClient:
    """Dependency for Catalog Service client."""
    return CatalogHTTPClient()


def get_payment_client() -> PaymentClient:
    """Dependency for Payment Service client."""
    return PaymentHTTPClient()


async def get_create_order_use_case(
    uow: UnitOfWork = Depends(get_uow),
    catalog_client: CatalogClient = Depends(get_catalog_client),
    payment_client: PaymentClient = Depends(get_payment_client),
) -> CreateOrderUseCase:
    """Dependency for create order use case."""
    return CreateOrderUseCase(uow, catalog_client, payment_client)


async def get_get_order_use_case(
    uow: UnitOfWork = Depends(get_uow),
) -> GetOrderUseCase:
    """Dependency for get order use case."""
    return GetOrderUseCase(uow)


async def get_process_payment_callback_use_case(
    uow: UnitOfWork = Depends(get_uow),
) -> ProcessPaymentCallbackUseCase:
    """Dependency for process payment callback use case."""
    return ProcessPaymentCallbackUseCase(uow)
