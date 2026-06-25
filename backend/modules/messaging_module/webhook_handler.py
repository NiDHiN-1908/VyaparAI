# backend/modules/messaging_module/webhook_handler.py
import logging
import asyncio
from typing import Dict, Any
from backend.services.supabase_service import supabase_svc
from backend.modules.conversation_module.conversation_service import conversation_svc
from backend.modules.websocket_module import websocket_manager
from .message_repository import message_repo

logger = logging.getLogger("vyaparai.messaging.webhook")

async def handle_evolution_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses and processes inbound Evolution API webhook events.
    1. Validates event type.
    2. Maps instance to tenant.
    3. Resolves conversation thread.
    4. Stores message.
    5. Broadcasts to WebSocket.
    6. Triggers AI agent if autopilot is active.
    """
    event_type = payload.get("event")
    instance_name = payload.get("instance")
    
    logger.info(f"Incoming Evolution webhook event '{event_type}' for instance '{instance_name}'")
    
    # 1. Resolve Tenant ID associated with the WhatsApp instance
    tenant_id = "00000000-0000-0000-0000-000000000000" # Default fallback
    if instance_name:
        instance = supabase_svc.get_whatsapp_instance_by_name(instance_name)
        if instance:
            tenant_id = instance["tenant_id"]
            
            # If the event is connection state update, sync instance status in DB
            if event_type == "connection.update":
                data = payload.get("data", {})
                state = data.get("state") or data.get("status")
                if state:
                    logger.info(f"Connection state update for {instance_name}: {state}")
                    mapped_status = "connected" if state in ["open", "connected"] else "disconnected"
                    phone = data.get("phone")
                    if not phone and data.get("wuid"):
                        wuid = data.get("wuid")
                        phone = wuid.split("@")[0] if "@" in wuid else wuid
                        
                    if mapped_status == "connected" and phone:
                        supabase_svc.update_whatsapp_instance_status(instance["id"], mapped_status, phone)
                    else:
                        supabase_svc.update_whatsapp_instance_status(instance["id"], mapped_status)
                    
                    # Notify WebSocket
                    await websocket_manager.broadcast_to_tenant(
                        tenant_id=tenant_id,
                        event_type="whatsapp.connected" if mapped_status == "connected" else "whatsapp.disconnected",
                        data={"instance_id": instance["id"], "instance_name": instance_name, "status": mapped_status}
                    )
                    return {"status": "success", "event": "connection_update_synced"}

    # 2. Only process message inserts
    if event_type not in ["messages.upsert", "messages.send"]:
        return {"status": "ignored", "reason": f"Unhandled event type: {event_type}"}

    data_payload = payload.get("data", {})
    if not data_payload:
        return {"status": "ignored", "reason": "Empty event data payload"}

    # Extract key variables
    key = data_payload.get("key", {})
    remote_jid = key.get("remoteJid", "") # e.g. "917306796590@s.whatsapp.net"
    from_me = key.get("fromMe", False)
    message_id = key.get("id")

    if not remote_jid or "@g.us" in remote_jid:
        # Ignore group chats or empty numbers
        return {"status": "ignored", "reason": "Group message or invalid JID"}

    # Parse customer phone
    customer_phone = remote_jid.split("@")[0]

    # 3. Parse content type, text, and media metadata
    content = ""
    message_type = "text"
    media_metadata = {}

    msg_body = data_payload.get("message", {})
    if not msg_body:
        return {"status": "ignored", "reason": "No message body found"}

    if "conversation" in msg_body:
        content = msg_body["conversation"]
    elif "extendedTextMessage" in msg_body:
        content = msg_body["extendedTextMessage"].get("text", "")
    elif "imageMessage" in msg_body:
        message_type = "image"
        content = msg_body["imageMessage"].get("url") or msg_body["imageMessage"].get("mediaUrl") or ""
        media_metadata["mimetype"] = msg_body["imageMessage"].get("mimetype", "image/jpeg")
        media_metadata["caption"] = msg_body["imageMessage"].get("caption", "")
    elif "videoMessage" in msg_body:
        message_type = "video"
        content = msg_body["videoMessage"].get("url") or msg_body["videoMessage"].get("mediaUrl") or ""
        media_metadata["mimetype"] = msg_body["videoMessage"].get("mimetype", "video/mp4")
        media_metadata["caption"] = msg_body["videoMessage"].get("caption", "")
    elif "audioMessage" in msg_body:
        message_type = "audio"
        content = msg_body["audioMessage"].get("url") or msg_body["audioMessage"].get("mediaUrl") or ""
        media_metadata["mimetype"] = msg_body["audioMessage"].get("mimetype", "audio/ogg")
    elif "documentMessage" in msg_body:
        message_type = "document"
        content = msg_body["documentMessage"].get("url") or msg_body["documentMessage"].get("mediaUrl") or ""
        media_metadata["mimetype"] = msg_body["documentMessage"].get("mimetype", "application/pdf")
        media_metadata["fileName"] = msg_body["documentMessage"].get("fileName", "document.pdf")
    else:
        logger.debug(f"Unhandled message structure: {msg_body}")
        # Extract direct text if possible or stringify
        content = msg_body.get("text") or str(msg_body)

    # 4. Resolve Conversation ID
    # Get or create the conversation thread
    conv = await conversation_svc.get_or_create_conversation(tenant_id, customer_phone, channel="whatsapp")
    conversation_id = conv["id"]

    # 5. Determine Sender Type
    # If fromMe is True, the agent replied directly on their phone app
    if from_me:
        sender_type = "agent"
    else:
        sender_type = "customer"

    # Check YouTube attribution if the message contains the tracking suffix
    if sender_type == "customer" and content:
        import re
        match = re.search(r"Ref:\s*YT_([a-zA-Z0-9_-]+)", content)
        if match:
            comment_id = match.group(1)
            logger.info(f"Detected YouTube attribution tag Ref: YT_{comment_id}")
            yt_comment = supabase_svc.get_youtube_comment(comment_id)
            if yt_comment:
                leads = supabase_svc.get_youtube_leads()
                yt_lead = next((l for l in leads if l.get("comment_id") == comment_id), None)
                if not yt_lead:
                    logger.info(f"Lead not found for comment {comment_id}. Dynamically promoting to sales lead.")
                    yt_lead = supabase_svc.create_youtube_lead(
                        comment_id=comment_id,
                        video_id=yt_comment["video_id"],
                        username=yt_comment["username"],
                        intent=yt_comment.get("intent", "HIGH_INTENT")
                    )
                
                if yt_lead:
                    logger.info(f"Linking conversation {conversation_id} to YouTube lead {yt_lead['id']}")
                    supabase_svc.update_conversation_v2(conversation_id, {"lead_id": yt_lead["id"]})
                    # Re-fetch conv to include lead_id
                    conv = supabase_svc.get_conversation(conversation_id) or conv

    # Assemble message metadata
    metadata = {
        "provider_message_sid": message_id,
        "pushName": data_payload.get("pushName", ""),
        "status": "delivered",
        **media_metadata
    }

    # 6. Save message record in DB
    msg_record = message_repo.create(
        conversation_id=conversation_id,
        sender_type=sender_type,
        content=content,
        message_type=message_type,
        metadata=metadata
    )

    # 7. Broadcast new message event via WebSocket
    await websocket_manager.broadcast_to_tenant(tenant_id, "message.created", msg_record)
    
    # Update conversation's updated_at timestamp in database
    supabase_svc.update_conversation_v2(conversation_id, {})
    await websocket_manager.broadcast_to_tenant(tenant_id, "conversation.updated", conv)

    # 8. Trigger AI response flow in the background if autopilot is enabled and message came from customer
    if sender_type == "customer":
        is_ai_enabled = conv.get("ai_enabled", True)
        is_human_override = conv.get("human_override", False)
        
        # Check human override takeover
        if is_ai_enabled and not is_human_override:
            logger.info(f"Triggering autonomous AI workflow for conversation {conversation_id}")
            from backend.modules.ai_module import ai_svc
            asyncio.create_task(ai_svc.process_incoming_message(conversation_id, content))
        else:
            logger.info(f"AI Autopilot disabled for conversation {conversation_id}. Awaiting manual agent reply.")

    return {"status": "success", "message_id": msg_record["id"]}
