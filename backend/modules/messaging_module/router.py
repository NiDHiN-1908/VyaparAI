# backend/modules/messaging_module/router.py
import os
import logging
from fastapi import APIRouter, HTTPException, Request, status, Query, Response
from pydantic import BaseModel
from typing import Optional
from .messaging_service import messaging_svc
from .webhook_handler import handle_evolution_webhook

logger = logging.getLogger("vyaparai.messaging.router")
router = APIRouter(tags=["Conversations Messaging"])

class OutboundMessageRequest(BaseModel):
    content: str
    message_type: Optional[str] = "text"
    sender_id: Optional[str] = None
    media_url: Optional[str] = None
    caption: Optional[str] = None

@router.post("/conversations/{conversation_id}/send")
async def send_manual_message(conversation_id: str, payload: OutboundMessageRequest):
    """
    Agent manual message dispatch from dashboard.
    Disables AI Autopilot automatically to support human takeover.
    """
    logger.info(f"Manual outreach request for conversation {conversation_id}")
    
    # Human takeover rule: manual reply forces human override to True / ai_enabled to False
    try:
        from backend.modules.conversation_module.conversation_service import conversation_svc
        await conversation_svc.toggle_autopilot(conversation_id, ai_enabled=False)
    except Exception as e:
        logger.warning(f"Failed to automatically toggle autopilot off: {e}")

    try:
        msg = await messaging_svc.send_outbound_message(
            conversation_id=conversation_id,
            sender_type="agent",
            sender_id=payload.sender_id,
            content=payload.content,
            message_type=payload.message_type or "text",
            media_url=payload.media_url,
            caption=payload.caption
        )
        return {"status": "success", "data": msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/webhooks/whatsapp")
async def verify_whatsapp_webhook(
    request: Request,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    """
    WhatsApp / Meta webhook GET verification flow (Requirement 4 & 5).
    """
    headers_dict = dict(request.headers)
    query_params = dict(request.query_params)
    
    logger.info(
        f"[WEBHOOK GET] Incoming WhatsApp Verification:\n"
        f"  Path: {request.url.path}\n"
        f"  Query Params: {query_params}\n"
        f"  Headers: {headers_dict}\n"
        f"  Verification Token Received: '{hub_verify_token}'"
    )

    local_verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "vyaparai_verify_token_secret")
    
    if hub_mode == "subscribe" and hub_verify_token == local_verify_token:
        logger.info(f"[WEBHOOK GET] Verification succeeded! Returning challenge: {hub_challenge}")
        return Response(content=str(hub_challenge or ""), media_type="text/plain")
        
    logger.warning(
        f"[WEBHOOK GET] Verification failed. Token mismatch or missing subscribe mode.\n"
        f"  Expected: '{local_verify_token}'\n"
        f"  Received: '{hub_verify_token}'"
    )
    raise HTTPException(
        status_code=403, 
        detail="Verification token mismatch or invalid verification request parameters"
    )

@router.post("/webhooks/whatsapp")
async def process_whatsapp_webhook(request: Request):
    """
    Evolution API/Meta webhook endpoint to receive real-time messages.
    """
    headers_dict = dict(request.headers)
    query_params = dict(request.query_params)
    
    logger.info(
        f"[WEBHOOK POST] Incoming WhatsApp Webhook Payload:\n"
        f"  Path: {request.url.path}\n"
        f"  Query Params: {query_params}\n"
        f"  Headers: {headers_dict}"
    )
    
    try:
        payload = await request.json()
        logger.info(f"Webhook raw payload: {payload}")
        
        # Intercept local ping validation requests (used by the Validate button)
        if payload.get("event") == "ping":
            logger.info("[WEBHOOK POST] Intercepted validation ping. Returning pong.")
            return {"status": "success", "message": "pong"}
            
        res = await handle_evolution_webhook(payload)
        return res
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}
