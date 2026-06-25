# backend/modules/conversation_module/conversation_repository.py
from typing import List, Dict, Any, Optional
from backend.services.supabase_service import supabase_svc

class ConversationRepository:
    def get_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        return supabase_svc.get_conversation(conversation_id)

    def get_by_phone(self, tenant_id: str, phone: str) -> Optional[Dict[str, Any]]:
        return supabase_svc.get_conversation_by_phone(tenant_id, phone)

    def get_by_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        return supabase_svc.get_conversation_by_lead(lead_id)

    def get_all(self, tenant_id: str, status: str = None) -> List[Dict[str, Any]]:
        return supabase_svc.get_conversations(tenant_id, status)

    def create(self, tenant_id: str, phone: str, channel: str = "whatsapp", lead_id: str = None) -> Dict[str, Any]:
        return supabase_svc.create_conversation_v2(
            tenant_id=tenant_id,
            customer_phone=phone,
            channel=channel,
            lead_id=lead_id
        )

    def update(self, conversation_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return supabase_svc.update_conversation_v2(conversation_id, updates)
        
conversation_repo = ConversationRepository()
