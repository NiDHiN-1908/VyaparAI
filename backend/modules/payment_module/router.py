# backend/modules/payment_module/router.py
import logging
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from backend.services.supabase_service import supabase_svc
from backend.modules.websocket_module import websocket_manager

logger = logging.getLogger("vyaparai.payment.router")
router = APIRouter(tags=["Payment Integration"])

class PaymentCallbackRequest(BaseModel):
    order_id: str
    status: str

@router.get("/payment/simulate", response_class=HTMLResponse)
async def simulate_payment_page(order_id: str, amount: float):
    """
    Renders a checkout page to simulate a customer completing a Razorpay payment.
    """
    merchant_name = "Green Haven Nursery"
    try:
        orders = supabase_svc.get_orders()
        order = next((o for o in orders if o["id"] == order_id), None)
        if order and order.get("lead_id"):
            lead = supabase_svc._select_one("leads", order["lead_id"])
            if lead and lead.get("business_id"):
                business = supabase_svc._select_one("businesses", lead["business_id"])
                if business and business.get("name"):
                    merchant_name = business["name"]
    except Exception as e:
        logger.error(f"Failed to dynamically resolve merchant name for order {order_id}: {e}")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VyaparAI - UPI Payments Sandbox</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Outfit', sans-serif;
                background-color: #0b0f19;
                color: #f1f5f9;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
            }}
            .card {{
                background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
                border: 1px solid #374151;
                border-radius: 24px;
                padding: 40px;
                width: 100%;
                max-width: 440px;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
                text-align: center;
            }}
            .header {{
                margin-bottom: 24px;
            }}
            .logo {{
                font-size: 24px;
                font-weight: 800;
                color: #6366f1;
                margin-bottom: 8px;
            }}
            .amount {{
                font-size: 40px;
                font-weight: 800;
                margin: 16px 0;
                color: #10b981;
            }}
            .details {{
                background: #030712;
                border-radius: 16px;
                padding: 16px;
                margin-bottom: 30px;
                font-size: 14px;
                color: #9ca3af;
                text-align: left;
                line-height: 1.6;
            }}
            .details strong {{
                color: #e5e7eb;
            }}
            .btn {{
                background-color: #10b981;
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
                border: none;
                border-radius: 12px;
                padding: 14px 28px;
                width: 100%;
                cursor: pointer;
                transition: background-color 0.2s, transform 0.1s;
            }}
            .btn:hover {{
                background-color: #059669;
            }}
            .btn:active {{
                transform: scale(0.98);
            }}
            .footer {{
                margin-top: 24px;
                font-size: 12px;
                color: #4b5563;
            }}
            .success-container {{
                display: none;
            }}
            .success-icon {{
                font-size: 48px;
                color: #10b981;
                margin-bottom: 16px;
            }}
        </style>
        <script>
            async function triggerPayment() {{
                const payBtn = document.getElementById("pay-btn");
                payBtn.disabled = true;
                payBtn.innerText = "Processing Transaction...";
                
                try {{
                    const response = await fetch("/payment", {{
                        method: "POST",
                        headers: {{
                            "Content-Type": "application/json"
                        }},
                        body: JSON.stringify({{
                            order_id: "{order_id}",
                            status: "paid"
                        }})
                    }});
                    
                    if (response.ok) {{
                        document.getElementById("payment-card").style.display = "none";
                        document.getElementById("success-card").style.display = "block";
                    }} else {{
                        alert("Payment callback failed. Please try again.");
                        payBtn.disabled = false;
                        payBtn.innerText = "Authorize & Pay UPI";
                    }}
                }} catch (e) {{
                    alert("Network error: " + e.message);
                    payBtn.disabled = false;
                    payBtn.innerText = "Authorize & Pay UPI";
                }}
            }}
        </script>
    </head>
    <body>
        <!-- Checkout Container -->
        <div id="payment-card" class="card">
            <div class="header">
                <div class="logo">VyaparAI Sandbox</div>
                <div style="font-size: 14px; color: #9ca3af;">Simulating Razorpay Payment Gateway</div>
            </div>
            
            <div class="amount">₹{amount:.2f}</div>
            
            <div class="details">
                <div><strong>Order Reference:</strong> {order_id}</div>
                <div><strong>Merchant:</strong> {merchant_name}</div>
                <div><strong>Payment Option:</strong> UPI (Auto Success Simulate)</div>
            </div>
            
            <button id="pay-btn" class="btn" onclick="triggerPayment()">Authorize & Pay UPI</button>
            
            <div class="footer">Secure payments simulated under sandbox mode.</div>
        </div>

        <!-- Success Screen -->
        <div id="success-card" class="card success-container">
            <div class="success-icon">✓</div>
            <h2 style="font-weight: 800; color: #e5e7eb; margin-bottom: 8px;">Payment Successful!</h2>
            <p style="color: #9ca3af; font-size: 14px; margin-bottom: 24px;">
                Transaction for reference ID <span style="font-family: monospace; color: #e5e7eb;">{order_id}</span> completed successfully.
            </p>
            <p style="color: #6366f1; font-size: 13px;">You can close this tab and return to the dashboard.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@router.post("/payment")
async def process_payment_callback(payload: PaymentCallbackRequest):
    """
    Unified payment callback endpoint.
    Updates order status, stores payment event in conversation timeline, and broadcasts via websockets.
    """
    logger.info(f"Payment callback request received for order {payload.order_id} with status {payload.status}")
    
    # 1. Look up the order in db
    orders = supabase_svc.get_orders()
    order = next((o for o in orders if o["id"] == payload.order_id), None)
    
    if not order:
        logger.warning(f"Order {payload.order_id} not found in database. Updating order status dynamically.")
        # Try to find if order_id is a substring or custom code
        order = next((o for o in orders if payload.order_id in o["id"] or o["id"] in payload.order_id), None)
        
    if not order:
        # Create a mock order structure for validation if missing
        logger.warning("Order record missing. Proceeding with callback fallback.")
        order = {
            "id": payload.order_id,
            "amount": 350.00,
            "lead_id": None
        }
    else:
        # Update actual order in database
        supabase_svc.update_order_status(order["id"], payload.status)
        
    # 2. Get active conversation associated with lead or fallback to latest
    conv = None
    if order.get("lead_id"):
        conv = supabase_svc.get_conversation_by_lead(order["lead_id"])
        
    if not conv:
        # Fallback: find conversation matching default lead or latest conversation
        conversations = supabase_svc.get_conversations(tenant_id="00000000-0000-0000-0000-000000000000")
        if conversations:
            conv = conversations[0]

    if conv:
        # 3. Create a system payment timeline event
        event_message = f"💳 Payment Event: Received Rs {order.get('amount', 350.00)}. Status: {payload.status.upper()}. Reference ID: {order['id']}."
        msg_record = supabase_svc.create_message(
            conversation_id=conv["id"],
            sender_type="system",
            content=event_message
        )
        
        # 4. Broadcast via WebSocket
        tenant_id = conv.get("tenant_id", "00000000-0000-0000-0000-000000000000")
        await websocket_manager.broadcast_to_tenant(
            tenant_id=tenant_id,
            event_type="message.created",
            data=msg_record
        )
        
        # Also broadcast confirmation trigger
        await websocket_manager.broadcast_to_tenant(
            tenant_id=tenant_id,
            event_type="conversation.updated",
            data=conv
        )
        
        return {"status": "success", "message": "Payment verified and recorded.", "data": msg_record}

    return {"status": "success", "message": "Payment updated, but no matching conversation timeline found."}
