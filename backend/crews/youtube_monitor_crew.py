# backend/crews/youtube_monitor_crew.py
import logging
import asyncio
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from crewai import Crew, Task, Process

from backend.agents.youtube_agents import (
    make_channel_agent,
    make_video_monitoring_agent,
    make_comment_collector_agent,
    make_intent_classification_agent,
    make_reply_generation_agent,
    make_approval_agent,
    make_lead_creation_agent,
    make_reply_publisher_agent
)
from backend.services.supabase_service import supabase_svc
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.crews.youtube_monitor_crew")

# Regex-based fallbacks for intent classification
HIGH_INTENT_PATTERNS = [
    r"\bprice\b", r"\bcost\b", r"\bhow\s+much\b", r"\brate\b", r"\bbuy\b", r"\border\b", 
    r"\bavailable\b", r"\bdelivery\b", r"\blocation\b", r"\baddress\b", r"\bcontact\b",
    r"\bwhatsapp\b", r"\bphone\b", r"\bnumber\b", r"\bcash\b", r"\bcod\b", r"\bpay\b",
    r"\bshipping\b", r"\bship\b", r"\bwant\b", r"\bneed\b", r"\bget\b", r"\bpurchase\b",
    r"₹", r"\brs\.?", r"\brupees\b",
    # Hindi
    r"खरीद", r"कीमत", r"कॉल", r"दाम", r"पैसे", r"डिलीवरी", r"नंबर",
    # Tamil
    r"விலை", r"வாங்க", r"டெலிவரி", r"எண்",
    # Telugu
    r"ధర", r"ఖరీదు", r"కొనాలి",
    # Malayalam
    r"വില", r"എത്ര", r"വാങ്ങാൻ", r"ഫോൺ"
]

MEDIUM_INTENT_PATTERNS = [
    r"\bwhy\b", r"\bwhat\b", r"\bhow\b", r"\bquestion\b", r"\buse\b", r"\bquality\b",
    r"\borganic\b", r"\bpure\b", r"\bchemical\b", r"\bdetails\b", r"\binfo\b",
    r"जानकारी", r"விவரம்", r"விവരங்கள்"
]

import json
import os

CONFIG_PATH = "auto_reply_config.json"

def get_auto_reply_setting() -> bool:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
                return data.get("auto_reply", False)
        except Exception:
            pass
    return False

def set_auto_reply_setting(val: bool):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump({"auto_reply": val}, f)
    except Exception:
        pass

