# backend/routers/whatsapp.py
import os
import uuid
import logging
import asyncio
import httpx

# Ensure standard Windows system directories are in the PATH (Requirement 7 & 11)
if os.name == 'nt':
    sys_paths = [
        r"C:\Windows\System32",
        r"C:\Windows",
        r"C:\Windows\System32\Wbem",
        r"C:\Windows\System32\WindowsPowerShell\v1.0"
    ]
    current_path = os.environ.get("PATH", "")
    for p in sys_paths:
        if p.lower() not in current_path.lower():
            current_path = p + os.pathsep + current_path
    os.environ["PATH"] = current_path
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.services.supabase_service import supabase_svc
from backend.agents.content_agent import get_ollama_llm
from backend.langgraph.sales_workflow import run_sales_chat

logger = logging.getLogger("vyaparai.routers.whatsapp")
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Chat & Webhooks"])

class SendMessageRequest(BaseModel):
    lead_id: str = Field(..., example="lead_uuid_here")
    message: str = Field(..., example="Hi, we saw your comment on YouTube. How can we help you order?")
    sender: Optional[str] = Field("business", description="business, customer, or ai")
    product_id: Optional[str] = Field(None, example="prod_fig")
    recipient_phone: Optional[str] = Field(None, example="919744506034")

class ToggleAutopilotRequest(BaseModel):
    lead_id: str = Field(..., example="lead_uuid_here")
    autopilot: bool = Field(..., example=True)

class WebhookConfigOverrideRequest(BaseModel):
    instance_id: str
    webhook_url: str

class WebhookValidateRequest(BaseModel):
    webhook_url: str

# In-Memory map to store phone-number-to-lead-id mappings dynamically for session tracking
PHONE_LEAD_MAP: Dict[str, str] = {}

async def simulate_customer_reply(lead_id: str, last_business_message: str):
    """Sandbox simulation: wait a moment, then generate a contextual reply using the LLM"""
    await asyncio.sleep(2)
    try:
        # Resolve lead details for context
        leads = supabase_svc.get_youtube_leads()
        lead = next((l for l in leads if l["id"] == lead_id), None)
        username = lead["username"] if lead else "customer"
        query_context = lead["reply"] if lead else "inquiring about Fiddle Leaf Fig price"

        # Generate response using LLM
        llm = get_ollama_llm()
        prompt = (
            f"You are a customer named @{username} chatting on WhatsApp with Green Haven Nursery. "
            f"You previously left a YouTube comment expressing high purchase intent: '{query_context}'.\n"
            f"The business owner just sent you this WhatsApp message: '{last_business_message}'.\n"
            f"Respond naturally as the customer. Keep your reply friendly, realistic, and to the point (maximum 1 or 2 short sentences)."
        )
        res = await llm.ainvoke(prompt)
        reply_text = res.content.strip().strip('"')
        
        # Save simulated reply in DB
        supabase_svc.create_whatsapp_message(
            lead_id=lead_id,
            sender="customer",
            text=reply_text
        )
        logger.info(f"[SANDBOX WHATSAPP] Generated simulated customer reply for lead {lead_id}: '{reply_text}'")
    except Exception as e:
        logger.error(f"Failed to generate simulated customer reply: {e}")
        # Standard fallback response
        supabase_svc.create_whatsapp_message(
            lead_id=lead_id,
            sender="customer",
            text="Sounds great! Yes, I want to order a Fiddle Leaf Fig plant. Where can I pay?"
        )

