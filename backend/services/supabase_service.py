# backend/services/supabase_service.py
import logging
import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from backend.database.connection import db_conn

logger = logging.getLogger("vyaparai.supabase_service")

import os
import json

MOCK_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "mock_db.json")

# In-Memory database for mock operations
MOCK_DB: Dict[str, List[Dict[str, Any]]] = {
    "businesses": [],
    "products": [],
    "keywords": [],
    "scripts": [],
    "thumbnails": [],
    "translations": [],
    "voiceovers": [],
    "videos": [],
    "comments": [],
    "leads": [],
    "conversations": [],
    "orders": [],
    "analytics": [],
    "youtube_channels": [],
    "youtube_videos": [],
    "youtube_comments": [],
    "youtube_replies": [],
    "youtube_leads": [],
    "youtube_analytics": []
}

def load_mock_db():
    global MOCK_DB
    if os.path.exists(MOCK_DB_PATH):
        try:
            with open(MOCK_DB_PATH, "r", encoding="utf-8") as f:
                MOCK_DB = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load mock DB: {e}")

def save_mock_db():
    try:
        os.makedirs(os.path.dirname(MOCK_DB_PATH), exist_ok=True)
        with open(MOCK_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(MOCK_DB, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save mock DB: {e}")

load_mock_db()

class SupabaseService:
    def __init__(self):
        self.is_mock = db_conn.is_mock
        self.client = db_conn.client

    def _insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        if "created_at" not in data:
            data["created_at"] = datetime.now().isoformat()
            
        if self.is_mock:
            MOCK_DB[table].append(data)
            logger.info(f"[MOCK DB] Inserted into {table}: {data['id']}")
            save_mock_db()
            return data
        else:
            try:
                res = self.client.table(table).insert(data).execute()
                if res.data:
                    return res.data[0]
                return data
            except Exception as e:
                logger.error(f"Supabase error inserting into {table}: {e}")
                MOCK_DB[table].append(data)
                save_mock_db()
                return data

    def _select_all(self, table: str) -> List[Dict[str, Any]]:
        if self.is_mock:
            return MOCK_DB[table]
        else:
            try:
                res = self.client.table(table).select("*").execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Supabase error reading {table}: {e}")
                return MOCK_DB[table]

    def _select_one(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            for item in MOCK_DB[table]:
                if item.get("id") == record_id:
                    return item
            return None
        else:
            try:
                res = self.client.table(table).select("*").eq("id", record_id).execute()
                if res.data:
                    return res.data[0]
                return None
            except Exception as e:
                logger.error(f"Supabase error reading {table} with id {record_id}: {e}")
                for item in MOCK_DB[table]:
                    if item.get("id") == record_id:
                        return item
                return None

    def _update(self, table: str, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            for item in MOCK_DB[table]:
                if item.get("id") == record_id:
                    item.update(data)
                    if "updated_at" in item or table == "conversations":
                        item["updated_at"] = datetime.now().isoformat()
                    logger.info(f"[MOCK DB] Updated {table}: {record_id}")
                    save_mock_db()
                    return item
            return None
        else:
            try:
                res = self.client.table(table).update(data).eq("id", record_id).execute()
                if res.data:
                    return res.data[0]
                return None
            except Exception as e:
                logger.error(f"Supabase error updating {table} with id {record_id}: {e}")
                for item in MOCK_DB[table]:
                    if item.get("id") == record_id:
                        item.update(data)
                        save_mock_db()
                        return item
                return None

    # --- Businesses ---
    def create_business(self, name: str, location: str, contact: str = None, industry: str = None) -> Dict[str, Any]:
        data = {
            "name": name,
            "location": location,
            "contact": contact,
            "industry": industry
        }
        return self._insert("businesses", data)

    def get_businesses(self) -> List[Dict[str, Any]]:
        return self._select_all("businesses")

    def get_business(self, business_id: str) -> Optional[Dict[str, Any]]:
        return self._select_one("businesses", business_id)

    # --- Products ---
    def create_product(self, business_id: str, name: str, description: str, price: float, images: List[str] = None) -> Dict[str, Any]:
        data = {
            "business_id": business_id,
            "name": name,
            "description": description,
            "price": price,
            "images": images or []
        }
        return self._insert("products", data)

    def get_products(self) -> List[Dict[str, Any]]:
        return self._select_all("products")

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        return self._select_one("products", product_id)

    # --- Keywords ---
    def create_keywords(self, product_id: str, primary_kw: List[str], secondary_kw: List[str], long_tail_kw: List[str], intent_kw: List[str], regional_kw: List[str]) -> Dict[str, Any]:
        data = {
            "product_id": product_id,
            "primary_keywords": primary_kw,
            "secondary_keywords": secondary_kw,
            "long_tail_keywords": long_tail_kw,
            "intent_keywords": intent_kw,
            "regional_keywords": regional_kw
        }
        return self._insert("keywords", data)

    def get_keywords_by_product(self, product_id: str) -> List[Dict[str, Any]]:
        if self.is_mock:
            return [k for k in MOCK_DB["keywords"] if k.get("product_id") == product_id]
        else:
            try:
                res = self.client.table("keywords").select("*").eq("product_id", product_id).execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Supabase error: {e}")
                return [k for k in MOCK_DB["keywords"] if k.get("product_id") == product_id]

    # --- Scripts (Expanded) ---
    def create_script(
        self, 
        product_id: str, 
        title: str, 
        hook: str, 
        script_text: str, 
        scene_breakdown: List[Dict[str, Any]], 
        caption_timeline: List[Dict[str, Any]], 
        thumbnail_text: str, 
        seo_description: str, 
        hashtags: List[str],
        version: int = 1
    ) -> Dict[str, Any]:
        data = {
            "product_id": product_id,
            "title": title,
            "hook": hook,
            "script_text": script_text,
            "scene_breakdown": scene_breakdown,
            "caption_timeline": caption_timeline,
            "thumbnail_text": thumbnail_text,
            "seo_description": seo_description,
            "hashtags": hashtags,
            "version": version,
            "status": "draft"
        }
        return self._insert("scripts", data)

    def get_script(self, script_id: str) -> Optional[Dict[str, Any]]:
        return self._select_one("scripts", script_id)

    def get_scripts_by_product(self, product_id: str) -> List[Dict[str, Any]]:
        if self.is_mock:
            return [s for s in MOCK_DB["scripts"] if s.get("product_id") == product_id]
        else:
            try:
                res = self.client.table("scripts").select("*").eq("product_id", product_id).execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Supabase error: {e}")
                return [s for s in MOCK_DB["scripts"] if s.get("product_id") == product_id]

    def update_script_status(self, script_id: str, status: str) -> Optional[Dict[str, Any]]:
        return self._update("scripts", script_id, {"status": status})

    # --- Thumbnails (New) ---
    def create_thumbnail(self, script_id: str, layout: str, text: str, prompt: str, image_url: str = None) -> Dict[str, Any]:
        data = {
            "script_id": script_id,
            "layout": layout,
            "text": text,
            "prompt": prompt,
            "image_url": image_url
        }
        return self._insert("thumbnails", data)

    def get_thumbnails_by_script(self, script_id: str) -> List[Dict[str, Any]]:
        if self.is_mock:
            return [t for t in MOCK_DB["thumbnails"] if t.get("script_id") == script_id]
        else:
            try:
                res = self.client.table("thumbnails").select("*").eq("script_id", script_id).execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Supabase error: {e}")
                return [t for t in MOCK_DB["thumbnails"] if t.get("script_id") == script_id]

    # --- Translations ---
    def create_translation(self, script_id: str, language: str, youtube: str, reel: str, whatsapp: str, google: str) -> Dict[str, Any]:
        data = {
            "script_id": script_id,
            "language": language,
            "youtube_script": youtube,
            "reel_script": reel,
            "whatsapp_post": whatsapp,
            "google_business_post": google
        }
        return self._insert("translations", data)

    def get_translations_by_script(self, script_id: str) -> List[Dict[str, Any]]:
        if self.is_mock:
            return [t for t in MOCK_DB["translations"] if t.get("script_id") == script_id]
        else:
            try:
                res = self.client.table("translations").select("*").eq("script_id", script_id).execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Supabase error: {e}")
                return [t for t in MOCK_DB["translations"] if t.get("script_id") == script_id]

    def get_translation(self, translation_id: str) -> Optional[Dict[str, Any]]:
        return self._select_one("translations", translation_id)

    # --- Voiceovers ---
    def create_voiceover(self, translation_id: str, audio_url: str, duration: float) -> Dict[str, Any]:
        data = {
            "translation_id": translation_id,
            "audio_url": audio_url,
            "duration": duration
        }
        return self._insert("voiceovers", data)

    # --- Videos (Expanded with YouTube Publishing info) ---
    def create_video(self, voiceover_id: str, video_url: str, status: str = "draft", approval_status: str = "pending", version: int = 1) -> Dict[str, Any]:
        data = {
            "voiceover_id": voiceover_id,
            "video_url": video_url,
            "status": status,
            "approval_status": approval_status,
            "version": version,
            "youtube_id": None,
            "youtube_url": None,
            "engagement_count": 0
        }
        return self._insert("videos", data)

    def get_videos(self) -> List[Dict[str, Any]]:
        return self._select_all("videos")

    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        return self._select_one("videos", video_id)

    def update_video_approval(self, video_id: str, approval_status: str) -> Optional[Dict[str, Any]]:
        return self._update("videos", video_id, {"approval_status": approval_status})

    def update_video_status(self, video_id: str, status: str) -> Optional[Dict[str, Any]]:
        return self._update("videos", video_id, {"status": status})

    def update_video_publish_info(self, video_id: str, youtube_id: str, youtube_url: str) -> Optional[Dict[str, Any]]:
        return self._update("videos", video_id, {"youtube_id": youtube_id, "youtube_url": youtube_url})

    # --- Comments ---
    def create_comment(self, video_id: str, username: str, comment_text: str, intent_class: str = "SPAM") -> Dict[str, Any]:
        data = {
            "video_id": video_id,
            "username": username,
            "comment_text": comment_text,
            "intent_class": intent_class,
            "response_sent": False
        }
        return self._insert("comments", data)

    def get_comments_by_video(self, video_id: str) -> List[Dict[str, Any]]:
        if self.is_mock:
            return [c for c in MOCK_DB["comments"] if c.get("video_id") == video_id]
        else:
            try:
                res = self.client.table("comments").select("*").eq("video_id", video_id).execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Supabase error: {e}")
                return [c for c in MOCK_DB["comments"] if c.get("video_id") == video_id]

    # --- Leads ---
    def create_lead(self, business_id: str, username: str, language: str = None, intent: str = "MEDIUM_INTENT", comment_id: str = None) -> Dict[str, Any]:
        data = {
            "business_id": business_id,
            "comment_id": comment_id,
            "username": username,
            "language": language,
            "intent": intent,
            "status": "new"
        }
        return self._insert("leads", data)

    def get_leads(self) -> List[Dict[str, Any]]:
        return self._select_all("leads")

    def update_lead_status(self, lead_id: str, status: str) -> Optional[Dict[str, Any]]:
        return self._update("leads", lead_id, {"status": status})

    # --- Conversations ---
    def create_conversation(self, lead_id: str, state: str = "WELCOME", history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = {
            "lead_id": lead_id,
            "state": state,
            "history": history or []
        }
        return self._insert("conversations", data)

    def get_conversation_by_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            for c in MOCK_DB["conversations"]:
                if c.get("lead_id") == lead_id:
                    return c
            return None
        else:
            try:
                res = self.client.table("conversations").select("*").eq("lead_id", lead_id).execute()
                if res.data:
                    return res.data[0]
                return None
            except Exception as e:
                logger.error(f"Supabase error: {e}")
                for c in MOCK_DB["conversations"]:
                    if c.get("lead_id") == lead_id:
                        return c
                return None

    def update_conversation(self, conversation_id: str, state: str, history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return self._update("conversations", conversation_id, {"state": state, "history": history})

    # --- Orders ---
    def create_order(self, lead_id: str, product_id: str, amount: float, address: str = None, status: str = "pending") -> Dict[str, Any]:
        data = {
            "lead_id": lead_id,
            "product_id": product_id,
            "amount": amount,
            "status": status,
            "address": address,
            "payment_method": "upi",
            "transaction_id": None
        }
        return self._insert("orders", data)

    def get_orders(self) -> List[Dict[str, Any]]:
        return self._select_all("orders")

    def update_order_status(self, order_id: str, status: str, transaction_id: str = None) -> Optional[Dict[str, Any]]:
        update_data = {"status": status}
        if transaction_id:
            update_data["transaction_id"] = transaction_id
        return self._update("orders", order_id, update_data)

    # --- Analytics ---
    def get_analytics(self, business_id: str) -> List[Dict[str, Any]]:
        if self.is_mock:
            rows = [a for a in MOCK_DB["analytics"] if a.get("business_id") == business_id]
            if not rows:
                today_str = date.today().isoformat()
                row = {
                    "id": str(uuid.uuid4()),
                    "business_id": business_id,
                    "date": today_str,
                    "total_leads": len([l for l in MOCK_DB["leads"] if l.get("business_id") == business_id]),
                    "total_conversions": len([o for o in MOCK_DB["orders"] if o.get("status") in ["paid", "completed"]]),
                    "videos_generated": len(MOCK_DB["videos"]),
                    "engagement_rate": 4.5,
                    "created_at": datetime.now().isoformat()
                }
                MOCK_DB["analytics"].append(row)
                save_mock_db()
                rows = [row]
            return rows
        else:
            try:
                res = self.client.table("analytics").select("*").eq("business_id", business_id).execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Supabase error: {e}")
                return [a for a in MOCK_DB["analytics"] if a.get("business_id") == business_id]

    def increment_analytics(self, business_id: str, metric: str, amount: int = 1):
        today_str = date.today().isoformat()
        if self.is_mock:
            row = None
            for r in MOCK_DB["analytics"]:
                if r.get("business_id") == business_id and r.get("date") == today_str:
                    row = r
                    break
            if not row:
                row = {
                    "id": str(uuid.uuid4()),
                    "business_id": business_id,
                    "date": today_str,
                    "total_leads": 0,
                    "total_conversions": 0,
                    "videos_generated": 0,
                    "engagement_rate": 5.0,
                    "created_at": datetime.now().isoformat()
                }
                MOCK_DB["analytics"].append(row)
            if metric in row:
                row[metric] += amount
            save_mock_db()
        else:
            try:
                res = self.client.table("analytics").select("*").eq("business_id", business_id).eq("date", today_str).execute()
                if res.data:
                    current = res.data[0]
                    new_val = current.get(metric, 0) + amount
                    self.client.table("analytics").update({metric: new_val}).eq("id", current["id"]).execute()
                else:
                    new_row = {
                        "business_id": business_id,
                        "date": today_str,
                        metric: amount
                    }
                    self.client.table("analytics").insert(new_row).execute()
            except Exception as e:
                logger.error(f"Failed to increment analytics: {e}")

    # --- YouTube Channels ---
    def create_youtube_channel(self, channel_id: str, channel_name: str, thumbnail: str, subscriber_count: int, access_token: str, refresh_token: str, token_uri: str = None, client_id: str = None, client_secret: str = None, scopes: List[str] = None) -> Dict[str, Any]:
        data = {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "thumbnail": thumbnail,
            "subscriber_count": subscriber_count,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_uri": token_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "scopes": scopes or []
        }
        if self.is_mock:
            MOCK_DB["youtube_channels"] = [c for c in MOCK_DB["youtube_channels"] if c.get("channel_id") != channel_id]
        else:
            try:
                self.client.table("youtube_channels").delete().eq("channel_id", channel_id).execute()
            except Exception as e:
                logger.error(f"Failed to delete duplicate youtube channel: {e}")
        return self._insert("youtube_channels", data)

    def get_youtube_channels(self) -> List[Dict[str, Any]]:
        return self._select_all("youtube_channels")

    def get_youtube_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            for item in MOCK_DB["youtube_channels"]:
                if item.get("channel_id") == channel_id:
                    return item
            return None
        else:
            try:
                res = self.client.table("youtube_channels").select("*").eq("channel_id", channel_id).execute()
                return res.data[0] if res.data else None
            except Exception as e:
                logger.error(f"Failed to get youtube channel: {e}")
                return None

    def delete_youtube_channel(self, channel_id: str) -> bool:
        if self.is_mock:
            MOCK_DB["youtube_channels"] = [c for c in MOCK_DB["youtube_channels"] if c.get("channel_id") != channel_id]
            MOCK_DB["youtube_videos"] = [v for v in MOCK_DB["youtube_videos"] if v.get("channel_id") != channel_id]
            MOCK_DB["youtube_analytics"] = [a for a in MOCK_DB["youtube_analytics"] if a.get("channel_id") != channel_id]
            logger.info(f"[MOCK DB] Disconnected YouTube channel: {channel_id}")
            save_mock_db()
            return True
        else:
            try:
                self.client.table("youtube_channels").delete().eq("channel_id", channel_id).execute()
                return True
            except Exception as e:
                logger.error(f"Failed to delete channel: {e}")
                return False

    # --- YouTube Videos ---
    def create_youtube_video(self, channel_id: str, video_id: str, title: str, publish_date: str, status: str = "monitored") -> Dict[str, Any]:
        data = {
            "channel_id": channel_id,
            "video_id": video_id,
            "title": title,
            "publish_date": publish_date,
            "status": status
        }
        return self._insert("youtube_videos", data)

    def get_youtube_videos(self) -> List[Dict[str, Any]]:
        return self._select_all("youtube_videos")

    def get_youtube_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            for item in MOCK_DB["youtube_videos"]:
                if item.get("video_id") == video_id:
                    return item
            return None
        else:
            try:
                res = self.client.table("youtube_videos").select("*").eq("video_id", video_id).execute()
                return res.data[0] if res.data else None
            except Exception as e:
                logger.error(f"Failed to get youtube video: {e}")
                return None

    def delete_youtube_video(self, video_id: str) -> bool:
        if self.is_mock:
            MOCK_DB["youtube_videos"] = [v for v in MOCK_DB["youtube_videos"] if v.get("video_id") != video_id]
            logger.info(f"[MOCK DB] Removed deleted YouTube video: {video_id}")
            save_mock_db()
            return True
        else:
            try:
                self.client.table("youtube_videos").delete().eq("video_id", video_id).execute()
                return True
            except Exception as e:
                logger.error(f"Failed to delete youtube video: {e}")
                return False

    # --- YouTube Comments ---
    def create_youtube_comment(self, video_id: str, comment_id: str, username: str, text: str, timestamp: str, intent: str = "SPAM", confidence: float = 1.0, status: str = "pending_approval") -> Dict[str, Any]:
        data = {
            "video_id": video_id,
            "comment_id": comment_id,
            "username": username,
            "text": text,
            "timestamp": timestamp,
            "intent": intent,
            "confidence": confidence,
            "status": status
        }
        return self._insert("youtube_comments", data)

    def get_youtube_comments(self) -> List[Dict[str, Any]]:
        return self._select_all("youtube_comments")

    def get_youtube_comment(self, comment_id: str) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            for item in MOCK_DB["youtube_comments"]:
                if item.get("comment_id") == comment_id:
                    return item
            return None
        else:
            try:
                res = self.client.table("youtube_comments").select("*").eq("comment_id", comment_id).execute()
                return res.data[0] if res.data else None
            except Exception as e:
                logger.error(f"Failed to get youtube comment: {e}")
                return None

    def update_youtube_comment_status(self, comment_id: str, status: str) -> Optional[Dict[str, Any]]:
        comment = self.get_youtube_comment(comment_id)
        if not comment:
            return None
        return self._update("youtube_comments", comment["id"], {"status": status})

    def update_youtube_comment_intent(self, comment_id: str, intent: str, confidence: float) -> Optional[Dict[str, Any]]:
        comment = self.get_youtube_comment(comment_id)
        if not comment:
            return None
        return self._update("youtube_comments", comment["id"], {"intent": intent, "confidence": confidence})

    # --- YouTube Replies ---
    def create_youtube_reply(self, comment_id: str, suggested_reply: str, actual_reply: str = None, reply_id: str = None, status: str = "draft", published_at: str = None) -> Dict[str, Any]:
        data = {
            "comment_id": comment_id,
            "suggested_reply": suggested_reply,
            "actual_reply": actual_reply,
            "reply_id": reply_id,
            "status": status,
            "published_at": published_at
        }
        return self._insert("youtube_replies", data)

    def get_youtube_replies(self) -> List[Dict[str, Any]]:
        return self._select_all("youtube_replies")

    def get_youtube_reply_by_comment(self, comment_id: str) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            for item in MOCK_DB["youtube_replies"]:
                if item.get("comment_id") == comment_id:
                    return item
            return None
        else:
            try:
                res = self.client.table("youtube_replies").select("*").eq("comment_id", comment_id).execute()
                return res.data[0] if res.data else None
            except Exception as e:
                logger.error(f"Failed to get youtube reply: {e}")
                return None

    def update_youtube_reply(self, reply_db_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._update("youtube_replies", reply_db_id, data)

    # --- YouTube Leads ---
    def create_youtube_lead(self, comment_id: str, video_id: str, username: str, intent: str = "HIGH_INTENT", reply: str = None, autopilot: bool = True) -> Dict[str, Any]:
        data = {
            "comment_id": comment_id,
            "video_id": video_id,
            "username": username,
            "intent": intent,
            "reply": reply,
            "autopilot": autopilot
        }
        return self._insert("youtube_leads", data)

    def get_youtube_leads(self) -> List[Dict[str, Any]]:
        return self._select_all("youtube_leads")

    def update_youtube_lead_autopilot(self, lead_id: str, autopilot: bool) -> Optional[Dict[str, Any]]:
        return self._update("youtube_leads", lead_id, {"autopilot": autopilot})

    # --- YouTube Analytics ---
    def create_youtube_analytics(self, channel_id: str, comments_processed: int = 0, reply_rate: float = 0.0, lead_count: int = 0, conversion_rate: float = 0.0, top_videos: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = {
            "channel_id": channel_id,
            "comments_processed": comments_processed,
            "reply_rate": reply_rate,
            "lead_count": lead_count,
            "conversion_rate": conversion_rate,
            "top_videos": top_videos or []
        }
        return self._insert("youtube_analytics", data)

    def get_youtube_analytics(self, channel_id: str) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            for item in MOCK_DB["youtube_analytics"]:
                if item.get("channel_id") == channel_id:
                    return item
            default_row = {
                "id": str(uuid.uuid4()),
                "channel_id": channel_id,
                "comments_processed": 12,
                "reply_rate": 75.0,
                "lead_count": 5,
                "conversion_rate": 41.6,
                "top_videos": [
                    {"video_id": "PuCb1JHpBkM", "title": "Cardamom Export Launch Campaign", "comments": 8, "leads": 4},
                    {"video_id": "dQw4w9WgXcQ", "title": "Coconut Oil Regional Promo Clip", "comments": 4, "leads": 1}
                ],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            MOCK_DB["youtube_analytics"].append(default_row)
            return default_row
        else:
            try:
                res = self.client.table("youtube_analytics").select("*").eq("channel_id", channel_id).execute()
                return res.data[0] if res.data else None
            except Exception as e:
                logger.error(f"Failed to get youtube analytics: {e}")
                return None

    def update_youtube_analytics(self, analytics_db_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._update("youtube_analytics", analytics_db_id, data)

    # --- WhatsApp Chat History ---
    def get_whatsapp_messages(self, lead_id: str = None) -> List[Dict[str, Any]]:
        if self.is_mock:
            messages = MOCK_DB.get("whatsapp_messages", [])
            if lead_id:
                messages = [m for m in messages if m.get("lead_id") == lead_id]
            return messages
        else:
            try:
                query = self.client.table("whatsapp_messages").select("*")
                if lead_id:
                    query = query.eq("lead_id", lead_id)
                res = query.execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Failed to fetch whatsapp messages: {e}")
                # Fallback to mock
                messages = MOCK_DB.get("whatsapp_messages", [])
                if lead_id:
                    messages = [m for m in messages if m.get("lead_id") == lead_id]
                return messages

    def create_whatsapp_message(self, lead_id: str, sender: str, text: str) -> Dict[str, Any]:
        data = {
            "id": str(uuid.uuid4()),
            "lead_id": lead_id,
            "sender": sender,  # "business" or "customer"
            "text": text,
            "created_at": datetime.now().isoformat()
        }
        if self.is_mock:
            if "whatsapp_messages" not in MOCK_DB:
                MOCK_DB["whatsapp_messages"] = []
            MOCK_DB["whatsapp_messages"].append(data)
            save_mock_db()
            return data
        else:
            try:
                res = self.client.table("whatsapp_messages").insert(data).execute()
                return res.data[0] if res.data else data
            except Exception as e:
                logger.error(f"Failed to insert whatsapp message: {e}")
                if "whatsapp_messages" not in MOCK_DB:
                    MOCK_DB["whatsapp_messages"] = []
                MOCK_DB["whatsapp_messages"].append(data)
                save_mock_db()
                return data

supabase_svc = SupabaseService()
