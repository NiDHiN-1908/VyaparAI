# backend/modules/payment_module/razorpay_service.py
import os
import logging
import httpx
from typing import Dict, Any
from .payment_interface import PaymentServiceInterface

logger = logging.getLogger("vyaparai.payment.razorpay")

class RazorpayPaymentService(PaymentServiceInterface):
    def __init__(self):
        self.key_id = os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        self.is_sandbox = not (self.key_id and self.key_secret)

        if self.is_sandbox:
            logger.warning("Razorpay credentials not found in env. Running in payment sandbox simulation mode.")

    async def create_payment_link(self, order_id: str, amount: float, description: str, customer_info: Dict[str, Any]) -> Dict[str, Any]:
        # Convert amount to paise (1 INR = 100 paise) for Razorpay
        amount_paise = int(amount * 100)
        
        # Determine the host URL from settings/env or fallback to localhost
        host_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
        
        if self.is_sandbox:
            # Simulate a payment link url pointing to our simulation page
            simulated_url = f"{host_url}/payment/simulate?order_id={order_id}&amount={amount}"
            logger.info(f"[PAYMENT SIMULATOR] Generated payment link for Order {order_id}: {simulated_url}")
            return {
                "id": f"plink_{order_id}",
                "status": "created",
                "short_url": simulated_url,
                "amount": amount,
                "currency": "INR"
            }

        # Real Razorpay API integration
        url = "https://api.razorpay.com/v1/payment_links"
        auth = (self.key_id, self.key_secret)
        headers = {"Content-Type": "application/json"}
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "accept_partial": False,
            "reference_id": order_id,
            "description": description,
            "customer": {
                "name": customer_info.get("name", "Customer"),
                "contact": customer_info.get("contact", ""),
                "email": customer_info.get("email", "")
            },
            "notify": {
                "sms": False,
                "email": False
            },
            "reminder_enable": False,
            "callback_url": f"{host_url}/payment/callback",
            "callback_method": "get"
        }

        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(url, auth=auth, headers=headers, json=payload, timeout=10.0)
                res_data = res.json()
                if res.status_code in [200, 201]:
                    return {
                        "id": res_data.get("id"),
                        "status": res_data.get("status"),
                        "short_url": res_data.get("short_url"),
                        "amount": amount,
                        "currency": "INR"
                    }
                else:
                    logger.error(f"Razorpay API error: {res_data}")
                    raise Exception(f"Razorpay API error: {res_data.get('error', {}).get('description')}")
            except Exception as e:
                logger.error(f"Network error calling Razorpay API: {e}. Falling back to simulation mode.")
                simulated_url = f"{host_url}/payment/simulate?order_id={order_id}&amount={amount}"
                return {
                    "id": f"plink_fallback_{order_id}",
                    "status": "created",
                    "short_url": simulated_url,
                    "amount": amount,
                    "currency": "INR"
                }

    async def verify_payment(self, payload: Dict[str, Any], signature: str) -> bool:
        if self.is_sandbox:
            # In sandbox/simulation, we verify if signature is "sandbox_signature"
            return signature == "sandbox_signature"
            
        # For real Razorpay webhook signature verification
        import hmac
        import hashlib
        webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
        if not webhook_secret:
            logger.warning("RAZORPAY_WEBHOOK_SECRET is not configured. Webhook signature verification will fail.")
            return False
            
        try:
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                msg=payload,
                digestmod=hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Failed to verify signature: {e}")
            return False
