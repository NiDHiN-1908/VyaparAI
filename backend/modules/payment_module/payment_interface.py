# backend/modules/payment_module/payment_interface.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class PaymentServiceInterface(ABC):
    @abstractmethod
    async def create_payment_link(self, order_id: str, amount: float, description: str, customer_info: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a payment link and returns details including short_url."""
        pass

    @abstractmethod
    async def verify_payment(self, payload: Dict[str, Any], signature: str) -> bool:
        """Verifies if the webhook payment event is authentic."""
        pass