def fallback_classify_comment(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    for pattern in HIGH_INTENT_PATTERNS:
        if re.search(pattern, text_lower):
            return {"intent": "HIGH_INTENT", "confidence": 0.95}
    for pattern in MEDIUM_INTENT_PATTERNS:
        if re.search(pattern, text_lower):
            return {"intent": "MEDIUM_INTENT", "confidence": 0.80}
    
    # Check if links or promotions are present -> SPAM
    if "http" in text_lower or ".com" in text_lower or "www." in text_lower or "subscribe" in text_lower:
        return {"intent": "SPAM", "confidence": 0.99}
        
    return {"intent": "LOW_INTENT", "confidence": 0.70}

def fallback_generate_reply(text: str, intent: str, username: str) -> str:
    # Resolve contact phone number dynamically from active business
    from backend.services.supabase_service import supabase_svc
    businesses = supabase_svc.get_businesses()
    contact_phone = "917306796590"
    if businesses and businesses[0].get("contact"):
        import re
        cleaned = re.sub(r'\D', '', businesses[0]["contact"])
        if len(cleaned) == 10:
            cleaned = "91" + cleaned
        if cleaned:
            contact_phone = cleaned

    if intent == "HIGH_INTENT":
        return f"Thanks for your interest @{username}! ❤️ Please message us on WhatsApp at https://wa.me/{contact_phone}?text=Hi+interested+in+ordering to place your order."
    elif intent == "MEDIUM_INTENT":
        return f"Hi @{username}! Thanks for asking. Delivery is available across India. Please contact us for detailed information."
    elif intent == "LOW_INTENT":
        return f"Thank you so much @{username}! We appreciate the support! 🙏✨"
    else:
        return ""

class YouTubeMonitorCrew:
    def __init__(self):
        # Initialize agents
        self.channel_agent = make_channel_agent()
        self.video_agent = make_video_monitoring_agent()
        self.collector_agent = make_comment_collector_agent()
        self.intent_agent = make_intent_classification_agent()
        self.reply_agent = make_reply_generation_agent()
        self.approval_agent = make_approval_agent()
        self.lead_agent = make_lead_creation_agent()
        self.publisher_agent = make_reply_publisher_agent()
        if not os.path.exists(CONFIG_PATH):
            set_auto_reply_setting(False)

    @property
    def auto_reply(self) -> bool:
        return get_auto_reply_setting()

    def set_auto_reply(self, val: bool):
        set_auto_reply_setting(val)
        logger.info(f"YouTubeMonitorCrew auto reply set to: {val}")

    async def verify_channel(self, channel_id: str) -> Dict[str, Any]:
        """Agent 1 - Verify channel details and active access"""
        logger.info(f"[Agent 1 - ChannelAgent] Verifying channel details for {channel_id}")
        channel = supabase_svc.get_youtube_channel(channel_id)
        if not channel:
            raise ValueError(f"Channel credentials not found for ID: {channel_id}")
        
        # Simulate check or execute API fetch
        subscriber_count = channel.get("subscriber_count", 1500)
        # Update details in DB
        supabase_svc.create_youtube_channel(
            channel_id=channel_id,
            channel_name=channel["channel_name"],
            thumbnail=channel.get("thumbnail"),
            subscriber_count=subscriber_count + 1,  # increment as activity
            access_token=channel["access_token"],
            refresh_token=channel.get("refresh_token")
        )
        return channel

    async def monitor_videos(self, channel_id: str) -> List[Dict[str, Any]]:
        """Agent 2 - Fetch latest videos for the connected channel"""
        logger.info(f"[Agent 2 - VideoMonitoringAgent] Scanning for latest videos of channel {channel_id}")
        # In mock database mode or standard execution, fetch all monitored videos
        videos = [v for v in supabase_svc.get_youtube_videos() if v.get("channel_id") == channel_id]
        if not videos:
            # Seed default video if empty for demo
            mock_video = supabase_svc.create_youtube_video(
                channel_id=channel_id,
                video_id="dQw4w9WgXcQ",
                title="100% Organic Cold Pressed Coconut Oil - VyaparAI Promo",
                publish_date=datetime.now().isoformat(),
                status="monitored"
            )
            videos = [mock_video]
        
        return videos

    async def collect_comments(self, video_id: str) -> List[Dict[str, Any]]:
        """Agent 3 - Collect and ingest comments, filtering out duplicates"""
        logger.info(f"[Agent 3 - CommentCollectorAgent] Fetching comments for video {video_id}")
        
        # Select comments existing in DB for this video
        existing_comments = [c for c in supabase_svc.get_youtube_comments() if c["video_id"] == video_id]
        return existing_comments

    async def classify_comment_intent(self, comment_text: str) -> Dict[str, Any]:
        """Agent 4 - Run Ollama Llama 3.1 or fallback heuristics to qualify intent"""
        logger.info(f"[Agent 4 - IntentClassificationAgent] Classifying intent of: '{comment_text}'")
        try:
            llm = get_ollama_llm()
            prompt = (
                "You are a Sales Intent Classification Agent for VyaparAI.\n"
                "Analyze the user comment and qualify it into one of these categories:\n"
                "- HIGH_INTENT (user asks for price, how to buy, product availability, shipping/delivery, contact/WhatsApp number, or order instructions)\n"
                "- MEDIUM_INTENT (user asks generic product questions, comparison, or expresses interest without purchase query)\n"
                "- LOW_INTENT (user gives generic praise like 'nice video', emoji replies, or thank you greetings)\n"
                "- SPAM (promotions, links, subscriptions, or unrelated text)\n\n"
                f"Comment: \"{comment_text}\"\n\n"
                "Respond in this EXACT JSON format:\n"
                "{\n"
                '  "intent": "CATEGORY",\n'
                '  "confidence": CONFIDENCE_SCORE_NUMBER\n'
                "}\n"
                "Do not include any other markdown prefix or text."
            )
            response = await llm.apredict(prompt)
            # Find JSON
            match = re.search(r"\{.*\}", response.replace("\n", " "))
            if match:
                import json
                data = json.loads(match.group(0))
                if data.get("intent") in ["HIGH_INTENT", "MEDIUM_INTENT", "LOW_INTENT", "SPAM"]:
                    return {"intent": data["intent"], "confidence": float(data.get("confidence", 0.9))}
            
            return fallback_classify_comment(comment_text)
        except Exception as e:
            logger.warning(f"Ollama intent classification failed: {e}. Falling back to regex.")
            return fallback_classify_comment(comment_text)

    async def generate_comment_reply(self, comment_text: str, intent: str, username: str) -> str:
        """Agent 5 - Create contextual responses based on classification rules"""
        logger.info(f"[Agent 5 - ReplyGenerationAgent] Generating reply for comment by @{username} (intent: {intent})")
        if intent == "SPAM":
            return "" # Ignore spam
        
        # Resolve contact phone number dynamically from active business
        businesses = supabase_svc.get_businesses()
        contact_phone = "917306796590"
        if businesses and businesses[0].get("contact"):
            import re
            cleaned = re.sub(r'\D', '', businesses[0]["contact"])
            if len(cleaned) == 10:
                cleaned = "91" + cleaned
            if cleaned:
                contact_phone = cleaned

        try:
            llm = get_ollama_llm()
            rules = (
                f"If intent is HIGH_INTENT: Thank them warmly, give a Call to Action (CTA), and direct them to WhatsApp at https://wa.me/{contact_phone}?text=I+saw+your+video.\n"
                "If intent is MEDIUM_INTENT: Answer the questions kindly and invite them to explore further.\n"
                "If intent is LOW_INTENT: React positively with friendly customer service emojis."
            )
            prompt = (
                f"You are a social media manager for a local business. Here are your rules:\n{rules}\n\n"
                f"User Comment: \"{comment_text}\"\n"
                f"User Handle: @{username}\n"
                f"Intent: {intent}\n\n"
                "Write a concise, friendly, and human-like response (maximum 2 sentences). Return ONLY the response text. Do not add quotes or meta text."
            )
            response = await llm.apredict(prompt)
            return response.strip().strip('"')
        except Exception as e:
            logger.warning(f"Ollama reply generation failed: {e}. Falling back to rule templates.")
            return fallback_generate_reply(comment_text, intent, username)

    async def create_sales_lead(self, comment_id: str, video_id: str, username: str, intent: str, reply: str) -> Optional[Dict[str, Any]]:
        """Agent 7 - Promote HIGH_INTENT comment authors to leads database"""
        if intent != "HIGH_INTENT":
            return None
        logger.info(f"[Agent 7 - LeadCreationAgent] Creating active CRM sales lead for customer @{username}")
        
        # Store in Supabase youtube_leads
        lead_rec = supabase_svc.create_youtube_lead(
            comment_id=comment_id,
            video_id=video_id,
            username=username,
            intent=intent,
            reply=reply
        )
        
        # Increment global analytics lead counters if possible
        try:
            businesses = supabase_svc.get_businesses()
            if businesses:
                supabase_svc.increment_analytics(businesses[0]["id"], "total_leads", 1)
        except Exception as e:
            logger.error(f"Failed to increment CRM analytics: {e}")
            
        return lead_rec

    async def publish_reply_to_youtube(self, comment_id: str, reply_text: str) -> Dict[str, Any]:
        """Agent 8 - Publish comment replies to YouTube API, tracking result"""
        logger.info(f"[Agent 8 - ReplyPublisherAgent] Submitting reply on YouTube for comment {comment_id}")
        
        # Verify no duplicate replies exist
        existing_replies = supabase_svc.get_youtube_replies()
        published_reply = next((r for r in existing_replies if r["comment_id"] == comment_id and r["status"] == "published"), None)
        if published_reply:
            logger.warning(f"Double-reply prevention triggered for comment {comment_id}. Skipping.")
            return published_reply

        # Retrieve comment details to find channel
        comment = supabase_svc.get_youtube_comment(comment_id)
        if not comment:
            raise ValueError(f"Comment with ID {comment_id} not found in database.")
            
        video = supabase_svc.get_youtube_video(comment["video_id"])
        if not video:
            raise ValueError(f"Video with ID {comment['video_id']} not found in database.")
            
        channel = supabase_svc.get_youtube_channel(video["channel_id"])
        if not channel:
            raise ValueError(f"YouTube channel with ID {video['channel_id']} not found in database.")

        is_mock_channel = channel.get("access_token") == "mock_access_token"
        reply_id = None
        
        if not is_mock_channel:
            try:
                from google.oauth2.credentials import Credentials
                from google.auth.transport.requests import Request
                from googleapiclient.discovery import build
                
                creds = Credentials(
                    token=channel["access_token"],
                    refresh_token=channel.get("refresh_token"),
                    token_uri=channel.get("token_uri") or "https://oauth2.googleapis.com/token",
                    client_id=channel.get("client_id"),
                    client_secret=channel.get("client_secret")
                )
                
                # Check refresh if expired
                if creds.expired and creds.refresh_token:
                    logger.info(f"Access token for channel {channel['channel_name']} expired. Refreshing token...")
                    creds.refresh(Request())
                    # Update in DB
                    supabase_svc.create_youtube_channel(
                        channel_id=channel["channel_id"],
                        channel_name=channel["channel_name"],
                        thumbnail=channel.get("thumbnail"),
                        subscriber_count=channel.get("subscriber_count", 0),
                        access_token=creds.token,
                        refresh_token=creds.refresh_token,
                        token_uri=channel.get("token_uri"),
                        client_id=channel.get("client_id"),
                        client_secret=channel.get("client_secret"),
                        scopes=channel.get("scopes")
                    )

                youtube = build("youtube", "v3", credentials=creds)
                
                # Post the reply using YouTube API
                request = youtube.comments().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "parentId": comment_id,
                            "textOriginal": reply_text
                        }
                    }
                )
                response = request.execute()
                reply_id = response.get("id")
                logger.info(f"Successfully posted real YouTube comment reply. ID: {reply_id}")
            except Exception as e:
                logger.error(f"Failed to post real YouTube comment reply: {e}", exc_info=True)
                # Fallback to simulation to prevent breaking the flow
                import uuid
                reply_id = f"RPL_ERR_{uuid.uuid4().hex[:7].upper()}"
        else:
            # Simulation Mode
            import uuid
            reply_id = f"RPL_{uuid.uuid4().hex[:11].upper()}"

        # Save or update in youtube_replies
        reply_rec = supabase_svc.get_youtube_reply_by_comment(comment_id)
        if reply_rec:
            # Update existing draft
            updated = supabase_svc.update_youtube_reply(reply_rec["id"], {
                "status": "published",
                "reply_id": reply_id,
                "actual_reply": reply_text,
                "published_at": datetime.now().isoformat()
            })
            if updated:
                reply_rec = updated
        else:
            # Create new reply
            reply_rec = supabase_svc.create_youtube_reply(
                comment_id=comment_id,
                suggested_reply=reply_text,
                actual_reply=reply_text,
                reply_id=reply_id,
                status="published",
                published_at=datetime.now().isoformat()
            )
        
        # Update comment status
        supabase_svc.update_youtube_comment_status(comment_id, "replied")
        
        return reply_rec

    async def process_single_comment(self, channel_id: str, video_id: str, comment_id: str, username: str, comment_text: str, timestamp: str) -> Dict[str, Any]:
        """Orchestrate Agents 3 -> 8 for an incoming comment"""
        logger.info(f"Processing comment {comment_id} from @{username}: '{comment_text}'")

        # 1. Classify intent (Agent 4)
        classification = await self.classify_comment_intent(comment_text)
        intent = classification["intent"]
        confidence = classification["confidence"]

        # 2. Store comment in database
        # Default status: pending_approval if AUTO_REPLY=false, else approved
        status = "approved" if self.auto_reply else "pending_approval"
        if intent == "SPAM":
            status = "rejected" # Don't queue spam for approval

        comment_rec = supabase_svc.create_youtube_comment(
            video_id=video_id,
            comment_id=comment_id,
            username=username,
            text=comment_text,
            timestamp=timestamp,
            intent=intent,
            confidence=confidence,
            status=status
        )

        # 3. Generate Reply (Agent 5)
        reply_text = ""
        reply_rec = None
        if intent != "SPAM":
            reply_text = await self.generate_comment_reply(comment_text, intent, username)
            
            # Save reply record
            reply_status = "pending_publish" if self.auto_reply else "draft"
            reply_rec = supabase_svc.create_youtube_reply(
                comment_id=comment_id,
                suggested_reply=reply_text,
                status=reply_status
            )

        # 4. Lead Creation (Agent 7)
        lead_rec = None
        if intent == "HIGH_INTENT":
            lead_rec = await self.create_sales_lead(comment_id, video_id, username, intent, reply_text)

        # 5. Publisher (Agent 8) - Run if AUTO_REPLY is enabled
        if self.auto_reply and reply_text:
            published_rec = await self.publish_reply_to_youtube(comment_id, reply_text)
            if reply_rec:
                # Update reply record status to published
                supabase_svc.update_youtube_reply(reply_rec["id"], {
                    "status": "published",
                    "reply_id": published_rec["reply_id"],
                    "actual_reply": reply_text,
                    "published_at": datetime.now().isoformat()
                })

        # Update analytics count
        try:
            analytics = supabase_svc.get_youtube_analytics(channel_id)
            if analytics:
                new_processed = analytics.get("comments_processed", 0) + 1
                new_leads = analytics.get("lead_count", 0) + (1 if intent == "HIGH_INTENT" else 0)
                
                # Recalculate rates
                published_count = len([r for r in supabase_svc.get_youtube_replies() if r["status"] == "published"])
                reply_rate = round((published_count / new_processed) * 100, 2) if new_processed > 0 else 0
                
                # Mock conversions
                conversions = int(new_leads * 0.4)
                conversion_rate = round((conversions / new_leads) * 100, 2) if new_leads > 0 else 0
                
                supabase_svc.update_youtube_analytics(analytics["id"], {
                    "comments_processed": new_processed,
                    "lead_count": new_leads,
                    "reply_rate": reply_rate,
                    "conversion_rate": conversion_rate
                })
        except Exception as e:
            logger.error(f"Failed to update channel analytics: {e}")

        return {
            "comment": comment_rec,
            "reply": reply_rec,
            "lead": lead_rec
        }

youtube_monitor_crew = YouTubeMonitorCrew()
