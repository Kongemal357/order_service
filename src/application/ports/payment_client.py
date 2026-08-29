"""
Payment Service client port (interface).
"""

from abc import ABC, abstractmethod

from src.application.dto.payment_dto import CreatePaymentDTO, PaymentResponseDTO


class PaymentClient(ABC):
    """Port for Payment Service client operations."""

    @abstractmethod
    async def create_payment(self, dto: CreatePaymentDTO) -> PaymentResponseDTO:
        pass
