# backend/modules/messaging_module/router.py
import logging
from fastapi import APIRouter, HTTPException, Request, status
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

@router.post("/webhooks/whatsapp")
async def process_whatsapp_webhook(request: Request):
    """
    Evolution API webhook endpoint to receive real-time messages.
    """
    try:
        payload = await request.json()
        logger.info(f"Evolution Webhook raw payload received.")
        res = await handle_evolution_webhook(payload)
        return res
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}
