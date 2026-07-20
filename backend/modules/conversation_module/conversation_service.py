# backend/modules/conversation_module/conversation_service.py
import logging
from typing import Dict, Any, List
from .conversation_repository import conversation_repo
from backend.services.supabase_service import supabase_svc
from backend.modules.websocket_module import websocket_manager

logger = logging.getLogger("vyaparai.conversation.service")

class ConversationService:
    async def get_or_create_conversation(self, tenant_id: str, phone: str, channel: str = "whatsapp", lead_id: str = None, instance_name: str = None) -> Dict[str, Any]:
        """
        Retrieves existing conversation by phone or creates a new one, broadcasting WebSocket events.
        """
        conv = conversation_repo.get_by_phone(tenant_id, phone, instance_name)
        if not conv and lead_id:
            conv = conversation_repo.get_by_lead(lead_id)
            if conv and not conv.get("instance_name") and instance_name:
                conversation_repo.update(conv["id"], {"instance_name": instance_name})
                conv["instance_name"] = instance_name
            
        if not conv:
            conv = conversation_repo.create(tenant_id, phone, channel, lead_id, instance_name)
            logger.info(f"Created new conversation: {conv['id']} for instance {instance_name}")
            # Broadcast conversation creation via Websocket
            await websocket_manager.broadcast_to_tenant(tenant_id, "conversation.created", conv)
        return conv

    async def assign_agent(self, conversation_id: str, agent_id: str) -> Dict[str, Any]:
        """
        Assigns an agent to the conversation.
        """
        conv = conversation_repo.get_by_id(conversation_id)
        if not conv:
            raise Exception("Conversation not found")
            
        updated = conversation_repo.update(conversation_id, {"assigned_agent_id": agent_id})
        await websocket_manager.broadcast_to_tenant(conv["tenant_id"], "conversation.updated", updated)
        return updated

    async def update_status(self, conversation_id: str, status: str) -> Dict[str, Any]:
        """
        Closes, snoozes, or opens the conversation.
        """
        conv = conversation_repo.get_by_id(conversation_id)
        if not conv:
            raise Exception("Conversation not found")
            
        updated = conversation_repo.update(conversation_id, {"status": status})
        await websocket_manager.broadcast_to_tenant(conv["tenant_id"], "conversation.updated", updated)
        return updated

    async def toggle_autopilot(self, conversation_id: str, ai_enabled: bool) -> Dict[str, Any]:
        """
        Enables or disables AI autopilot (human override takeover).
        """
        conv = conversation_repo.get_by_id(conversation_id)
        if not conv:
            raise Exception("Conversation not found")
            
        # human_override is opposite of ai_enabled
        updates = {
            "ai_enabled": ai_enabled,
            "human_override": not ai_enabled
        }
        updated = conversation_repo.update(conversation_id, updates)
        
        # Keep legacy lead autopilot in sync if lead_id is present
        if conv.get("lead_id"):
            supabase_svc.update_youtube_lead_autopilot(conv["lead_id"], ai_enabled)

        await websocket_manager.broadcast_to_tenant(conv["tenant_id"], "conversation.updated", updated)
        return updated

conversation_svc = ConversationService()
