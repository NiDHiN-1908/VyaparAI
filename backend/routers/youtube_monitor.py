# backend/routers/youtube_monitor.py
import logging
from pydantic import BaseModel, Field
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from backend.services.supabase_service import supabase_svc
from backend.services.youtube_monitor_service import youtube_monitor_svc
from backend.crews.youtube_monitor_crew import youtube_monitor_crew

logger = logging.getLogger("vyaparai.routers.youtube_monitor")
router = APIRouter(prefix="/youtube", tags=["YouTube Comments & Leads Monitoring"])

class CommentInjectRequest(BaseModel):
    video_id: str = Field(..., example="PuCb1JHpBkM")
    username: str = Field(..., example="shyam_kumar")
    comment_text: str = Field(..., example="How to buy this product? Is it available?")

class ReplyApproveRequest(BaseModel):
    reply_text: str = Field(..., example="Thank you for your interest! Message us on WhatsApp to order.")

class AutoReplyToggleRequest(BaseModel):
    auto_reply: bool

@router.get("/videos")
async def get_monitored_videos():
    """List all monitored YouTube videos"""
    try:
        channels = supabase_svc.get_youtube_channels()
        if channels:
            await youtube_monitor_svc.sync_channel_videos(channels[0])
        videos = supabase_svc.get_youtube_videos()
        return {"status": "success", "data": videos}
    except Exception as e:
        logger.error(f"Error fetching monitored videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comments/sync")
async def sync_comments():
    """Manually trigger comment polling and video syncing from connected YouTube channels"""
    logger.info("Manually triggering comments and videos sync...")
    try:
        await youtube_monitor_svc.poll_comments_for_all_channels()
        return {"status": "success", "message": "Comments and videos synced from YouTube"}
    except Exception as e:
        logger.error(f"Error syncing comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/comments")
async def get_monitored_comments(
    video_id: Optional[str] = None,
    intent: Optional[str] = None,
    status: Optional[str] = None
):
    """Retrieve comments with optional filtering by video, intent, or status"""
    try:
        comments = supabase_svc.get_youtube_comments()
        
        # Get active monitored video IDs to exclude comments of deleted/unmonitored videos
        monitored_videos = supabase_svc.get_youtube_videos()
        monitored_video_ids = {v["video_id"] for v in monitored_videos}

        # Apply filters
        if video_id:
            comments = [c for c in comments if c["video_id"] == video_id]
        else:
            comments = [c for c in comments if c["video_id"] in monitored_video_ids]
        if intent:
            comments = [c for c in comments if c["intent"] == intent]
        if status:
            comments = [c for c in comments if c["status"] == status]
            
        # Combine comments with their replies for inbox view
        replies = supabase_svc.get_youtube_replies()
        replies_map = {r["comment_id"]: r for r in replies}
        
        combined_data = []
        for c in comments:
            item = dict(c)
            item["reply"] = replies_map.get(c["comment_id"])
            combined_data.append(item)
            
        # Sort by timestamp descending
        combined_data.sort(key=lambda x: x.get("timestamp") or x.get("created_at") or "", reverse=True)
            
        return {"status": "success", "data": combined_data}
    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comments/inject")
async def inject_comment(payload: CommentInjectRequest):
    """Inject a new comment for real-time processing and pipeline test"""
    logger.info(f"Injecting simulated comment from user @{payload.username}")
    try:
        channels = supabase_svc.get_youtube_channels()
        if not channels:
            # Connect mock if none exists
            from backend.routers.youtube_auth import mock_youtube_connect
            await mock_youtube_connect()
            channels = supabase_svc.get_youtube_channels()
            
        channel_id = channels[0]["channel_id"]
        
        # Verify video exists, create if not
        video = supabase_svc.get_youtube_video(payload.video_id)
        if not video:
            supabase_svc.create_youtube_video(
                channel_id=channel_id,
                video_id=payload.video_id,
                title="Monitored Marketing Video",
                publish_date=datetime.now().isoformat()
            )

        res = await youtube_monitor_svc.inject_comment_manually(
            channel_id=channel_id,
            video_id=payload.video_id,
            username=payload.username,
            text=payload.comment_text
        )
        
        return {"status": "success", "message": "Comment injected and processed", "data": res}
    except Exception as e:
        logger.error(f"Failed to inject comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comments/{comment_id}/approve")
