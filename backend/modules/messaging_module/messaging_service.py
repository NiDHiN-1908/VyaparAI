# backend/modules/messaging_module/messaging_service.py
import logging
import asyncio
from typing import Dict, Any, List, Optional
from .message_repository import message_repo
from backend.modules.whatsapp_module import whatsapp_instance_svc
from backend.modules.websocket_module import websocket_manager
from backend.services.supabase_service import supabase_svc

logger = logging.getLogger("vyaparai.messaging.service")

class MessagingService:
    async def send_outbound_message(self, conversation_id: str, sender_type: str, content: str, message_type: str = "text", sender_id: str = None, media_url: str = None, caption: str = None) -> Dict[str, Any]:
        """
        Saves a message record locally with a 'sending' status, queues it to be sent asynchronously, 
        and triggers a real-time event via WebSockets.
        """
        # 1. Resolve conversation
        conv = supabase_svc.get_conversation(conversation_id)
        if not conv:
            raise Exception("Conversation not found")
            
        tenant_id = conv["tenant_id"]
        recipient_phone = conv["customer_phone"]
        
        # Format the phone number (strip non-numeric values)
        import re
        cleaned_phone = re.sub(r'\D', '', recipient_phone)
        
        # 2. Resolve WhatsApp instance connected for this tenant (prioritize 'connected' status)
        instances = supabase_svc.get_whatsapp_instances(tenant_id)
        instance_name = "default_instance"
        if instances:
            connected_instances = [i for i in instances if i.get("status") == "connected"]
            if connected_instances:
                instance_name = connected_instances[0]["instance_name"]
            else:
                instance_name = instances[0]["instance_name"]
        
        # 3. Create initial database record with status 'sending'
        initial_metadata = {
            "status": "sending",
            "media_url": media_url,
            "caption": caption
        }
        msg = message_repo.create(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            message_type=message_type,
            content=content,
            metadata=initial_metadata
        )
        
        # Update conversation's updated_at timestamp
        supabase_svc.update_conversation_v2(conversation_id, {})
        
        # Broadcast message sending status via WebSocket
        await websocket_manager.broadcast_to_tenant(tenant_id, "message.sent", msg)
        
        # 4. Dispatch the message asynchronously to prevent blocking the HTTP thread
        asyncio.create_task(self._dispatch_message_async(instance_name, cleaned_phone, msg, media_url, caption))
        
        return msg

    async def _dispatch_message_async(self, instance_name: str, recipient: str, msg: Dict[str, Any], media_url: str = None, caption: str = None):
        """
        Asynchronously calls the WhatsApp Provider API, handling failures and retries.
        """
        provider = whatsapp_instance_svc.provider
        message_id = msg["id"]
        conversation_id = msg["conversation_id"]
        
        # Resolve tenant ID for WS broadcast
        tenant_id = None
        conv = supabase_svc.get_conversation(conversation_id)
        if conv:
            tenant_id = conv["tenant_id"]

        max_retries = 3
        backoff = 1.0
        success = False
        res = None

        for attempt in range(max_retries):
            try:
                if msg["message_type"] == "text":
                    res = await provider.send_message(instance_name, recipient, msg["content"])
                else:
                    # In case of media message, content contains the media_url
                    target_url = media_url or msg["content"]
                    res = await provider.send_media(instance_name, recipient, target_url, msg["message_type"], caption)
                success = True
                break
            except Exception as e:
                logger.warning(f"Failed to dispatch message {message_id} on attempt {attempt+1}: {e}")
                await asyncio.sleep(backoff)
                backoff *= 2.0

        if success:
            logger.info(f"Message {message_id} sent successfully to +{recipient}")
            # Retrieve WhatsApp Message ID/SID from API response
            message_sid = ""
            if isinstance(res, dict):
                key = res.get("key", {})
                message_sid = key.get("id") or res.get("id") or ""
                
            updates = {
                "status": "delivered",
                "provider_message_sid": message_sid
            }
            updated_msg = message_repo.update_metadata(message_id, updates)
            
            # Broadcast delivery success
            if tenant_id:
                await websocket_manager.broadcast_to_tenant(tenant_id, "message.delivered", updated_msg)
        else:
            logger.error(f"Message {message_id} failed permanently after {max_retries} attempts.")
            updated_msg = message_repo.update_metadata(message_id, {"status": "failed", "error": "Max retries exceeded"})
            if tenant_id:
                await websocket_manager.broadcast_to_tenant(tenant_id, "message.failed", updated_msg)

messaging_svc = MessagingService()
