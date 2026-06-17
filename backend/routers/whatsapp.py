# backend/routers/whatsapp.py
import os
import uuid
import logging
import asyncio
import httpx
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
    product_id: Optional[str] = Field(None, example="prod_cardamom")
    recipient_phone: Optional[str] = Field(None, example="917306796590")

class ToggleAutopilotRequest(BaseModel):
    lead_id: str = Field(..., example="lead_uuid_here")
    autopilot: bool = Field(..., example=True)

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
        query_context = lead["reply"] if lead else "inquiring about cardamom price"

        # Generate response using LLM
        llm = get_ollama_llm()
        prompt = (
            f"You are a customer named @{username} chatting on WhatsApp with Kochi Spice Farm. "
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
            text="Sounds great! Yes, I want to order 2 packs of Cardamom. Where can I pay?"
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
            prod_id = products[0]["id"] if products else "prod_cardamom"
            
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
            recipient = "917306796590"
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
                        product_id = products[0]["id"] if products else "prod_cardamom"
                        
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
