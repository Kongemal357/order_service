import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from src.application.usecases import CreateOrderUseCase, GetOrderUseCase
from src.application.usecases.process_payment_callback import ProcessPaymentCallbackUseCase
from src.domain.exceptions import (
    CatalogServiceError,
    InsufficientStockError,
    OrderAlreadyExistsError,
    OrderNotFoundError,
)
from src.presentation.api.dependencies import (
    get_create_order_use_case,
    get_get_order_use_case,
    get_process_payment_callback_use_case,
)
from src.presentation.api.schemas import (
    CreateOrderRequest,
    ErrorResponse,
    OrderResponse,
    PaymentCallbackRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        409: {"model": ErrorResponse, "description": "Idempotency conflict"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
)
async def create_order(
    request: CreateOrderRequest,
    use_case: CreateOrderUseCase = Depends(get_create_order_use_case),
) -> OrderResponse:
    """Create a new order."""
    logger.info(f"Received create order request: {request}")

    try:
        result_dto = await use_case.execute(request.to_dto())

        return result_dto

    except InsufficientStockError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OrderAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except CatalogServiceError:
        raise HTTPException(status_code=503, detail="Catalog Service unavailable")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_order(
    order_id: UUID,
    use_case: GetOrderUseCase = Depends(get_get_order_use_case),
) -> OrderResponse:
    """Get an order by ID."""
    logger.info(f"Received get order request: {order_id}")

    try:
        result_dto = await use_case.execute(order_id)

        return result_dto

    except OrderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/payment-callback", status_code=status.HTTP_200_OK)
async def payment_callback(
    request: PaymentCallbackRequest,
    use_case: ProcessPaymentCallbackUseCase = Depends(get_process_payment_callback_use_case),
) -> dict:
    """Handle payment callback from Payment Service."""
    logger.info(f"Received payment callback: order={request.order_id}, status={request.status}")

    try:
        result = await use_case.execute(request.to_dto())

        return {
            "status": "ok",
            "order_id": str(result.id),
            "order_status": result.status.value,
        }

    except OrderNotFoundError as e:
        logger.warning(f"Order not found: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"Error processing payment callback: {e}")
        return {"status": "error", "message": "Internal server error"}
