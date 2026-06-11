# backend/services/supabase_service.py
import logging
import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from backend.database.connection import db_conn

logger = logging.getLogger("vyaparai.supabase_service")

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
    "analytics": []
}

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

supabase_svc = SupabaseService()
