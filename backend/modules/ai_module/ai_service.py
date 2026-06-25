# backend/modules/ai_module/ai_service.py
import logging
import asyncio
from backend.services.supabase_service import supabase_svc
from backend.langgraph.sales_workflow import run_sales_chat
from backend.modules.websocket_module import websocket_manager

logger = logging.getLogger("vyaparai.ai.service")

class AiService:
    async def process_incoming_message(self, conversation_id: str, customer_message: str):
        """
        Processes incoming WhatsApp customer message with AI agent.
        1. Verifies if AI is active and not overridden.
        2. Resolves or creates a target Lead record for LangGraph.
        3. Calls LangGraph sales workflow.
        4. Saves AI reply to Database and triggers outbound delivery via WhatsApp.
        """
        # Brief sleep to allow message history write to settle and look natural
        await asyncio.sleep(1.0)
        
        # 1. Fetch conversation
        conv = supabase_svc.get_conversation(conversation_id)
        if not conv:
            logger.error(f"Conversation {conversation_id} not found. AI aborting.")
            return

        # Check takeover status
        if not conv.get("ai_enabled", True) or conv.get("human_override", False):
            logger.info(f"AI Autopilot disabled or human override active for conversation {conversation_id}. Aborting response.")
            return

        # 2. Resolve Lead ID for LangGraph compatibility
        lead_id = conv.get("lead_id")
        tenant_id = conv.get("tenant_id", "00000000-0000-0000-0000-000000000000")
        
        # Resolve target product from database (dynamically match product based on source video title)
        products = supabase_svc.get_products()
        product_id = products[0]["id"] if products else "prod_cardamom"
        
        if lead_id and products:
            try:
                leads = supabase_svc.get_youtube_leads()
                lead = next((l for l in leads if l["id"] == lead_id), None)
                if lead and lead.get("video_id"):
                    video = supabase_svc.get_youtube_video(lead["video_id"])
                    if video and video.get("title"):
                        title_lower = video["title"].lower()
                        matched_product = None
                        
                        if "paint" in title_lower:
                            matched_product = next((p for p in products if "paint" in p["name"].lower()), None)
                        elif "coconut" in title_lower or "oil" in title_lower:
                            matched_product = next((p for p in products if "coconut" in p["name"].lower() or "oil" in p["name"].lower()), None)
                        elif "cardamom" in title_lower or "elaichi" in title_lower:
                            matched_product = next((p for p in products if "cardamom" in p["name"].lower() or "elaichi" in p["name"].lower()), None)
                            
                        if matched_product:
                            product_id = matched_product["id"]
                            logger.info(f"Dynamically mapped product {product_id} ('{matched_product['name']}') for video title '{video['title']}'")
            except Exception as pe:
                logger.error(f"Failed to dynamically match product for lead: {pe}")
        
        if not lead_id:
            # Direct-to-WhatsApp customer. Create a lead record for LangGraph session tracking.
            logger.info("Direct WhatsApp customer detected. Creating local lead record...")
            businesses = supabase_svc.get_businesses()
            business_id = businesses[0]["id"] if businesses else None
            
            # Form clean username from customer phone number
            customer_phone = conv.get("customer_phone", "unknown")
            username = f"wa_{customer_phone.replace('+', '')}"
            
            try:
                # Create qualified lead
                lead = supabase_svc.create_lead(
                    business_id=business_id,
                    username=username,
                    intent="HIGH_INTENT"
                )
                lead_id = lead["id"]
                # Update conversation mapping
                supabase_svc.update_conversation_v2(conversation_id, {"lead_id": lead_id})
                logger.info(f"Mapped conversation {conversation_id} to new lead {lead_id}")
            except Exception as e:
                logger.error(f"Failed to create lead for customer: {e}")
                return

        # 3. Call LangGraph Sales Graph
        logger.info(f"Executing LangGraph step for lead {lead_id} (product: {product_id})...")
        try:
            chat_res = run_sales_chat(
                lead_id=lead_id,
                product_id=product_id,
                user_message=customer_message
            )
            ai_reply = chat_res["response"]
        except Exception as e:
            logger.error(f"LangGraph execution failed: {e}")
            ai_reply = "Thank you! We received your message. A representative will contact you shortly."

        # 4. Save and Dispatch outbound WhatsApp reply as AI
        from backend.modules.messaging_module import messaging_svc
        try:
            # We call send_outbound_message with role 'ai'
            await messaging_svc.send_outbound_message(
                conversation_id=conversation_id,
                sender_type="ai",
                content=ai_reply
            )
            
            # Sync conversation state updates from LangGraph to conversation record
            conv_status = "open"
            if chat_res.get("next_state") == "COMPLETE":
                conv_status = "closed"
            supabase_svc.update_conversation_v2(conversation_id, {
                "state": chat_res.get("next_state", "WELCOME"),
                "status": conv_status
            })
            
        except Exception as e:
            logger.error(f"Failed to dispatch AI response: {e}")

# Global AI Service instance
ai_svc = AiService()
