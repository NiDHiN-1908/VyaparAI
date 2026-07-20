# backend/modules/messaging_module/message_repository.py
from typing import List, Dict, Any, Optional
from backend.services.supabase_service import supabase_svc

class MessageRepository:
    def create(self, conversation_id: str, sender_type: str, content: str, message_type: str = "text", sender_id: str = None, metadata: dict = None) -> Dict[str, Any]:
        """
        Creates a new message record in the database.
        """
        return supabase_svc.create_message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            content=content,
            message_type=message_type,
            sender_id=sender_id,
            metadata=metadata
        )

    def get_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a message by its ID.
        """
        return supabase_svc._select_one("messages", message_id)

    def get_for_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Fetches all messages inside a conversation ordered chronologically.
        """
        return supabase_svc.get_messages_by_conversation(conversation_id)

    def update_metadata(self, message_id: str, updates: dict) -> Optional[Dict[str, Any]]:
        """
        Appends or updates key-value pairs inside a message's JSONB metadata field.
        """
        return supabase_svc.update_message_metadata(message_id, updates)

    def get_by_provider_sid(self, provider_message_sid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a message by its provider message ID/SID.
        """
        return supabase_svc.get_message_by_provider_sid(provider_message_sid)
        
message_repo = MessageRepository()