async def approve_comment_reply(comment_id: str, payload: ReplyApproveRequest):
    """Approve a suggested reply draft and publish it directly to YouTube"""
    logger.info(f"Approving reply for comment: {comment_id}")
    try:
        comment = supabase_svc.get_youtube_comment(comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
            
        # Publish reply (handles API upload and database clean save/update)
        published_reply = await youtube_monitor_crew.publish_reply_to_youtube(comment_id, payload.reply_text)
            
        return {"status": "success", "message": "Reply approved and published successfully", "data": published_reply}
    except Exception as e:
        logger.error(f"Error approving comment reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comments/{comment_id}/reject")
async def reject_comment_reply(comment_id: str):
    """Reject and archive a suggested reply"""
    logger.info(f"Rejecting/dismissing reply suggestion for comment: {comment_id}")
    try:
        comment = supabase_svc.get_youtube_comment(comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
            
        # Update status
        supabase_svc.update_youtube_comment_status(comment_id, "rejected")
        
        reply_rec = supabase_svc.get_youtube_reply_by_comment(comment_id)
        if reply_rec:
            supabase_svc.update_youtube_reply(reply_rec["id"], {"status": "rejected"})
            
        return {"status": "success", "message": "Reply rejected and dismissed"}
    except Exception as e:
        logger.error(f"Error rejecting comment reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comments/{comment_id}/regenerate")
async def regenerate_comment_reply(comment_id: str):
    """Triggers Llama 3.1 to rewrite a new reply draft for a comment"""
    logger.info(f"Regenerating reply suggestion for comment: {comment_id}")
    try:
        comment = supabase_svc.get_youtube_comment(comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
            
        # Generate new reply text
        new_text = await youtube_monitor_crew.generate_comment_reply(
            comment_text=comment["text"],
            intent=comment["intent"],
            username=comment["username"]
        )
        
        # Save updated reply in DB
        reply_rec = supabase_svc.get_youtube_reply_by_comment(comment_id)
        if reply_rec:
            supabase_svc.update_youtube_reply(reply_rec["id"], {
                "suggested_reply": new_text,
                "status": "draft"
            })
        else:
            supabase_svc.create_youtube_reply(
                comment_id=comment_id,
                suggested_reply=new_text,
                status="draft"
            )
            
        return {"status": "success", "suggested_reply": new_text}
    except Exception as e:
        logger.error(f"Error regenerating comment reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/leads")
async def get_youtube_leads():
    """Retrieve all sales leads generated from YouTube comment qualification"""
    try:
        leads = supabase_svc.get_youtube_leads()
        
        # Join with comment source text
        comments = supabase_svc.get_youtube_comments()
        comments_map = {c["comment_id"]: c for c in comments}
        
        extended_leads = []
        for l in leads:
            item = dict(l)
            src_cmt = comments_map.get(l["comment_id"])
            if src_cmt:
                item["comment_text"] = src_cmt["text"]
            else:
                item["comment_text"] = ""
            extended_leads.append(item)
            
        extended_leads.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return {"status": "success", "data": extended_leads}
    except Exception as e:
        logger.error(f"Error retrieving leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_youtube_analytics_dashboard():
    """Retrieve aggregate performance and metrics for active channels"""
    try:
        channels = supabase_svc.get_youtube_channels()
        if not channels:
            return {
                "status": "success",
                "data": {
                    "comments_processed": 0,
                    "reply_rate": 0.0,
                    "lead_count": 0,
                    "conversion_rate": 0.0,
                    "top_videos": []
                }
            }
            
        channel_id = channels[0]["channel_id"]
        analytics = supabase_svc.get_youtube_analytics(channel_id)
        return {"status": "success", "data": analytics}
    except Exception as e:
        logger.error(f"Error loading youtube analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings/auto-reply")
async def toggle_auto_reply(payload: AutoReplyToggleRequest):
    """Enable or disable AUTO_REPLY=true mode"""
    youtube_monitor_crew.set_auto_reply(payload.auto_reply)
    return {"status": "success", "auto_reply": youtube_monitor_crew.auto_reply}

@router.get("/settings/auto-reply")
async def get_auto_reply_status():
    """Get AUTO_REPLY status"""
    return {"auto_reply": youtube_monitor_crew.auto_reply}

@router.get("/temp-clean-db")
async def temp_clean_db():
    from backend.services.supabase_service import supabase_svc
    supabase_svc.delete_youtube_video("dQw4w9WgXcQ")
    
    db_path = "backend/database/mock_db.json"
    import json
    with open(db_path, "r", encoding="utf-8") as f:
        db = json.load(f)
    
    db["youtube_comments"] = [c for c in db.get("youtube_comments", []) if c.get("video_id") != "dQw4w9WgXcQ"]
    
    # Filter replies
    db["youtube_replies"] = [r for r in db.get("youtube_replies", []) if not r.get("comment_id", "").startswith("MOCK_CMT_COCO_")]
    
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)
        
    from backend.services.supabase_service import MOCK_DB
    MOCK_DB.clear()
    MOCK_DB.update(db)
    return {"status": "success"}
