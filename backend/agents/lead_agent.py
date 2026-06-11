# backend/agents/lead_agent.py
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from backend.agents.comment_monitor_agent import classify_comment
from backend.services.supabase_service import supabase_svc

logger = logging.getLogger("vyaparai.agents.lead_agent")

class LeadAgent:
    def process_incoming_comment(
        self, 
        video_id: str, 
        business_id: str, 
        username: str, 
        comment_text: str
    ) -> Dict[str, Any]:
        """
        Monitors incoming comments, runs classification, saves comments,
        and automatically creates CRM lead records for actionable intents.
        """
        # 1. Classify the comment
        intent_class = classify_comment(comment_text)
        logger.info(f"Comment by {username} classified as: {intent_class}")

        # 2. Store comment in database
        comment_rec = supabase_svc.create_comment(
            video_id=video_id,
            username=username,
            comment_text=comment_text,
            intent_class=intent_class
        )

        lead_rec = None
        # 3. If HIGH or MEDIUM intent, promote to lead
        if intent_class in ["HIGH_INTENT", "MEDIUM_INTENT"]:
            logger.info(f"Promoting {username} to lead CRM...")
            
            # Simple language detection heuristic (e.g. word check or default)
            detected_lang = "English"
            text_lower = comment_text.lower()
            if any(w in text_lower for w in ["खरीद", "कीमत", "कॉल", "नमस्ते"]):
                detected_lang = "Hindi"
            elif any(w in text_lower for w in ["விலை", "வணக்கம்"]):
                detected_lang = "Tamil"
            elif any(w in text_lower for w in ["ధర", "నమస్తే"]):
                detected_lang = "Telugu"
            elif any(w in text_lower for w in ["വില", "എത്ര", "നമസ്കാരം"]):
                detected_lang = "Malayalam"

            lead_rec = supabase_svc.create_lead(
                business_id=business_id,
                comment_id=comment_rec["id"],
                username=username,
                language=detected_lang,
                intent=intent_class
            )
            
            # Increment leads counter in analytics
            try:
                supabase_svc.increment_analytics(business_id, "total_leads", 1)
            except Exception as e:
                logger.error(f"Failed to increment lead analytics: {e}")

        return {
            "comment": comment_rec,
            "lead": lead_rec
        }

lead_agent = LeadAgent()
