# backend/modules/conversation_module/router.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from .conversation_repository import conversation_repo
from .conversation_service import conversation_svc
from backend.services.supabase_service import supabase_svc

router = APIRouter(prefix="/conversations", tags=["Conversations Management"])

class AssignAgentRequest(BaseModel):
    agent_id: str

class UpdateStatusRequest(BaseModel):
    status: str

class ToggleAutopilotRequest(BaseModel):
    ai_enabled: bool

@router.get("")
async def list_conversations(
    tenant_id: str = Query("00000000-0000-0000-0000-000000000000"),
    status: Optional[str] = Query(None)
):
    """
    Lists active conversations for a tenant, optionally filtered by status (open, closed).
    """
    try:
        conversations = conversation_repo.get_all(tenant_id, status)
        
        # Resolve lead details if lead_id is set
        leads = supabase_svc.get_youtube_leads()
        leads_map = {l["id"]: l for l in leads}
        comments = supabase_svc.get_youtube_comments()
        comments_map = {c["comment_id"]: c for c in comments}
        videos = supabase_svc.get_youtube_videos()
        videos_map = {v["video_id"]: v for v in videos}
        
        for conv in conversations:
            lead_id = conv.get("lead_id")
            if lead_id and lead_id in leads_map:
                lead = leads_map[lead_id]
                cmt_id = lead.get("comment_id")
                conv["lead"] = {
                    "id": lead["id"],
                    "username": lead.get("username"),
                    "intent": lead.get("intent"),
                    "comment_text": "",
                    "video_title": ""
                }
                if cmt_id and cmt_id in comments_map:
                    cmt = comments_map[cmt_id]
                    conv["lead"]["comment_text"] = cmt.get("text", "")
                    vid_id = cmt.get("video_id")
                    if vid_id and vid_id in videos_map:
                        conv["lead"]["video_title"] = videos_map[vid_id].get("title", "")
                        
        # Sort by updated_at or created_at desc to show newest first
        conversations.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
        return {"status": "success", "data": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{conversation_id}")
async def get_conversation_details(conversation_id: str):
    """
    Gets conversation details by ID.
    """
    conv = conversation_repo.get_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # Resolve lead details if lead_id is set
    lead_id = conv.get("lead_id")
    if lead_id:
        leads = supabase_svc.get_youtube_leads()
        lead = next((l for l in leads if l["id"] == lead_id), None)
        if lead:
            cmt_id = lead.get("comment_id")
            conv["lead"] = {
                "id": lead["id"],
                "username": lead.get("username"),
                "intent": lead.get("intent"),
                "comment_text": "",
                "video_title": ""
            }
            if cmt_id:
                cmt = supabase_svc.get_youtube_comment(cmt_id)
                if cmt:
                    conv["lead"]["comment_text"] = cmt.get("text", "")
                    video = supabase_svc.get_youtube_video(cmt["video_id"])
                    if video:
                        conv["lead"]["video_title"] = video.get("title", "")
                        
    return {"status": "success", "data": conv}

@router.get("/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """
    Fetches chronological message history for a conversation.
    """
    conv = conversation_repo.get_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        messages = supabase_svc.get_messages_by_conversation(conversation_id)
        return {"status": "success", "data": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{conversation_id}/assign")
async def assign_conversation_agent(conversation_id: str, payload: AssignAgentRequest):
    """
    Assigns an agent to take over the conversation.
    """
    try:
        updated = await conversation_svc.assign_agent(conversation_id, payload.agent_id)
        return {"status": "success", "data": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{conversation_id}/status")
async def update_conversation_status(conversation_id: str, payload: UpdateStatusRequest):
    """
    Closes or opens a conversation.
    """
    try:
        updated = await conversation_svc.update_status(conversation_id, payload.status)
        return {"status": "success", "data": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{conversation_id}/toggle-autopilot")
async def toggle_conversation_autopilot(conversation_id: str, payload: ToggleAutopilotRequest):
    """
    Toggles autopilot on/off for human takeover.
    """
    try:
        updated = await conversation_svc.toggle_autopilot(conversation_id, payload.ai_enabled)
        return {"status": "success", "data": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
