import logging
from uuid import UUID

from sqlalchemy import select, text

from fastapi import APIRouter, Depends
from src.application.ports.uow import UnitOfWorkFactory
from src.infrastructure.persistence.models import OutboxModel
from src.presentation.api.dependencies import get_uow_factory

logger = logging.getLogger(__name__)

debug_router = APIRouter(prefix="/debug", tags=["debug"])


@debug_router.get("/outbox")
async def debug_outbox(
    limit: int = 20,
    uow_factory: UnitOfWorkFactory = Depends(get_uow_factory),
) -> dict:
    """
    Диагностика: просмотр последних записей в outbox.
    """
    async with uow_factory() as uow:
        # Получаем последние записи из outbox
        stmt = select(OutboxModel).order_by(OutboxModel.created_at.desc()).limit(limit)
        result = await uow._session.execute(stmt)
        rows = result.scalars().all()

        return {
            "count": len(rows),
            "rows": [
                {
                    "id": str(row.id),
                    "event_type": row.event_type,
                    "status": row.status,
                    "idempotency_key": row.idempotency_key,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "sent_at": row.sent_at.isoformat() if row.sent_at else None,
                }
                for row in rows
            ],
        }


@debug_router.get("/outbox/pending")
async def debug_outbox_pending(
    uow_factory: UnitOfWorkFactory = Depends(get_uow_factory),
) -> dict:
    """
    Диагностика: просмотр pending событий в outbox.
    """
    async with uow_factory() as uow:
        stmt = (
            select(OutboxModel)
            .where(OutboxModel.status == "pending")
            .order_by(OutboxModel.created_at)
        )
        result = await uow._session.execute(stmt)
        rows = result.scalars().all()

        return {
            "count": len(rows),
            "rows": [
                {
                    "id": str(row.id),
                    "event_type": row.event_type,
                    "status": row.status,
                    "idempotency_key": row.idempotency_key,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ],
        }


@debug_router.get("/outbox/failed")
async def debug_outbox_failed(
    uow_factory: UnitOfWorkFactory = Depends(get_uow_factory),
) -> dict:
    """
    Диагностика: просмотр failed событий в outbox.
    """
    async with uow_factory() as uow:
        stmt = (
            select(OutboxModel)
            .where(OutboxModel.status == "failed")
            .order_by(OutboxModel.created_at.desc())
        )
        result = await uow._session.execute(stmt)
        rows = result.scalars().all()

        return {
            "count": len(rows),
            "rows": [
                {
                    "id": str(row.id),
                    "event_type": row.event_type,
                    "status": row.status,
                    "idempotency_key": row.idempotency_key,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ],
        }


@debug_router.get("/order/{order_id}")
async def debug_order(
    order_id: UUID,
    uow_factory: UnitOfWorkFactory = Depends(get_uow_factory),
) -> dict:
    """
    Диагностика: просмотр заказа по ID.
    """
    async with uow_factory() as uow:
        order = await uow.order_repo.get_by_id(order_id)
        if not order:
            return {"error": f"Order {order_id} not found"}

        return {
            "id": str(order.id),
            "user_id": order.user_id,
            "item_id": str(order.item_id),
            "quantity": order.quantity,
            "status": order.status.value,
            "payment_id": str(order.payment_id) if order.payment_id else None,
            "idempotency_key": order.idempotency_key,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        }


@debug_router.get("/inbox")
async def debug_inbox(
    limit: int = 20,
    uow_factory: UnitOfWorkFactory = Depends(get_uow_factory),
) -> dict:
    """
    Диагностика: просмотр последних записей в inbox.
    """
    async with uow_factory() as uow:
        result = await uow._session.execute(
            text(
                "SELECT id, event_id, idempotency_key, event_type, processed_at "
                "FROM inbox ORDER BY processed_at DESC LIMIT :limit"
            ),
            {"limit": limit},
        )
        rows = result.fetchall()

        return {
            "count": len(rows),
            "rows": [
                {
                    "id": str(row[0]),
                    "event_id": row[1],
                    "idempotency_key": row[2],
                    "event_type": row[3],
                    "processed_at": row[4].isoformat() if row[4] else None,
                }
                for row in rows
            ],
        }