@router.post("/send")
async def send_whatsapp_message(payload: SendMessageRequest):
    """Sends a message in the unified feed (routes to LangGraph if sender is 'customer', otherwise sends via WhatsApp API)"""
    logger.info(f"Processing message send for lead {payload.lead_id} (sender: {payload.sender})")
    
    # 1. AI SALES AGENT SIMULATION (Autopilot ON roleplay)
    if payload.sender == "customer":
        # Save customer message in DB
        cust_msg = supabase_svc.create_whatsapp_message(
            lead_id=payload.lead_id,
            sender="customer",
            text=payload.message
        )
        
        # Determine product to sell
        prod_id = payload.product_id
        if not prod_id:
            products = supabase_svc.get_products()
            prod_id = products[0]["id"] if products else "prod_fig"
            
        try:
            # Execute LangGraph Sales Chat
            chat_res = run_sales_chat(
                lead_id=payload.lead_id,
                product_id=prod_id,
                user_message=payload.message
            )
            ai_reply_text = chat_res["response"]
            next_state = chat_res["next_state"]
        except Exception as e:
            logger.error(f"LangGraph execution failed: {e}")
            ai_reply_text = "Thank you for your interest! Let me check the specifications for you."
            next_state = "QA_LOOP"
            
        # Save AI message in DB
        ai_msg = supabase_svc.create_whatsapp_message(
            lead_id=payload.lead_id,
            sender="ai",
            text=ai_reply_text
        )
        
        return {
            "status": "success",
            "mode": "ai_agent",
            "customer_msg": cust_msg,
            "ai_msg": ai_msg,
            "state": next_state
        }
        
    # 2. MANUAL OUTREACH / TAKE OVER (Autopilot OFF)
    # Save the outgoing message in our DB
    msg_rec = supabase_svc.create_whatsapp_message(
        lead_id=payload.lead_id,
        sender="business",
        text=payload.message
    )

    # Check for WhatsApp Business API configuration
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    if access_token and phone_number_id:
        recipient = payload.recipient_phone
        if not recipient:
            reversed_map = {v: k for k, v in PHONE_LEAD_MAP.items()}
            recipient = reversed_map.get(payload.lead_id)
        
        if not recipient:
            businesses = supabase_svc.get_businesses()
            recipient = "919744506034"
            if businesses and businesses[0].get("contact"):
                import re
                cleaned = re.sub(r'\D', '', businesses[0]["contact"])
                if cleaned:
                    recipient = cleaned

        logger.info(f"[WHATSAPP CLOUD API] Sending manual message to {recipient} via official Meta API...")
        try:
            async with httpx.AsyncClient() as client:
                url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                body = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": recipient,
                    "type": "text",
                    "text": {
                        "preview_url": False,
                        "body": payload.message
                    }
                }
                res = await client.post(url, headers=headers, json=body, timeout=10.0)
                res_data = res.json()
                if res.status_code == 200:
                    logger.info("[WHATSAPP CLOUD API] Message successfully sent via Meta!")
                    return {
                        "status": "success",
                        "mode": "production",
                        "data": msg_rec,
                        "meta_response": res_data
                    }
                else:
                    logger.error(f"[WHATSAPP CLOUD API] Meta API returned error: {res_data}")
        except Exception as e:
            logger.error(f"[WHATSAPP CLOUD API] Network error calling Meta API: {e}")

    # Fallback / Sandbox Simulation Mode
    logger.info("[SANDBOX WHATSAPP] Running in Sandbox mode. Triggering LLM customer response...")
    asyncio.create_task(simulate_customer_reply(payload.lead_id, payload.message))
    
    return {
        "status": "success",
        "mode": "sandbox",
        "data": msg_rec
    }

@router.post("/toggle-autopilot")
async def toggle_autopilot(payload: ToggleAutopilotRequest):
    """Toggles autopilot for a lead in the database"""
    logger.info(f"Toggling autopilot for lead {payload.lead_id} to {payload.autopilot}")
    try:
        updated = supabase_svc.update_youtube_lead_autopilot(payload.lead_id, payload.autopilot)
        if not updated:
            raise HTTPException(status_code=404, detail="Lead not found")
        return {"status": "success", "data": updated}
    except Exception as e:
        logger.error(f"Failed to toggle autopilot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{lead_id}")
