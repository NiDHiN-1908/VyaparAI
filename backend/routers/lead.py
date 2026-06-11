# backend/routers/lead.py
import logging
from fastapi import APIRouter, HTTPException
from backend.models.schemas import CommentCreateRequest, LeadCreateRequest
from backend.services.supabase_service import supabase_svc
from backend.agents.lead_agent import lead_agent

logger = logging.getLogger("vyaparai.routers.lead")
router = APIRouter(prefix="", tags=["CRM Leads & Social Comments"])

@router.post("/comment")
async def register_comment(payload: CommentCreateRequest):
    logger.info(f"Ingesting comment from {payload.username} on video {payload.video_id}")
    try:
        # Resolve the business ID from the video ID
        # Video -> Voiceover -> Translation -> Script -> Product -> Business
        video = supabase_svc.get_video(payload.video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # In mock mode, we search or assign a default business
        business_id = None
        businesses = supabase_svc.get_businesses()
        if businesses:
            business_id = businesses[0]["id"]
        else:
            # Seed mock business
            mock_bus = supabase_svc.create_business(name="VyaparAI Shop", location="Kochi")
            business_id = mock_bus["id"]

        # Run lead agent pipeline (classifies, saves comment, promotes if high intent)
        res = lead_agent.process_incoming_comment(
            video_id=payload.video_id,
            business_id=business_id,
            username=payload.username,
            comment_text=payload.comment_text
        )

        return {"status": "success", "comment": res["comment"], "lead_created": res["lead"] is not None, "lead": res["lead"]}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error handling comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/lead")
async def create_lead(payload: LeadCreateRequest):
    logger.info(f"Manually creating CRM lead: {payload.username}")
    try:
        business = supabase_svc.get_business(payload.business_id)
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")

        res = supabase_svc.create_lead(
            business_id=payload.business_id,
            username=payload.username,
            intent=payload.intent or "MEDIUM_INTENT",
            comment_id=None
        )
        return {"status": "success", "data": res}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error creating lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))
