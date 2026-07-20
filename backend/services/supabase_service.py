# backend/services/supabase_service.py
import logging
import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from backend.database.connection import db_conn

logger = logging.getLogger("vyaparai.supabase_service")

import os
import json

MOCK_DB_PATH = os.path.expanduser("~/.vyapar_mock_db.json")
OLD_MOCK_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "mock_db.json")

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
    "youtube_analytics": [],
    "video_jobs": []
}

def load_mock_db():
    global MOCK_DB
    # Migrate old mock db if it exists and new one does not
    if not os.path.exists(MOCK_DB_PATH) and os.path.exists(OLD_MOCK_DB_PATH):
        try:
            import shutil
            shutil.copy2(OLD_MOCK_DB_PATH, MOCK_DB_PATH)
            logger.info(f"Migrated mock database from {OLD_MOCK_DB_PATH} to {MOCK_DB_PATH} successfully.")
        except Exception as migration_err:
            logger.error(f"Failed to migrate old mock db: {migration_err}")

    if os.path.exists(MOCK_DB_PATH):
        try:
            with open(MOCK_DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Merge loaded keys
                for k, v in data.items():
                    MOCK_DB[k] = v
        except Exception as e:
            logger.error(f"Failed to load mock DB: {e}")

    # Ensure keys exist
    for key in ["tenants", "whatsapp_instances", "conversations", "messages", "video_jobs"]:
        if key not in MOCK_DB:
            MOCK_DB[key] = []

def save_mock_db():
    try:
        os.makedirs(os.path.dirname(MOCK_DB_PATH), exist_ok=True)
        with open(MOCK_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(MOCK_DB, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save mock DB: {e}")

def fix_mock_db_links():
    global MOCK_DB
    import re
    public_url = os.getenv("PUBLIC_URL") or os.getenv("APP_BASE_URL") or "http://localhost:8000"
    if "host.docker.internal" in public_url:
        public_url = "http://localhost:8000"
    if not public_url.endswith("/"):
        public_url += "/"
        
    updated = False
    pattern = re.compile(r"https?://[^/]+/youtube/r/")
    
    if "youtube_replies" in MOCK_DB:
        for reply in MOCK_DB["youtube_replies"]:
            for key in ["suggested_reply", "actual_reply"]:
                val = reply.get(key)
                if val and isinstance(val, str):
                    if pattern.search(val):
                        new_val = pattern.sub(f"{public_url}youtube/r/", val)
                        if new_val != val:
                            reply[key] = new_val
                            updated = True
                            
    if updated:
        logger.info(f"Automatically corrected mock database links to use public URL: {public_url}")
        save_mock_db()

load_mock_db()
fix_mock_db_links()

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
        raw_products = self._select_all("products")
        seen_names = set()
        clean_products = []
        excluded_keywords = ["saree", "fabric", "clothing", "paint", "emulsion", "cardamom", "coconut", "oil"]
        for p in raw_products:
            pname = (p.get("name") or "").strip()
            pname_lower = pname.lower()
            # Filter out non-nursery test artifacts and empty items
            if not pname or any(kw in pname_lower for kw in excluded_keywords):
                continue
            if pname_lower not in seen_names:
                seen_names.add(pname_lower)
                clean_products.append(p)
        return clean_products

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
    def create_youtube_video(self, channel_id: str, video_id: str, title: str, publish_date: str, status: str = "monitored", auto_reply: bool = True) -> Dict[str, Any]:
        data = {
            "channel_id": channel_id,
            "video_id": video_id,
            "title": title,
            "publish_date": publish_date,
            "status": status,
            "auto_reply": auto_reply
        }
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        if "created_at" not in data:
            data["created_at"] = datetime.now().isoformat()
            
        if self.is_mock:
            # Check if video exists to update it, otherwise insert
            existing = self.get_youtube_video(video_id)
            if existing:
                existing.update(data)
                save_mock_db()
                return existing
            MOCK_DB["youtube_videos"].append(data)
            logger.info(f"[MOCK DB] Inserted into youtube_videos: {data['id']}")
            save_mock_db()
            return data
        else:
            try:
                res = self.client.table("youtube_videos").insert(data).execute()
                if res.data:
                    return res.data[0]
                return data
            except Exception as e:
                err_msg = str(e)
                if "auto_reply" in err_msg or "column" in err_msg:
                    logger.warning(
                        "Supabase error: youtube_videos table may be missing 'auto_reply' column. "
                        "Please execute this SQL migration in your Supabase SQL Editor:\n"
                        "ALTER TABLE youtube_videos ADD COLUMN IF NOT EXISTS auto_reply BOOLEAN DEFAULT true;\n"
                        f"Detailed error: {e}"
                    )
                    # Retry without auto_reply
                    data_fallback = dict(data)
                    data_fallback.pop("auto_reply", None)
                    try:
                        res = self.client.table("youtube_videos").insert(data_fallback).execute()
                        if res.data:
                            record = res.data[0]
                            record["auto_reply"] = auto_reply
                            return record
                    except Exception as fallback_e:
                        logger.error(f"Fallback insert also failed: {fallback_e}")
                
                # If everything else fails, fall back to mock
                logger.warning("Falling back to local in-memory DB for this video record.")
                MOCK_DB["youtube_videos"].append(data)
                save_mock_db()
                return data

    def get_youtube_videos(self) -> List[Dict[str, Any]]:
        videos = self._select_all("youtube_videos")
        for v in videos:
            if v.get("auto_reply") is None:
                v["auto_reply"] = True
            # Merge/fallback to local mock_db if status is missing (helps resolve missing column in Supabase)
            if v.get("status") is None:
                mock_v = next((mv for mv in MOCK_DB["youtube_videos"] if mv.get("video_id") == v.get("video_id")), None)
                v["status"] = mock_v.get("status") if (mock_v and mock_v.get("status") is not None) else "monitored"
        # Sort videos so that newly uploaded/added videos (newest publish_date or created_at) come to the top
        videos.sort(key=lambda x: x.get("publish_date") or x.get("created_at") or "", reverse=True)
        return videos

    def get_youtube_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        video = None
        if self.is_mock:
            for item in MOCK_DB["youtube_videos"]:
                if item.get("video_id") == video_id:
                    video = item
                    break
        else:
            try:
                res = self.client.table("youtube_videos").select("*").eq("video_id", video_id).execute()
                video = res.data[0] if res.data else None
            except Exception as e:
                logger.error(f"Failed to get youtube video: {e}")
                # Fallback to mock search
                for item in MOCK_DB["youtube_videos"]:
                    if item.get("video_id") == video_id:
                        video = item
                        break
        
        if video:
            if video.get("auto_reply") is None:
                video["auto_reply"] = True
            # Merge/fallback to local mock_db if status is missing
            if video.get("status") is None:
                mock_v = next((mv for mv in MOCK_DB["youtube_videos"] if mv.get("video_id") == video_id), None)
                video["status"] = mock_v.get("status") if (mock_v and mock_v.get("status") is not None) else "monitored"
        return video

    def update_youtube_video_auto_reply(self, video_id: str, auto_reply: bool) -> Optional[Dict[str, Any]]:
        video = self.get_youtube_video(video_id)
        if not video:
            return None
        
        data = {"auto_reply": auto_reply}
        if self.is_mock:
            return self._update("youtube_videos", video["id"], data)
        else:
            try:
                res = self.client.table("youtube_videos").update(data).eq("id", video["id"]).execute()
                if res.data:
                    return res.data[0]
                # If update succeeded but did not return data
                video = dict(video)
                video["auto_reply"] = auto_reply
                return video
            except Exception as e:
                err_msg = str(e)
                if "auto_reply" in err_msg or "column" in err_msg:
                    logger.warning(
                        "Supabase error: youtube_videos table may be missing 'auto_reply' column during update. "
                        "Please execute this SQL migration in your Supabase SQL Editor:\n"
                        "ALTER TABLE youtube_videos ADD COLUMN IF NOT EXISTS auto_reply BOOLEAN DEFAULT true;\n"
                        f"Detailed error: {e}"
                    )
                # Fallback to mock
                return self._update("youtube_videos", video["id"], data)

    def update_youtube_video_status(self, video_id: str, status: str) -> Optional[Dict[str, Any]]:
        video = self.get_youtube_video(video_id)
        if not video:
            return None
        
        data = {"status": status}
        if self.is_mock:
            return self._update("youtube_videos", video["id"], data)
        else:
            try:
                res = self.client.table("youtube_videos").update(data).eq("id", video["id"]).execute()
                if res.data:
                    return res.data[0]
                video = dict(video)
                video["status"] = status
                return video
            except Exception as e:
                err_msg = str(e)
                if "status" in err_msg or "column" in err_msg:
                    logger.warning(
                        "Supabase error updating status column. The youtube_videos table may be missing 'status' column. "
                        "Please execute this SQL migration in your Supabase SQL Editor:\n"
                        "ALTER TABLE youtube_videos ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'monitored';\n"
                        f"Detailed error: {e}"
                    )
                else:
                    logger.error(f"Failed to update youtube video status: {e}")
                # Fallback to mock
                return self._update("youtube_videos", video["id"], data)

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
    def create_youtube_comment(self, video_id: str, comment_id: str, username: str, text: str, timestamp: str, intent: str = "SPAM", confidence: float = 1.0, status: str = "pending_approval", reply_link: str = None) -> Dict[str, Any]:
        # Duplicate detection (Requirement 1 & Diagnostics)
        existing = self.get_youtube_comment(comment_id)
        if existing:
            logger.info(f"[DB DUPLICATE DETECTED] Comment {comment_id} from @{username} already exists. Skipping insertion.")
            return existing

        # Generate default reply link if not provided
        if not reply_link:
            import os
            from backend.config import settings
            public_url = settings.PUBLIC_URL or os.getenv("PUBLIC_URL") or os.getenv("APP_BASE_URL") or "http://localhost:8000"
            if "host.docker.internal" in public_url:
                public_url = "http://localhost:8000"
            if not public_url.endswith("/"):
                public_url += "/"
            reply_link = f"{public_url}youtube/r/{comment_id}"

        data = {
            "video_id": video_id,
            "comment_id": comment_id,
            "username": username,
            "text": text,
            "timestamp": timestamp,
            "intent": intent,
            "confidence": confidence,
            "status": status,
            "reply_link": reply_link
        }
        
        logger.info(f"[DB INSERT] Inserting comment {comment_id} from @{username} (intent: {intent}, reply_link: {reply_link})")
        
        if self.is_mock:
            # Avoid id collision/empty
            if "id" not in data:
                data["id"] = str(uuid.uuid4())
            if "created_at" not in data:
                data["created_at"] = datetime.now().isoformat()
            MOCK_DB["youtube_comments"].append(data)
            logger.info(f"[MOCK DB] Inserted into youtube_comments: {data['id']}")
            save_mock_db()
            return data
        else:
            try:
                res = self.client.table("youtube_comments").insert(data).execute()
                if res.data:
                    return res.data[0]
                return data
            except Exception as e:
                err_msg = str(e)
                if "reply_link" in err_msg or "column" in err_msg:
                    logger.warning(
                        f"[DB WARNING] youtube_comments table lacks 'reply_link' column. Retrying without column. Error: {e}"
                    )
                    data_fallback = dict(data)
                    data_fallback.pop("reply_link", None)
                    try:
                        res = self.client.table("youtube_comments").insert(data_fallback).execute()
                        if res.data:
                            record = res.data[0]
                            record["reply_link"] = data["reply_link"]
                            return record
                    except Exception as fallback_e:
                        logger.error(f"[DB ERROR] Fallback insert failed: {fallback_e}")
                else:
                    logger.error(f"[DB ERROR] Failed to insert comment: {e}")
                
                # Fallback to Mock DB
                logger.warning("[DB FALLBACK] Falling back to local in-memory DB for this comment record.")
                if "id" not in data:
                    data["id"] = str(uuid.uuid4())
                if "created_at" not in data:
                    data["created_at"] = datetime.now().isoformat()
                MOCK_DB["youtube_comments"].append(data)
                save_mock_db()
                return data

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
    def create_youtube_reply(self, comment_id: str, suggested_reply: str, actual_reply: str = None, reply_id: str = None, status: str = "draft", published_at: str = None, failure_reason: str = None) -> Dict[str, Any]:
        data = {
            "comment_id": comment_id,
            "suggested_reply": suggested_reply,
            "actual_reply": actual_reply,
            "reply_id": reply_id,
            "status": status,
            "published_at": published_at,
            "failure_reason": failure_reason
        }
        if self.is_mock:
            if "id" not in data:
                data["id"] = str(uuid.uuid4())
            if "created_at" not in data:
                data["created_at"] = datetime.now().isoformat()
            MOCK_DB["youtube_replies"].append(data)
            logger.info(f"[MOCK DB] Inserted into youtube_replies: {data['id']}")
            save_mock_db()
            return data
        else:
            try:
                if "id" not in data:
                    data["id"] = str(uuid.uuid4())
                if "created_at" not in data:
                    data["created_at"] = datetime.now().isoformat()
                res = self.client.table("youtube_replies").insert(data).execute()
                if res.data:
                    return res.data[0]
                return data
            except Exception as e:
                logger.warning(f"[DB WARNING] youtube_replies table insert with failure_reason failed: {e}. Retrying fallback.")
                data_fallback = dict(data)
                data_fallback.pop("failure_reason", None)
                try:
                    res = self.client.table("youtube_replies").insert(data_fallback).execute()
                    if res.data:
                        return res.data[0]
                except Exception as inner_e:
                    logger.error(f"[DB ERROR] Fallback insert failed: {inner_e}")
                MOCK_DB["youtube_replies"].append(data)
                save_mock_db()
                return data

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
        if self.is_mock:
            return self._update("youtube_replies", reply_db_id, data)
        else:
            try:
                res = self.client.table("youtube_replies").update(data).eq("id", reply_db_id).execute()
                if res.data:
                    return res.data[0]
                return None
            except Exception as e:
                logger.warning(f"[DB WARNING] youtube_replies update failed: {e}. Retrying fallback.")
                data_fallback = dict(data)
                data_fallback.pop("failure_reason", None)
                try:
                    res = self.client.table("youtube_replies").update(data_fallback).eq("id", reply_db_id).execute()
                    if res.data:
                        return res.data[0]
                except Exception as inner_e:
                    logger.error(f"[DB ERROR] Fallback update failed: {inner_e}")
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
        
        if self.is_mock:
            if "id" not in data:
                data["id"] = str(uuid.uuid4())
            if "created_at" not in data:
                data["created_at"] = datetime.now().isoformat()
            MOCK_DB["youtube_leads"].append(data)
            save_mock_db()
            return data
        else:
            try:
                res = self.client.table("youtube_leads").insert(data).execute()
                if res.data:
                    return res.data[0]
                return data
            except Exception as e:
                err_msg = str(e)
                if "autopilot" in err_msg or "column" in err_msg:
                    logger.warning(
                        f"[DB WARNING] youtube_leads table lacks 'autopilot' column. Retrying without column. Error: {e}"
                    )
                    data_fallback = dict(data)
                    data_fallback.pop("autopilot", None)
                    try:
                        res = self.client.table("youtube_leads").insert(data_fallback).execute()
                        if res.data:
                            record = res.data[0]
                            record["autopilot"] = data["autopilot"]
                            return record
                    except Exception as fallback_e:
                        logger.error(f"[DB ERROR] Fallback lead insert failed: {fallback_e}")
                else:
                    logger.error(f"[DB ERROR] Failed to insert lead: {e}")
                
                # Fallback to local mock db
                logger.warning("[DB FALLBACK] Falling back to local in-memory DB for this lead record.")
                if "id" not in data:
                    data["id"] = str(uuid.uuid4())
                if "created_at" not in data:
                    data["created_at"] = datetime.now().isoformat()
                MOCK_DB["youtube_leads"].append(data)
                save_mock_db()
                return data

    def get_youtube_leads(self) -> List[Dict[str, Any]]:
        return self._select_all("youtube_leads")

    def update_youtube_lead_autopilot(self, lead_id: str, autopilot: bool) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            return self._update("youtube_leads", lead_id, {"autopilot": autopilot})
        else:
            try:
                res = self.client.table("youtube_leads").update({"autopilot": autopilot}).eq("id", lead_id).execute()
                if res.data:
                    return res.data[0]
                return None
            except Exception as e:
                err_msg = str(e)
                if "autopilot" in err_msg or "column" in err_msg:
                    logger.warning(f"[DB WARNING] youtube_leads table lacks 'autopilot' column. Ignoring autopilot update in DB: {e}")
                    # Update local mock as fallback
                    for item in MOCK_DB["youtube_leads"]:
                        if item.get("id") == lead_id:
                            item["autopilot"] = autopilot
                            save_mock_db()
                            return item
                    return None
                else:
                    logger.error(f"[DB ERROR] Failed to update lead autopilot: {e}")
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
                    {"video_id": "PuCb1JHpBkM", "title": "Cardamom Export Launch Campaign", "comments": 8, "leads": 4}
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

    # --- WhatsApp Chat History (Backward Compatible Wrapper) ---
    def get_whatsapp_messages(self, lead_id: str = None) -> List[Dict[str, Any]]:
        # Resolve conversation using lead_id
        if not lead_id:
            # If no lead_id is provided, try returning all messages
            all_messages = self._select_all("messages")
            legacy_messages = []
            for m in all_messages:
                legacy_messages.append({
                    "id": m.get("id"),
                    "lead_id": lead_id or "legacy_lead",
                    "sender": "business" if m.get("sender_type") in ["agent", "ai", "system"] else "customer",
                    "text": m.get("content"),
                    "created_at": m.get("created_at")
                })
            return legacy_messages
            
        conv = self.get_conversation_by_lead(lead_id)
        if not conv:
            return []
            
        msgs = self.get_messages_by_conversation(conv["id"])
        legacy_messages = []
        for m in msgs:
            legacy_messages.append({
                "id": m.get("id"),
                "lead_id": lead_id,
                "sender": "business" if m.get("sender_type") in ["agent", "ai", "system"] else "customer",
                "text": m.get("content"),
                "created_at": m.get("created_at")
            })
        return legacy_messages

    def create_whatsapp_message(self, lead_id: str, sender: str, text: str) -> Dict[str, Any]:
        conv = self.get_conversation_by_lead(lead_id)
        if not conv:
            # Determine username if possible
            username = "customer"
            leads = self.get_youtube_leads()
            lead = next((l for l in leads if l["id"] == lead_id), None)
            if lead:
                username = lead.get("username", "customer")
            
            # Create a default conversation
            conv = self.create_conversation_v2(
                tenant_id="00000000-0000-0000-0000-000000000000",
                customer_phone=f"+91{username}", # dummy phone for legacy leads
                channel="whatsapp",
                lead_id=lead_id
            )
            
        # Determine sender_type
        if sender == "business":
            sender_type = "agent"
        elif sender == "ai":
            sender_type = "ai"
        else:
            sender_type = "customer"
            
        msg = self.create_message(
            conversation_id=conv["id"],
            sender_type=sender_type,
            content=text
        )
        
        return {
            "id": msg.get("id"),
            "lead_id": lead_id,
            "sender": sender,
            "text": text,
            "created_at": msg.get("created_at")
        }

    # --- Tenants ---
    def create_tenant(self, name: str, tenant_id: str = None) -> Dict[str, Any]:
        data = {"name": name}
        if tenant_id:
            data["id"] = tenant_id
        return self._insert("tenants", data)

    def get_tenants(self) -> List[Dict[str, Any]]:
        return self._select_all("tenants")

    def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        return self._select_one("tenants", tenant_id)

    # --- WhatsApp Instances ---
    def create_whatsapp_instance(self, tenant_id: str, provider: str, instance_name: str, phone_number: str = None, status: str = "disconnected", session_data: Dict[str, Any] = None) -> Dict[str, Any]:
        data = {
            "tenant_id": tenant_id,
            "provider": provider,
            "instance_name": instance_name,
            "phone_number": phone_number,
            "status": status,
            "session_data": session_data or {}
        }
        return self._insert("whatsapp_instances", data)

    def get_whatsapp_instances(self, tenant_id: str) -> List[Dict[str, Any]]:
        if self.is_mock:
            return [i for i in MOCK_DB.get("whatsapp_instances", []) if i.get("tenant_id") == tenant_id]
        else:
            try:
                res = self.client.table("whatsapp_instances").select("*").eq("tenant_id", tenant_id).execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Failed to get whatsapp_instances for tenant {tenant_id}: {e}")
                return [i for i in MOCK_DB.get("whatsapp_instances", []) if i.get("tenant_id") == tenant_id]

    def get_whatsapp_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        return self._select_one("whatsapp_instances", instance_id)

    def get_whatsapp_instance_by_name(self, instance_name: str) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            for item in MOCK_DB.get("whatsapp_instances", []):
                if item.get("instance_name") == instance_name:
                    return item
            return None
        else:
            try:
                res = self.client.table("whatsapp_instances").select("*").eq("instance_name", instance_name).execute()
                return res.data[0] if res.data else None
            except Exception as e:
                logger.error(f"Failed to get whatsapp_instance by name {instance_name}: {e}")
                # Fallback to mock search
                for item in MOCK_DB.get("whatsapp_instances", []):
                    if item.get("instance_name") == instance_name:
                        return item
                return None

    def update_whatsapp_instance_status(self, instance_id_or_name: str, status: str, phone_number: str = None, session_data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        instance = self.get_whatsapp_instance_by_name(instance_id_or_name)
        if not instance:
            instance = self.get_whatsapp_instance(instance_id_or_name)
        if not instance:
            return None
        
        updates = {"status": status}
        if phone_number is not None:
            updates["phone_number"] = phone_number
        if session_data is not None:
            updates["session_data"] = session_data
            
        res = self._update("whatsapp_instances", instance["id"], updates)
        try:
            self.update_all_reply_links()
        except Exception as e:
            logger.error(f"Failed to automatically update reply links on status update: {e}")
        return res

    def update_whatsapp_instance_webhook(self, instance_id_or_name: str, webhook_url: str) -> Optional[Dict[str, Any]]:
        instance = self.get_whatsapp_instance_by_name(instance_id_or_name)
        if not instance:
            instance = self.get_whatsapp_instance(instance_id_or_name)
        if not instance:
            return None
        
        session_data = instance.get("session_data") or {}
        if not isinstance(session_data, dict):
            session_data = {}
        session_data["webhook_url"] = webhook_url
        
        res = self._update("whatsapp_instances", instance["id"], {"session_data": session_data})
        try:
            self.update_all_reply_links()
        except Exception as e:
            logger.error(f"Failed to automatically update reply links on webhook update: {e}")
        return res

    def delete_whatsapp_instance(self, instance_id_or_name: str) -> bool:
        instance = self.get_whatsapp_instance_by_name(instance_id_or_name)
        if not instance:
            instance = self.get_whatsapp_instance(instance_id_or_name)
        if not instance:
            return False
            
        if self.is_mock:
            MOCK_DB["whatsapp_instances"] = [i for i in MOCK_DB.get("whatsapp_instances", []) if i.get("id") != instance["id"]]
            save_mock_db()
            return True
        else:
            try:
                self.client.table("whatsapp_instances").delete().eq("id", instance["id"]).execute()
                return True
            except Exception as e:
                logger.error(f"Failed to delete whatsapp_instance {instance['id']}: {e}")
                return False

    # --- Conversations v2 ---
    def create_conversation_v2(self, tenant_id: str, customer_phone: str, channel: str = "whatsapp", assigned_agent_id: str = None, status: str = "open", lead_id: str = None, state: str = "WELCOME", instance_name: str = None) -> Dict[str, Any]:
        data = {
            "tenant_id": tenant_id,
            "customer_phone": customer_phone,
            "channel": channel,
            "assigned_agent_id": assigned_agent_id,
            "status": status,
            "lead_id": lead_id,
            "state": state,
            "history": [],
            "state_metadata": {},
            "ai_enabled": True,
            "human_override": False,
            "instance_name": instance_name
        }
        return self._insert("conversations", data)

    def get_conversations(self, tenant_id: str, status: str = None) -> List[Dict[str, Any]]:
        conversations = []
        if self.is_mock:
            conversations = [c for c in MOCK_DB.get("conversations", []) if c.get("tenant_id") == tenant_id]
            if status:
                conversations = [c for c in conversations if c.get("status") == status]
        else:
            try:
                query = self.client.table("conversations").select("*").eq("tenant_id", tenant_id)
                if status:
                    query = query.eq("status", status)
                res = query.execute()
                conversations = res.data or []
            except Exception as e:
                logger.error(f"Failed to fetch conversations for tenant {tenant_id}: {e}")
                conversations = [c for c in MOCK_DB.get("conversations", []) if c.get("tenant_id") == tenant_id]
                if status:
                    conversations = [c for c in conversations if c.get("status") == status]

        # Filter conversations by currently connected WhatsApp instance name
        instances = self.get_whatsapp_instances(tenant_id)
        active_instance = next((i for i in instances if i.get("status") == "connected"), None)
        if not active_instance and instances:
            active_instance = next((i for i in instances if i.get("status") == "connecting"), None)
            if not active_instance:
                active_instance = instances[0]

        active_instance_name = active_instance["instance_name"] if active_instance else None
        
        filtered = []
        for conv in conversations:
            conv_instance = conv.get("instance_name")
            if not conv_instance:
                if active_instance_name:
                    # Dynamically bind legacy conversations to the current active instance
                    self.update_conversation_v2(conv["id"], {"instance_name": active_instance_name})
                    conv["instance_name"] = active_instance_name
                    filtered.append(conv)
                else:
                    filtered.append(conv)
            elif conv_instance == active_instance_name:
                filtered.append(conv)

        return filtered

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        return self._select_one("conversations", conversation_id)

    def get_conversation_by_phone(self, tenant_id: str, customer_phone: str, instance_name: str = None) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            for item in MOCK_DB.get("conversations", []):
                if item.get("tenant_id") == tenant_id and item.get("customer_phone") == customer_phone:
                    if instance_name is None or item.get("instance_name") == instance_name:
                        return item
            return None
        else:
            try:
                query = self.client.table("conversations").select("*").eq("tenant_id", tenant_id).eq("customer_phone", customer_phone)
                if instance_name:
                    query = query.eq("instance_name", instance_name)
                res = query.execute()
                return res.data[0] if res.data else None
            except Exception as e:
                logger.error(f"Failed to get conversation by phone {customer_phone}: {e}")
                # Fallback to mock search
                for item in MOCK_DB.get("conversations", []):
                    if item.get("tenant_id") == tenant_id and item.get("customer_phone") == customer_phone:
                        if instance_name is None or item.get("instance_name") == instance_name:
                            return item
                return None

    def update_conversation_v2(self, conversation_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._update("conversations", conversation_id, updates)

    def delete_all_conversations(self, tenant_id: str) -> bool:
        logger.info(f"Clearing all conversations for tenant {tenant_id}")
        
        # 1. Fetch conversations to get lead IDs and delete associated orders/leads
        try:
            convs = self.get_conversations(tenant_id)
            lead_ids = [c["lead_id"] for c in convs if c.get("lead_id")]
            for lead_id in lead_ids:
                try:
                    if self.is_mock:
                        MOCK_DB["orders"] = [o for o in MOCK_DB.get("orders", []) if o.get("lead_id") != lead_id]
                    else:
                        self.client.table("orders").delete().eq("lead_id", lead_id).execute()
                    
                    lead_data = self._select_one("leads", lead_id)
                    if lead_data and lead_data.get("username", "").startswith("wa_"):
                        if self.is_mock:
                            MOCK_DB["leads"] = [l for l in MOCK_DB.get("leads", []) if l.get("id") != lead_id]
                        else:
                            self.client.table("leads").delete().eq("id", lead_id).execute()
                except Exception as ex:
                    logger.error(f"Failed to clean up lead/orders on delete_all_conversations: {ex}")
        except Exception as e:
            logger.error(f"Failed to fetch conversations for clean up: {e}")

        # 2. Delete conversations
        if self.is_mock:
            conv_ids = [c["id"] for c in MOCK_DB.get("conversations", []) if c.get("tenant_id") == tenant_id]
            MOCK_DB["messages"] = [m for m in MOCK_DB.get("messages", []) if m.get("conversation_id") not in conv_ids]
            MOCK_DB["conversations"] = [c for c in MOCK_DB.get("conversations", []) if c.get("tenant_id") != tenant_id]
            save_mock_db()
            return True
        else:
            try:
                self.client.table("conversations").delete().eq("tenant_id", tenant_id).execute()
                return True
            except Exception as e:
                logger.error(f"Failed to delete all conversations from Supabase: {e}")
                conv_ids = [c["id"] for c in MOCK_DB.get("conversations", []) if c.get("tenant_id") == tenant_id]
                MOCK_DB["messages"] = [m for m in MOCK_DB.get("messages", []) if m.get("conversation_id") not in conv_ids]
                MOCK_DB["conversations"] = [c for c in MOCK_DB.get("conversations", []) if c.get("tenant_id") != tenant_id]
                save_mock_db()
                return True

    def delete_conversation_by_id(self, conversation_id: str) -> bool:
        logger.info(f"Deleting conversation ID {conversation_id}")
        
        # 1. Fetch conversation to get lead_id and delete associated orders/leads
        try:
            conv = self.get_conversation(conversation_id)
            if conv and conv.get("lead_id"):
                lead_id = conv["lead_id"]
                if self.is_mock:
                    MOCK_DB["orders"] = [o for o in MOCK_DB.get("orders", []) if o.get("lead_id") != lead_id]
                else:
                    self.client.table("orders").delete().eq("lead_id", lead_id).execute()
                
                lead_data = self._select_one("leads", lead_id)
                if lead_data and lead_data.get("username", "").startswith("wa_"):
                    if self.is_mock:
                        MOCK_DB["leads"] = [l for l in MOCK_DB.get("leads", []) if l.get("id") != lead_id]
                    else:
                        self.client.table("leads").delete().eq("id", lead_id).execute()
        except Exception as e:
            logger.error(f"Failed to clean up lead/orders on delete_conversation_by_id: {e}")

        # 2. Delete conversation
        if self.is_mock:
            MOCK_DB["messages"] = [m for m in MOCK_DB.get("messages", []) if m.get("conversation_id") != conversation_id]
            MOCK_DB["conversations"] = [c for c in MOCK_DB.get("conversations", []) if c.get("id") != conversation_id]
            save_mock_db()
            return True
        else:
            try:
                self.client.table("conversations").delete().eq("id", conversation_id).execute()
                return True
            except Exception as e:
                logger.error(f"Failed to delete conversation {conversation_id} from Supabase: {e}")
                MOCK_DB["messages"] = [m for m in MOCK_DB.get("messages", []) if m.get("conversation_id") != conversation_id]
                MOCK_DB["conversations"] = [c for c in MOCK_DB.get("conversations", []) if c.get("id") != conversation_id]
                save_mock_db()
                return True

    def edit_message(self, message_id: str, new_content: str) -> Optional[Dict[str, Any]]:
        logger.info(f"Editing message ID {message_id} to '{new_content}'")
        msg = self._select_one("messages", message_id)
        if not msg:
            logger.warning(f"Message ID {message_id} not found for editing")
            return None
            
        old_content = msg.get("content")
        metadata = msg.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
            
        edit_history = metadata.get("edit_history", [])
        if not isinstance(edit_history, list):
            edit_history = []
            
        edit_history.append({
            "content": old_content,
            "edited_at": datetime.now().isoformat()
        })
        
        metadata["edited"] = True
        metadata["edited_at"] = datetime.now().isoformat()
        metadata["edit_history"] = edit_history
        
        updates = {
            "content": new_content,
            "metadata": metadata
        }
        
        return self._update("messages", message_id, updates)

    # --- Messages ---
    def create_message(self, conversation_id: str, sender_type: str, content: str, message_type: str = "text", sender_id: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        data = {
            "conversation_id": conversation_id,
            "sender_type": sender_type,
            "sender_id": sender_id,
            "message_type": message_type,
            "content": content,
            "metadata": metadata or {}
        }
        return self._insert("messages", data)

    def get_messages_by_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        if self.is_mock:
            items = [m for m in MOCK_DB.get("messages", []) if m.get("conversation_id") == conversation_id]
            items.sort(key=lambda x: x.get("created_at") or "")
            return items
        else:
            try:
                res = self.client.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Failed to fetch messages for conversation {conversation_id}: {e}")
                items = [m for m in MOCK_DB.get("messages", []) if m.get("conversation_id") == conversation_id]
                items.sort(key=lambda x: x.get("created_at") or "")
                return items

    def update_message_metadata(self, message_id: str, metadata_updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg = self._select_one("messages", message_id)
        if not msg:
            return None
        current_metadata = msg.get("metadata") or {}
        current_metadata.update(metadata_updates)
        return self._update("messages", message_id, {"metadata": current_metadata})

    def get_message_by_provider_sid(self, provider_message_sid: str) -> Optional[Dict[str, Any]]:
        if self.is_mock:
            for m in MOCK_DB.get("messages", []):
                meta = m.get("metadata") or {}
                if meta.get("provider_message_sid") == provider_message_sid:
                    return m
            return None
        else:
            try:
                res = self.client.table("messages").select("*").eq("metadata->>provider_message_sid", provider_message_sid).execute()
                if res.data:
                    return res.data[0]
                for m in MOCK_DB.get("messages", []):
                    meta = m.get("metadata") or {}
                    if meta.get("provider_message_sid") == provider_message_sid:
                        return m
                return None
            except Exception as e:
                logger.error(f"Failed to fetch message by provider_message_sid {provider_message_sid}: {e}")
                for m in MOCK_DB.get("messages", []):
                    meta = m.get("metadata") or {}
                    if meta.get("provider_message_sid") == provider_message_sid:
                        return m
                return None

    # --- Video Jobs ---
    def create_video_job(self, product_id: str, status: str = "queued") -> Dict[str, Any]:
        data = {
            "product_id": product_id,
            "status": status,
            "progress_step": 0,
            "progress_message": "Preparing assets...",
            "error_message": None
        }
        return self._insert("video_jobs", data)

    def update_video_job(self, job_id: str, status: str = None, progress_step: int = None, progress_message: str = None, error_message: str = None) -> Optional[Dict[str, Any]]:
        updates = {}
        if status is not None:
            updates["status"] = status
        if progress_step is not None:
            updates["progress_step"] = progress_step
        if progress_message is not None:
            updates["progress_message"] = progress_message
        if error_message is not None:
            updates["error_message"] = error_message
        
        updates["updated_at"] = datetime.now().isoformat()
        return self._update("video_jobs", job_id, updates)

    def get_video_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._select_one("video_jobs", job_id)

    def get_video_jobs_by_product(self, product_id: str) -> List[Dict[str, Any]]:
        if self.is_mock:
            items = [j for j in MOCK_DB.get("video_jobs", []) if j.get("product_id") == product_id]
            items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
            return items
        else:
            try:
                res = self.client.table("video_jobs").select("*").eq("product_id", product_id).order("created_at", desc=True).execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Failed to fetch video jobs for product {product_id}: {e}")
                items = [j for j in MOCK_DB.get("video_jobs", []) if j.get("product_id") == product_id]
                items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
                return items

    def get_unfinished_video_jobs(self) -> List[Dict[str, Any]]:
        if self.is_mock:
            items = [j for j in MOCK_DB.get("video_jobs", []) if j.get("status") in ["queued", "processing"]]
            items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
            return items
        else:
            try:
                res = self.client.table("video_jobs").select("*").in_("status", ["queued", "processing"]).order("created_at", desc=True).execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Failed to fetch unfinished video jobs: {e}")
                items = [j for j in MOCK_DB.get("video_jobs", []) if j.get("status") in ["queued", "processing"]]
                items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
                return items

    def purge_campaign_data(self, product_id: str) -> bool:
        """
        Permanently purges all generated campaign records (scripts, thumbnails, translations,
        voiceovers, videos, video_jobs, keywords) and physical media files associated with a product.
        """
        import glob
        from backend.config import settings

        logger.info(f"[PURGE CAMPAIGN] Purging all database records and media files for product {product_id}")
        
        try:
            # 1. Fetch scripts
            scripts = self.get_scripts_by_product(product_id)
            script_ids = [s["id"] for s in scripts]

            # 2. Fetch & delete thumbnails
            for s_id in script_ids:
                thumbnails = self.get_thumbnails_by_script(s_id)
                for thumb in thumbnails:
                    img_url = thumb.get("image_url")
                    if img_url and img_url.startswith("/static/"):
                        file_p = settings.STATIC_DIR / img_url[8:]
                        if os.path.exists(file_p):
                            try: os.remove(file_p)
                            except Exception: pass
                    if self.is_mock:
                        MOCK_DB["thumbnails"] = [t for t in MOCK_DB.get("thumbnails", []) if t.get("id") != thumb["id"]]
                    else:
                        try: self.client.table("thumbnails").delete().eq("id", thumb["id"]).execute()
                        except Exception: pass

            # 3. Fetch & delete translations, voiceovers, videos
            for s_id in script_ids:
                translations = self.get_translations_by_script(s_id)
                for trans in translations:
                    # Voiceovers
                    voiceovers_list = self._select_all("voiceovers")
                    voiceovers = [v for v in voiceovers_list if v.get("translation_id") == trans["id"]]
                    for voice in voiceovers:
                        audio_url = voice.get("audio_url")
                        if audio_url and audio_url.startswith("/static/"):
                            file_p = settings.STATIC_DIR / audio_url[8:]
                            if os.path.exists(file_p):
                                try: os.remove(file_p)
                                except Exception: pass
                        
                        # Videos
                        videos_list = self._select_all("videos")
                        vids = [vid for vid in videos_list if vid.get("voiceover_id") == voice["id"]]
                        for vid in vids:
                            v_url = vid.get("video_url")
                            if v_url and v_url.startswith("/static/"):
                                file_p = settings.STATIC_DIR / v_url[8:]
                                if os.path.exists(file_p):
                                    try: os.remove(file_p)
                                    except Exception: pass
                            if self.is_mock:
                                MOCK_DB["videos"] = [v for v in MOCK_DB.get("videos", []) if v.get("id") != vid["id"]]
                            else:
                                try: self.client.table("videos").delete().eq("id", vid["id"]).execute()
                                except Exception: pass

                        if self.is_mock:
                            MOCK_DB["voiceovers"] = [v for v in MOCK_DB.get("voiceovers", []) if v.get("id") != voice["id"]]
                        else:
                            try: self.client.table("voiceovers").delete().eq("id", voice["id"]).execute()
                            except Exception: pass

                    if self.is_mock:
                        MOCK_DB["translations"] = [t for t in MOCK_DB.get("translations", []) if t.get("id") != trans["id"]]
                    else:
                        try: self.client.table("translations").delete().eq("id", trans["id"]).execute()
                        except Exception: pass

            # Delete scripts
            for s_id in script_ids:
                if self.is_mock:
                    MOCK_DB["scripts"] = [s for s in MOCK_DB.get("scripts", []) if s.get("id") != s_id]
                else:
                    try: self.client.table("scripts").delete().eq("id", s_id).execute()
                    except Exception: pass

            # Delete keywords
            keywords = self.get_keywords_by_product(product_id)
            for kw in keywords:
                if self.is_mock:
                    MOCK_DB["keywords"] = [k for k in MOCK_DB.get("keywords", []) if k.get("id") != kw["id"]]
                else:
                    try: self.client.table("keywords").delete().eq("id", kw["id"]).execute()
                    except Exception: pass

            # Delete video_jobs
            if self.is_mock:
                MOCK_DB["video_jobs"] = [j for j in MOCK_DB.get("video_jobs", []) if j.get("product_id") != product_id]
                save_mock_db()
            else:
                try: self.client.table("video_jobs").delete().eq("product_id", product_id).execute()
                except Exception: pass

            # Physical files cleanup in media directory
            patterns = [f"*{product_id}*", f"temp_*{product_id}*"]
            for pat in patterns:
                for filepath in glob.glob(os.path.join(str(settings.MEDIA_DIR), pat)):
                    try:
                        if os.path.exists(filepath): os.remove(filepath)
                    except Exception: pass

            logger.info(f"[PURGE CAMPAIGN] Purged campaign data completely for product {product_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to purge campaign data for product {product_id}: {e}")
            return False

    def update_all_reply_links(self, new_base_url: str = None) -> int:
        """
        Scan all youtube comments and replies in the database (or mock database)
        and update the redirect URLs to use the latest base public URL.
        Returns the number of records updated.
        """
        import re
        import os
        if not new_base_url:
            from backend.config import settings
            new_base_url = settings.PUBLIC_URL or os.getenv("PUBLIC_URL") or os.getenv("APP_BASE_URL") or "http://localhost:8000"
            
        if "host.docker.internal" in new_base_url:
            new_base_url = new_base_url.replace("host.docker.internal", "localhost")
        if not new_base_url.endswith("/"):
            new_base_url += "/"
            
        logger.info(f"[LINK SYNC] Automatically updating all YouTube reply links to use base URL: {new_base_url}")
        
        updated_count = 0
        
        # 1. Update youtube_comments table
        comments = self.get_youtube_comments()
        for comment in comments:
            comment_id = comment["comment_id"]
            expected_link = f"{new_base_url}youtube/r/{comment_id}"
            
            # Check if current link matches expected link
            if comment.get("reply_link") != expected_link:
                comment["reply_link"] = expected_link
                self._update("youtube_comments", comment["id"], {"reply_link": expected_link})
                updated_count += 1
                
        # 2. Update youtube_replies table (suggested_reply & actual_reply containing old URLs)
        replies = self.get_youtube_replies()
        pattern = re.compile(r"https?://[^/]+/youtube/r/([a-zA-Z0-9_\-]+)")
        
        for reply in replies:
            changed = False
            updates = {}
            for field in ["suggested_reply", "actual_reply"]:
                val = reply.get(field)
                if val and isinstance(val, str):
                    if pattern.search(val):
                        # Replace the URL matches
                        new_val = pattern.sub(rf"{new_base_url}youtube/r/\1", val)
                        if new_val != val:
                            updates[field] = new_val
                            reply[field] = new_val
                            changed = True
            if changed:
                self._update("youtube_replies", reply["id"], updates)
                updated_count += 1
                
        logger.info(f"[LINK SYNC] Completed. Updated {updated_count} records to use new base URL.")
        return updated_count

supabase_svc = SupabaseService()