async def get_whatsapp_history(lead_id: str):
    """Retrieves chat history for a specific lead"""
    logger.info(f"Fetching chat history for lead: {lead_id}")
    try:
        messages = supabase_svc.get_whatsapp_messages(lead_id)
        return {"status": "success", "data": messages}
    except Exception as e:
        logger.error(f"Failed to fetch chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: int = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """Meta webhook verification endpoint"""
    logger.info("WhatsApp webhook verification request received.")
    local_verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "vyaparai_verify_token_secret")
    
    if hub_mode == "subscribe" and hub_verify_token == local_verify_token:
        logger.info("Webhook verification succeeded.")
        from fastapi.responses import Response
        return Response(content=str(hub_challenge), media_type="text/plain")
    else:
        logger.warning("Webhook verification failed. Invalid token.")
        raise HTTPException(status_code=403, detail="Verification token mismatch")

@router.post("/webhook")
async def process_webhook(request: Request):
    """Webhook to receive real-time messages from WhatsApp users"""
    payload = await request.json()
    logger.info(f"Inbound webhook received from Meta: {payload}")

    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    try:
        entry = payload.get("entry", [])
        if not entry:
            return {"status": "ignored"}
            
        changes = entry[0].get("changes", [])
        if not changes:
            return {"status": "ignored"}

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        
        if messages:
            msg = messages[0]
            from_phone = msg.get("from") # E.g. "917306796590"
            text_body = msg.get("text", {}).get("body")
            
            if from_phone and text_body:
                logger.info(f"Incoming message from +{from_phone}: '{text_body}'")
                
                # Check if this phone number is mapped to a lead_id
                lead_id = PHONE_LEAD_MAP.get(from_phone)
                if not lead_id:
                    # Resolve lead ID from active leads list matching latest active conversation
                    leads = supabase_svc.get_youtube_leads()
                    if leads:
                        # Fallback: map to the most recent lead
                        lead_id = leads[0]["id"]
                        PHONE_LEAD_MAP[from_phone] = lead_id
                
                if lead_id:
                    # Save incoming customer message in database
                    supabase_svc.create_whatsapp_message(
                        lead_id=lead_id,
                        sender="customer",
                        text=text_body
                    )
                    
                    # Check if Autopilot is enabled for this lead
                    leads = supabase_svc.get_youtube_leads()
                    lead = next((l for l in leads if l["id"] == lead_id), None)
                    is_autopilot = lead.get("autopilot", True) if lead else True
                    
                    if is_autopilot:
                        # Auto-respond using LangGraph sales agent!
                        products = supabase_svc.get_products()
                        product_id = products[0]["id"] if products else "prod_fig"
                        
                        chat_res = run_sales_chat(
                            lead_id=lead_id,
                            product_id=product_id,
                            user_message=text_body
                        )
                        
                        ai_reply = chat_res["response"]
                        # Save AI reply
                        supabase_svc.create_whatsapp_message(
                            lead_id=lead_id,
                            sender="ai",
                            text=ai_reply
                        )
                        
                        # If live mode, push the AI's reply back to the user's WhatsApp
                        if access_token and phone_number_id:
                            logger.info(f"[WHATSAPP CLOUD API] Pushing autopilot response to customer {from_phone}...")
                            async with httpx.AsyncClient() as client:
                                url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
                                headers = {
                                    "Authorization": f"Bearer {access_token}",
                                    "Content-Type": "application/json"
                                }
                                body = {
                                    "messaging_product": "whatsapp",
                                    "recipient_type": "individual",
                                    "to": from_phone,
                                    "type": "text",
                                    "text": {
                                        "preview_url": False,
                                        "body": ai_reply
                                    }
                                }
                                await client.post(url, headers=headers, json=body, timeout=10.0)
                    
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error parsing incoming Meta webhook: {e}")
        return {"status": "error", "detail": str(e)}

@router.get("/webhook-config")
async def get_webhook_config(tenant_id: str = "00000000-0000-0000-0000-000000000000"):
    """
    Retrieves, validates, and automatically synchronizes the webhook URL 
    associated with the connected WhatsApp account using the current ngrok endpoint.
    """
    logger.info(f"Retrieving webhook configuration for tenant {tenant_id}")
    
    # 1. Fetch connected/connecting WhatsApp instances for this tenant
    instances = supabase_svc.get_whatsapp_instances(tenant_id)
    if not instances:
        return {
            "status": "error",
            "message": "No WhatsApp account connected. Please connect a WhatsApp account first.",
            "connected": False
        }
        
    # Get the active connected/connecting instance (prefer connected)
    active_instance = next((i for i in instances if i.get("status") == "connected"), None)
    if not active_instance:
        active_instance = next((i for i in instances if i.get("status") == "connecting"), None)
        
    if not active_instance:
        return {
            "status": "error",
            "message": "No active WhatsApp account connected. Please check connection status.",
            "connected": False
        }
        
    instance_id = active_instance["id"]
    instance_name = active_instance["instance_name"]
    
    # 2. Automatically check if a local ngrok daemon is running and get the active tunnel URL (Requirement 4 & 5)
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    from backend.services.connectivity_service import connectivity_svc
    active_ngrok_url = await connectivity_svc.get_active_ngrok_url()
    
    from backend.config import settings
    if active_ngrok_url:
        logger.info(f"Dynamically detected active ngrok URL: {active_ngrok_url}. Overriding PUBLIC_URL.")
        settings.PUBLIC_URL = active_ngrok_url
    else:
        settings.PUBLIC_URL = os.getenv("PUBLIC_URL")
        
    public_url = settings.PUBLIC_URL or os.getenv("PUBLIC_URL") or os.getenv("APP_BASE_URL") or "http://localhost:8000"
    suggested_webhook_url = f"{public_url.rstrip('/')}/webhooks/whatsapp"
    
    # 3. Retrieve stored webhook URL from DB
    session_data = active_instance.get("session_data") or {}
    stored_webhook_url = session_data.get("webhook_url")
    
    is_synchronized = True
    # 4. Check if webhook URL is missing or out of sync (Requirement 8)
    if not stored_webhook_url or (stored_webhook_url != suggested_webhook_url and not session_data.get("webhook_override")):
        logger.info(f"Out of sync or missing webhook URL detected. Synchronizing to new PUBLIC_URL: {suggested_webhook_url}")
        try:
            # Re-register with the provider
            from backend.modules.whatsapp_module.instance_service import whatsapp_instance_svc
            app_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
            provider_webhook = f"{app_url.rstrip('/')}/webhooks/whatsapp?instance={instance_name}"
            await whatsapp_instance_svc.provider.register_webhook(instance_name, provider_webhook)
            
            # Save the new public webhook URL in the database
            supabase_svc.update_whatsapp_instance_webhook(instance_id, suggested_webhook_url)
            stored_webhook_url = suggested_webhook_url
        except Exception as e:
            logger.error(f"Failed to automatically synchronize webhook URL: {e}")
            is_synchronized = False
            
    is_override = bool(session_data.get("webhook_override"))
    
    return {
        "status": "success",
        "connected": True,
        "instance_id": instance_id,
        "instance_name": instance_name,
        "suggested_webhook_url": suggested_webhook_url,
        "stored_webhook_url": stored_webhook_url or suggested_webhook_url,
        "is_synchronized": is_synchronized,
        "is_override": is_override,
        "active_tunnel_url": public_url
    }

@router.post("/webhook-config")
async def save_webhook_config(payload: WebhookConfigOverrideRequest):
    """
    Saves an overridden custom webhook URL for a specific WhatsApp instance 
    and registers it with the active WhatsApp provider.
    """
    logger.info(f"Saving custom webhook override for instance {payload.instance_id}: {payload.webhook_url}")
    
    instance = supabase_svc.get_whatsapp_instance(payload.instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="WhatsApp instance not found")
        
    instance_name = instance["instance_name"]
    
    try:
        session_data = instance.get("session_data") or {}
        if not isinstance(session_data, dict):
            session_data = {}
        session_data["webhook_url"] = payload.webhook_url
        session_data["webhook_override"] = True
        
        supabase_svc._update("whatsapp_instances", instance["id"], {"session_data": session_data})
    except Exception as e:
        logger.error(f"Failed to save webhook configuration in DB: {e}")
        raise HTTPException(status_code=500, detail="Database write failure")
        
    try:
        from backend.modules.whatsapp_module.instance_service import whatsapp_instance_svc
        await whatsapp_instance_svc.provider.register_webhook(instance_name, payload.webhook_url)
    except Exception as e:
        logger.error(f"Failed to register custom webhook with provider: {e}")
        
    return {"status": "success", "message": "Webhook URL overridden and registered successfully."}

@router.post("/validate-webhook")
async def validate_webhook(payload: WebhookValidateRequest):
    """
    Validates the reachability of a webhook endpoint by performing a GET verification pre-check,
    followed by a POST ping test.
    """
    logger.info(f"Validating webhook reachability for: {payload.webhook_url}")
    
    from backend.services.connectivity_service import connectivity_svc
    
    webhook_url = payload.webhook_url
    local_verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "vyaparai_verify_token_secret")
    
    # 0. Pre-validation Health Check: Check if local backend is active (Requirement 2 & 9)
    port = int(os.getenv("PORT", 8000))
    local_backend_active = False
    try:
        async with httpx.AsyncClient() as client:
            res_local = await client.get(f"http://127.0.0.1:{port}/health", timeout=1.0)
            if res_local.status_code == 200:
                local_backend_active = True
    except Exception:
        pass
        
    if not local_backend_active:
        return {
            "status": "error",
            "reachable": False,
            "validated_url": webhook_url,
            "message": (
                f"Validation Blocked: Local backend server on http://localhost:{port} is offline or not responding. "
                "You must start your backend before validating the public webhook."
            ),
            "recovery_suggestions": [
                "Start backend server (run start_all.bat)",
                f"Verify uvicorn processes are listening on port {port}",
                "Check uvicorn logs for errors or startup crashes"
            ]
        }

    # 1. Perform GET verification health check (Requirement 4 & 5)
    challenge = "test_challenge_12345"
    test_url = (
        f"{webhook_url}"
        f"{'&' if '?' in webhook_url else '?'}"
        f"hub.mode=subscribe&hub.challenge={challenge}&hub.verify_token={local_verify_token}"
    )
    
    logger.info(f"[HEALTH CHECK GET] Pinging GET verification on: {test_url}")
    
    try:
        res_get = await connectivity_svc.request_with_retry(
            method="GET",
            url=test_url,
            timeout=4.0,
            retries=2,
            backoff_factor=1.5
        )
        
        # Intercept HTTP 503 (Service Unavailable) - Requirement 7
        if res_get.status_code == 503:
            return {
                "status": "error",
                "reachable": False,
                "validated_url": webhook_url,
                "message": (
                    "Validation Failed: Service Unavailable (503). Your public tunnel is online, "
                    "but it is unable to connect to your local backend server on port 8000."
                ),
                "recovery_suggestions": [
                    "Restart the public tunnel (run start_all.bat again)",
                    "Verify local port mapping in start_tunnel.py points to port 8000",
                    "Check Windows Firewall or antivirus proxy configurations that might block local SSH port forwarding connections"
                ]
            }
        elif res_get.status_code == 404:
            return {
                "status": "error",
                "reachable": False,
                "validated_url": webhook_url,
                "message": (
                    "Validation Failed: Route not found (404). The path '/webhooks/whatsapp' was not found on the server. "
                    "Ensure your proxy, router, or gateway forwards requests correctly without stripping the path."
                ),
                "recovery_suggestions": [
                    "Refresh tunnel URL in the dashboard to make sure it is not expired",
                    "Verify that the GET /webhooks/whatsapp endpoint is declared in messaging_module/router.py",
                    "Confirm the prefix routes are correctly loaded in main.py without collisions"
                ]
            }
        elif res_get.status_code == 403:
            return {
                "status": "error",
                "reachable": False,
                "validated_url": webhook_url,
                "message": (
                    "Validation Failed: Invalid verify token (403). The server rejected the verify token. "
                    "Make sure the WHATSAPP_VERIFY_TOKEN configured in your backend .env matches."
                ),
                "recovery_suggestions": [
                    "Verify the WHATSAPP_VERIFY_TOKEN matches in the environment variables",
                    "Check if the token has special characters or trailing whitespaces in the config"
                ]
            }
        elif res_get.status_code == 200:
            body_text = res_get.text.strip()
            if body_text != challenge:
                return {
                    "status": "warning",
                    "reachable": False,
                    "validated_url": webhook_url,
                    "message": (
                        f"Validation Warning: GET check returned status 200, but challenge did not match. "
                        f"Expected '{challenge}', got '{body_text}'."
                    ),
                    "recovery_suggestions": [
                        "Ensure your local route handles GET requests and responds exactly with the hub.challenge query parameter",
                        "Verify there are no middleware intercepts modifying the response body"
                    ]
                }
            logger.info("[HEALTH CHECK GET] Webhook GET verification succeeded. Proceeding to POST check.")
        else:
            return {
                "status": "warning",
                "reachable": False,
                "validated_url": webhook_url,
                "message": f"Validation Warning: GET health check returned unexpected status code {res_get.status_code}.",
                "recovery_suggestions": [
                    "Inspect the tunnel or proxy logs to see what returned the status code",
                    "Refresh your tunnel URL and check connectivity again"
                ]
            }
            
    except (httpx.TimeoutException, httpx.ConnectError, Exception) as err:
        logger.warning(f"GET health check connection failed: {err}")
        return {
            "status": "error",
            "reachable": False,
            "validated_url": webhook_url,
            "message": (
                f"Validation Failed: Tunnel connection offline. The public URL '{webhook_url}' is unreachable."
            ),
            "recovery_suggestions": [
                "Restart tunnel (run start_all.bat to start tunnel again)",
                "Refresh tunnel URL in the dashboard to update outdated configuration links",
                "Verify your machine is connected to the internet and can reach public gateway sites"
            ]
        }

    # 2. Perform POST ping validation (Requirement 9 & 8)
    ping_payload = {
        "event": "ping",
        "instance": "validation_test",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        res_post = await connectivity_svc.request_with_retry(
            method="POST",
            url=webhook_url,
            json=ping_payload,
            timeout=4.0,
            retries=3,
            backoff_factor=1.5
        )
        
        if res_post.status_code == 200:
            res_data = res_post.json()
            if res_data.get("status") == "success" and res_data.get("message") == "pong":
                return {
                    "status": "success",
                    "reachable": True,
                    "validated_url": webhook_url,
                    "message": "Connection Successful! The WhatsApp webhook endpoint is online, reachable, and verified."
                }
                
        return {
            "status": "warning",
            "reachable": False,
            "validated_url": webhook_url,
            "message": (
                f"POST validation returned status {res_post.status_code}, but the verification payload was incorrect. "
                "Confirm that your custom proxy routes incoming webhook calls to /webhooks/whatsapp."
            ),
            "recovery_suggestions": [
                "Check if the POST /webhooks/whatsapp route is handling incoming JSON payloads",
                "Confirm that the endpoint intercepts validation ping payloads correctly"
            ]
        }
    except Exception as e:
        logger.error(f"POST validation check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "reachable": False,
            "validated_url": webhook_url,
            "message": f"POST Connection Failed: {str(e)}. Webhook is not fully operational.",
            "recovery_suggestions": [
                "Verify internet connectivity",
                "Inspect the backend traceback for exceptions/crashes when processing incoming POST webhooks"
            ]
        }

@router.post("/test-local-backend")
async def test_local_backend():
    """
    Performs a direct connectivity check to the local backend port 8000 (Requirement 9 & 11).
    """
    import socket
    port = int(os.getenv("PORT", 8000))
    
    # Check if port is open locally
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    is_listening = sock.connect_ex(("127.0.0.1", port)) == 0
    sock.close()
    
    # Try querying the /health endpoint
    health_status = "unknown"
    health_details = {}
    health_error = None
    
    if is_listening:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
                if res.status_code == 200:
                    health_status = "healthy"
                    health_details = res.json()
                else:
                    health_status = f"unhealthy (status {res.status_code})"
        except Exception as e:
            health_status = "error"
            health_error = str(e)
            
    # Resolve tunnel forwarding info
    from backend.services.connectivity_service import connectivity_svc
    active_tunnel = await connectivity_svc.get_active_ngrok_url()
    
    # Detailed logging (Requirement 11)
    logger.info(
        f"[LOCAL BACKEND DIAGNOSTIC]\n"
        f"  Configured Port: {port}\n"
        f"  Is Port Listening: {is_listening}\n"
        f"  Tunnel Forwarding Target: {active_tunnel or 'None'}\n"
        f"  Health Check Status: {health_status}\n"
        f"  Health Check Error: {health_error}"
    )
    
    return {
        "status": "success" if (is_listening and health_status == "healthy") else "error",
        "configured_port": port,
        "is_listening": is_listening,
        "tunnel_forwarding_target": active_tunnel,
        "health_status": health_status,
        "health_details": health_details,
        "health_error": health_error,
        "message": (
            "Local backend is running and fully responsive!" 
            if (is_listening and health_status == "healthy") else
            "Local backend check failed. The server is either offline or not responding on the configured port."
        )
    }

@router.post("/test-public-tunnel")
async def test_public_tunnel():
    """
    Performs a comparative connectivity check between local backend health and public tunnel health (Requirement 4 & 5).
    """
    import socket
    import httpx
    import os
    import time
    from backend.services.tunnel_manager import tunnel_mgr
    
    port = int(os.getenv("PORT", 8000))
    local_listening = False
    local_health = "offline"
    ssh_running = False
    public_url = None
    public_status = "offline"
    public_status_code = None
    public_error = None
    webhook_status = "offline"
    
    # Error classification variables (Requirement 5)
    failing_step = "none"
    failure_cause = "none"
    message = "Public tunnel is online and successfully forwarding traffic to local backend!"
    recovery_actions = []
    
    # 1. Port Listening Check (Requirement 4.2)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            local_listening = (s.connect_ex(("127.0.0.1", port)) == 0)
    except Exception as ex:
        local_listening = False
        public_error = f"Socket error: {str(ex)}"
        
    if not local_listening:
        failing_step = "local_port_check"
        failure_cause = "port_not_listening"
        message = f"Local port {port} is offline or not listening."
        recovery_actions = [
            "Start the backend server (run start_all.bat).",
            f"Verify that uvicorn is configured to bind to port {port}."
        ]
        
    # 2. Local /health Endpoint Check (Requirement 4.3)
    if failing_step == "none":
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
                if res.status_code == 200:
                    local_health = "healthy"
                else:
                    local_health = f"status {res.status_code}"
        except Exception as e:
            local_health = f"error: {str(e)}"
            
        if local_health != "healthy":
            failing_step = "local_health_check"
            failure_cause = "local_health_check_failed"
            message = f"Local backend health check endpoint failed: {local_health}."
            recovery_actions = [
                "Check database connectivity (Supabase URL/Key in .env).",
                "Look at the backend server logs for traceback or database runtime errors."
            ]

    # 3. Tunnel Process check (Requirement 4.4)
    if failing_step == "none":
        ssh_running = (tunnel_mgr.proc is not None and tunnel_mgr.proc.poll() is None) or (tunnel_mgr.status == "Running" and getattr(tunnel_mgr, "is_reused", False))
        if not ssh_running:
            failing_step = "ssh_process_check"
            # Distinguish process crashed vs stopped
            if tunnel_mgr.error_reason == "ssh_process_crashed":
                failure_cause = "ssh_process_crashed"
                message = "The localhost.run SSH tunnel process crashed unexpectedly."
            else:
                failure_cause = "ssh_tunnel_offline"
                message = "No active SSH tunnel process detected."
            recovery_actions = [
                "Click 'Restart Tunnel' to spawn a new SSH process.",
                "Verify OpenSSH client is installed and accessible in the system PATH."
            ]
            # Automatically trigger recovery if process died
            import threading
            threading.Thread(target=lambda: tunnel_mgr.heal_tunnel("SSH process died detected by test endpoint"), daemon=True).start()

    # 4. Tunnel URL Availability check (Requirement 5)
    if failing_step == "none":
        public_url = tunnel_mgr.public_url
        if not public_url:
            failing_step = "tunnel_url_check"
            failure_cause = "tunnel_url_missing"
            message = "Tunnel is active but no public forwarding URL has been generated yet."
            recovery_actions = [
                "Wait a few seconds for the provider DNS to propagate.",
                "Click 'Restart Tunnel' if the URL does not update."
            ]

    # 5. Public Health endpoint check (Requirement 4.5)
    if failing_step == "none":
        try:
            async with httpx.AsyncClient() as client:
                res_pub = await client.get(f"{public_url.rstrip('/')}/health", timeout=15.0)
                public_status_code = res_pub.status_code
                if res_pub.status_code == 200:
                    public_status = "healthy"
                else:
                    public_status = f"status {res_pub.status_code}"
                    public_error = "Invalid reverse proxy configuration"
        except httpx.ConnectTimeout:
            public_status = "timeout"
            public_error = "Request never reached backend"
        except httpx.ConnectError:
            public_status = "dns_error"
            public_error = "Request never reached backend"
        except httpx.RemoteProtocolError:
            public_status = "remote_protocol_error"
            public_error = "Tunnel closed connection before forwarding"
        except Exception as e:
            ex_str = str(e).lower()
            if "ssl" in ex_str or "handshake" in ex_str:
                public_status = "tls_error"
                public_error = "TLS handshake failed"
            elif "disconnected" in ex_str or "connection closed" in ex_str or "closed connection" in ex_str:
                public_status = "disconnect_error"
                public_error = "Backend closed connection unexpectedly"
            else:
                public_status = "error"
                public_error = "Request never reached backend"
            
        if public_status != "healthy":
            failing_step = "public_health_check"
            failure_cause = public_error
            message = f"Public health check failed: {public_error}."
            recovery_actions = [
                "Click 'Restart Tunnel' to obtain a fresh public domain forwarding mapping.",
                "Check that local firewalls are not blocking port 8000 reverse-forward bindings."
            ]

    # 6. Public Webhook Reachability check (Requirement 4.6)
    if failing_step == "none":
        try:
            async with httpx.AsyncClient() as client:
                res_wh = await client.post(
                    f"{public_url.rstrip('/')}/webhooks/whatsapp",
                    json={"event": "ping"},
                    headers={"Content-Type": "application/json"},
                    timeout=15.0
                )
                if res_wh.status_code in [200, 201, 202, 400, 422]:
                    webhook_status = "healthy"
                else:
                    webhook_status = f"status {res_wh.status_code}"
                    public_error = "Invalid reverse proxy configuration"
        except httpx.ConnectTimeout:
            webhook_status = "timeout"
            public_error = "Request never reached backend"
        except httpx.ConnectError:
            webhook_status = "dns_error"
            public_error = "Request never reached backend"
        except httpx.RemoteProtocolError:
            webhook_status = "remote_protocol_error"
            public_error = "Tunnel closed connection before forwarding"
        except Exception as e:
            ex_str = str(e).lower()
            if "ssl" in ex_str or "handshake" in ex_str:
                webhook_status = "tls_error"
                public_error = "TLS handshake failed"
            elif "disconnected" in ex_str or "connection closed" in ex_str or "closed connection" in ex_str:
                webhook_status = "disconnect_error"
                public_error = "Backend closed connection unexpectedly"
            else:
                webhook_status = "error"
                public_error = "Request never reached backend"
            
        if webhook_status != "healthy":
            failing_step = "public_webhook_check"
            failure_cause = public_error
            message = f"WhatsApp webhook routing check failed: {public_error}."
            recovery_actions = [
                "Ensure local routing paths for /webhooks/whatsapp are correct.",
                "Verify no middleware is blocking incoming POST webhook requests."
            ]
    # Log diagnostic status (Requirement 7)
    logger.info(
        f"[DIAGNOSTICS RUN] Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"  Local Port 8000 Listen: {local_listening}\n"
        f"  Local /health Check: {local_health}\n"
        f"  SSH Client Active: {ssh_running}\n"
        f"  Public Tunnel URL: {public_url or 'None'}\n"
        f"  Public Health Status: {public_status} (code: {public_status_code}, error: {public_error})\n"
        f"  Webhook Route Health: {webhook_status}\n"
        f"  Failing Step: {failing_step} | Failure Cause: {failure_cause}"
    )

    diags = tunnel_mgr.get_diagnostics()
    # Override current diagnostics to match live state immediately (Requirement 1)
    diags["status"] = "Running" if (failing_step == "none" or failing_step in ["public_health_check", "public_webhook_check"]) else "Stopped"
    diags["error_reason"] = failure_cause if failure_cause != "none" else None

    # Clear state conflict (Requirement 2)
    # If tunnel is offline or not running, the public URL is none
    return {
        "status": "success" if failing_step == "none" else "error",
        "configured_port": port,
        "local_health": "healthy" if local_health == "healthy" else "offline",
        "public_tunnel_url": public_url if ssh_running else None,
        "public_health_status": "healthy" if public_status == "healthy" else "offline",
        "public_status_code": public_status_code,
        "public_error": public_error or (webhook_status if webhook_status != "healthy" else None),
        "message": message,
        "failure_cause": failure_cause,
        "failing_step": failing_step,
        "recovery_actions": recovery_actions,
        "diagnostics": diags
    }

@router.post("/restart-tunnel")
async def restart_tunnel():
    """
    Stops the existing tunnel process, starts a new tunnel process, and refreshes the public URL.
    """
    from backend.services.tunnel_manager import tunnel_mgr
    import asyncio
    
    logger.info("[Tunnel Action] Manually restarting tunnel...")
    
    # Run healing in background thread to avoid blocking FastAPI
    await asyncio.to_thread(tunnel_mgr.heal_tunnel, "Manual restart requested via API")
    
    diags = tunnel_mgr.get_diagnostics()
    if tunnel_mgr.status != "Running":
        raise HTTPException(
            status_code=504, 
            detail=f"Failed to restart tunnel. Error reason: {diags.get('error_reason') or 'unknown'}"
        )
        
    return {
        "status": "success",
        "message": "Tunnel restarted successfully and diagnostics refreshed.",
        "public_url": tunnel_mgr.public_url,
        "diagnostics": diags
    }

CONFIG_FILE = "nursery_delivery_config.json"

@router.get("/delivery-config")
async def get_delivery_config():
    import json
    default_config = {
        "enabled": True,
        "free_min_distance": 5.0,
        "free_max_distance": 10.0,
        "charge_under_5km_per_km": 10.0,
        "charge_over_10km_per_km": 15.0,
        "huge_purchase_min_amount": 1500.0,
        "huge_purchase_discount_pct": 10.0,
        "permanent_customer_min_orders": 5,
        "permanent_customer_discount_pct": 15.0
    }
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f)
        return default_config
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            # Fill missing keys with defaults
            for k, v in default_config.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return default_config

class DeliveryConfigModel(BaseModel):
    enabled: bool
    free_min_distance: float
    free_max_distance: float
    charge_under_5km_per_km: float
    charge_over_10km_per_km: float
    huge_purchase_min_amount: float
    huge_purchase_discount_pct: float
    permanent_customer_min_orders: int
    permanent_customer_discount_pct: float

@router.post("/delivery-config")
async def save_delivery_config(config: DeliveryConfigModel):
    import json
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config.dict(), f)
        return {"status": "success", "message": "Delivery config saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

