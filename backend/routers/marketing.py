# backend/routers/marketing.py
import os
import logging
from typing import List
from fastapi import APIRouter, HTTPException
from backend.models.schemas import GenerateContentRequest, TranslateRequest, GenerateVideoRequest, ApproveRequest, RegenerateRequest, PublishRequest
from backend.services.supabase_service import supabase_svc
from backend.crews.marketing_crew import marketing_crew
from backend.services.voice_service import voice_svc
from backend.services.video_service import video_svc
from backend.services.youtube_publishing_service import youtube_publish_svc
from backend.config import settings

logger = logging.getLogger("vyaparai.routers.marketing")
router = APIRouter(prefix="", tags=["Marketing Content Agents"])

from pathlib import Path

def get_fallback_video_url(language: str) -> str:
    fallbacks = {
        "English": "/static/media/video_english_v2_3ce14206.mp4",
        "Hindi": "/static/media/video_hindi_v2_63b2d922.mp4",
        "Tamil": "/static/media/video_tamil_v2_12efcce8.mp4",
        "Telugu": "/static/media/video_telugu_v2_6a2efde3.mp4",
        "Malayalam": "/static/media/video_malayalam_v2_b9304c03.mp4"
    }
    lang_key = next((k for k in fallbacks.keys() if k.lower() == language.lower()), "English")
    return fallbacks[lang_key]

def get_valid_video_url(video_url: str, language: str) -> str:
    if not video_url:
        return get_fallback_video_url(language)
    try:
        if video_url.startswith("/static/"):
            rel_path = video_url[len("/static/"):]
            file_path = settings.STATIC_DIR / rel_path
        else:
            file_path = Path(video_url)
            
        if not file_path.exists():
            return get_fallback_video_url(language)
            
        if file_path.stat().st_size <= 100:
            return get_fallback_video_url(language)
            
        return video_url
    except Exception as e:
        logger.warning(f"Error checking video file size for {video_url}: {e}")
        return video_url

@router.post("/generate-content")
async def generate_content(payload: GenerateContentRequest):
    logger.info(f"Triggering 8-Agent CrewAI pipeline for product ID: {payload.product_id}")
    try:
        product = supabase_svc.get_product(payload.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Run multi-agent pipeline
        crew_result = marketing_crew.run(
            product_name=product["name"],
            description=product.get("description", ""),
            location=payload.location,
            product_images=product.get("images", []),
            version=1
        )

        # 1. Save Discovered Keywords
        kw_data = crew_result["keywords"]
        kw_rec = supabase_svc.create_keywords(
            product_id=payload.product_id,
            primary_kw=kw_data["primary"],
            secondary_kw=kw_data["secondary"],
            long_tail_kw=kw_data["long_tail"],
            intent_kw=kw_data["intent"],
            regional_kw=kw_data["regional"]
        )

        # 2. Save Generated Script
        s_data = crew_result["script"]
        script_rec = supabase_svc.create_script(
            product_id=payload.product_id,
            title=s_data["title"],
            hook=s_data["hook"],
            script_text=s_data["script_text"],
            scene_breakdown=s_data["scene_breakdown"],
            caption_timeline=s_data["caption_timeline"],
            thumbnail_text=s_data["thumbnail_text"],
            seo_description=s_data["seo_description"],
            hashtags=s_data["hashtags"],
            version=1
        )

        # 3. Save Thumbnail Layout & Prompt
        t_data = crew_result["thumbnail"]
        thumb_rec = supabase_svc.create_thumbnail(
            script_id=script_rec["id"],
            layout=t_data["layout"],
            text=t_data["text"],
            prompt=t_data["prompt"],
            image_url=t_data.get("image_url")
        )

        # 4. Save Translations, Voiceovers, and Videos
        languages = ["English", "Hindi", "Tamil", "Telugu", "Malayalam"]
        saved_translations = []
        saved_videos = []

        for lang in languages:
            lang_scripts = crew_result["translations"][lang]
            trans_rec = supabase_svc.create_translation(
                script_id=script_rec["id"],
                language=lang,
                youtube=lang_scripts["youtube_script"],
                reel=lang_scripts["reel_script"],
                whatsapp=lang_scripts["whatsapp_post"],
                google=lang_scripts["google_business_post"]
            )
            saved_translations.append(trans_rec)

            voice_data = crew_result["voiceovers"][lang]
            voice_rec = supabase_svc.create_voiceover(
                translation_id=trans_rec["id"],
                audio_url=voice_data["audio_url"],
                duration=voice_data["duration"]
            )

            video_data = crew_result["videos"][lang]
            video_rec = supabase_svc.create_video(
                voiceover_id=voice_rec["id"],
                video_url=video_data["video_url"],
                status="ready",
                approval_status="pending",
                version=1
            )
            video_rec["video_url"] = get_valid_video_url(video_rec["video_url"], lang)
            saved_videos.append(video_rec)
            supabase_svc.increment_analytics(product["business_id"], "videos_generated", 1)

        return {
            "status": "success",
            "version": 1,
            "qa_score": crew_result["qa_score"],
            "qa_status": crew_result["qa_status"],
            "keywords": kw_rec,
            "script": script_rec,
            "thumbnail": thumb_rec,
            "translations": saved_translations,
            "videos": saved_videos
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to execute 8-agent crew: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/regenerate")
async def regenerate_campaign(payload: RegenerateRequest):
    logger.info(f"Regenerating campaign V2 for product ID: {payload.product_id}")
    try:
        product = supabase_svc.get_product(payload.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Check existing script version count
        existing_scripts = supabase_svc.get_scripts_by_product(payload.product_id)
        new_version = len(existing_scripts) + 1

        # Run pipeline with version increment
        crew_result = marketing_crew.run(
            product_name=product["name"],
            description=product.get("description", ""),
            location=payload.location,
            product_images=product.get("images", []),
            force_feedback=payload.feedback or "Please generate a new creative hook and layout",
            version=new_version
        )

        # 1. Save new script version
        s_data = crew_result["script"]
        script_rec = supabase_svc.create_script(
            product_id=payload.product_id,
            title=s_data["title"],
            hook=s_data["hook"],
            script_text=s_data["script_text"],
            scene_breakdown=s_data["scene_breakdown"],
            caption_timeline=s_data["caption_timeline"],
            thumbnail_text=s_data["thumbnail_text"],
            seo_description=s_data["seo_description"],
            hashtags=s_data["hashtags"],
            version=new_version
        )

        # 2. Save new thumbnail
        t_data = crew_result["thumbnail"]
        thumb_rec = supabase_svc.create_thumbnail(
            script_id=script_rec["id"],
            layout=t_data["layout"],
            text=t_data["text"],
            prompt=t_data["prompt"],
            image_url=t_data.get("image_url")
        )

        # 3. Save translations, voiceovers and videos
        languages = ["English", "Hindi", "Tamil", "Telugu", "Malayalam"]
        saved_translations = []
        saved_videos = []

        for lang in languages:
            lang_scripts = crew_result["translations"][lang]
            trans_rec = supabase_svc.create_translation(
                script_id=script_rec["id"],
                language=lang,
                youtube=lang_scripts["youtube_script"],
                reel=lang_scripts["reel_script"],
                whatsapp=lang_scripts["whatsapp_post"],
                google=lang_scripts["google_business_post"]
            )
            saved_translations.append(trans_rec)

            voice_data = crew_result["voiceovers"][lang]
            voice_rec = supabase_svc.create_voiceover(
                translation_id=trans_rec["id"],
                audio_url=voice_data["audio_url"],
                duration=voice_data["duration"]
            )

            video_data = crew_result["videos"][lang]
            video_rec = supabase_svc.create_video(
                voiceover_id=voice_rec["id"],
                video_url=video_data["video_url"],
                status="ready",
                approval_status="pending",
                version=new_version
            )
            video_rec["video_url"] = get_valid_video_url(video_rec["video_url"], lang)
            saved_videos.append(video_rec)

        return {
            "status": "success",
            "version": new_version,
            "qa_score": crew_result["qa_score"],
            "script": script_rec,
            "thumbnail": thumb_rec,
            "translations": saved_translations,
            "videos": saved_videos
        }
    except Exception as e:
        logger.error(f"Regeneration workflow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/publish")
async def publish_video(payload: PublishRequest):
    logger.info(f"YouTube publishing triggered for video ID: {payload.video_id}")
    try:
        video = supabase_svc.get_video(payload.video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video record not found")

        # Resolve voiceover -> translation -> script
        voiceovers = supabase_svc._select_all("voiceovers")
        voice_rec = next((v for v in voiceovers if v["id"] == video["voiceover_id"]), None)
        if not voice_rec:
            raise HTTPException(status_code=404, detail="Voiceover metadata not found")

        translation = supabase_svc.get_translation(voice_rec["translation_id"])
        if not translation:
            raise HTTPException(status_code=404, detail="Translation metadata not found")

        script = supabase_svc.get_script(translation["script_id"])
        if not script:
            raise HTTPException(status_code=404, detail="Script metadata not found")

        # Check if the video file is a mock file. If so, use fallback pre-seeded video for uploading.
        orig_filename = os.path.basename(video["video_url"])
        original_video_path = settings.MEDIA_DIR / orig_filename
        
        actual_video_path = original_video_path
        if os.path.exists(original_video_path) and os.path.getsize(original_video_path) <= 100:
            fallback_rel_url = get_fallback_video_url(translation["language"])
            actual_video_path = settings.MEDIA_DIR / os.path.basename(fallback_rel_url)
            logger.info(f"Video file is mock (<=100 bytes). Redirecting publishing to pre-seeded fallback video: {actual_video_path}")
            
        # Publish file using service (triggers real upload or mock sandbox)
        publish_res = youtube_publish_svc.publish_video(
            video_path=str(actual_video_path),
            title=script.get("title", "VyaparAI Promo Video"),
            description=script.get("seo_description", "Campaign promotional short video."),
            hashtags=script.get("hashtags", ["VyaparAI", "LocalStore"])
        )

        # Update YouTube publication details in database
        updated_video = supabase_svc.update_video_publish_info(
            video_id=payload.video_id,
            youtube_id=publish_res["youtube_id"],
            youtube_url=publish_res["youtube_url"]
        )

        # Register video in YouTube Monitor tracker so it appears in the Monitoring module
        channels = supabase_svc.get_youtube_channels()
        if channels:
            from datetime import datetime
            supabase_svc.create_youtube_video(
                channel_id=channels[0]["channel_id"],
                video_id=publish_res["youtube_id"],
                title=script.get("title", "VyaparAI Promo Video"),
                publish_date=datetime.now().isoformat(),
                status="monitored"
            )

            # If the video upload was simulated, seed some realistic, product-relevant comments immediately
            if publish_res.get("simulated", False):
                import asyncio
                import uuid
                from datetime import timedelta
                from backend.crews.youtube_monitor_crew import youtube_monitor_crew
                
                # Fetch product name
                try:
                    product = supabase_svc.get_product(script["product_id"])
                    product_name = product["name"] if product else "product"
                except Exception:
                    product_name = "product"
                
                # Setup realistic comments
                simulated_incoming = [
                    {"username": "arun_raj", "text": f"What is the price of this {product_name}? Do you deliver to Bangalore?"},
                    {"username": "hema_bhat", "text": f"How can I order? Please share contact number for {product_name}."},
                    {"username": "rahul_k", "text": f"Is this {product_name} 100% organic and chemical free?"},
                    {"username": "crypto_guy", "text": "Click here to win a free iphone! www.spambot.com"},
                    {"username": "meera_nair", "text": f"Super quality {product_name}, highly recommended! ❤️"},
                    {"username": "vicky_sharma", "text": f"Do you offer cash on delivery for {product_name}?"}
                ]
                
                for idx, demo in enumerate(simulated_incoming):
                    comment_id = f"MOCK_CMT_{uuid.uuid4().hex[:8].upper()}"
                    # Space out timestamps slightly in the past
                    comment_time = (datetime.now() - timedelta(minutes=(10 - idx) * 3)).isoformat()
                    
                    # Fire single comment processing asynchronously so it doesn't hold up HTTP response
                    asyncio.create_task(
                        youtube_monitor_crew.process_single_comment(
                            channel_id=channels[0]["channel_id"],
                            video_id=publish_res["youtube_id"],
                            comment_id=comment_id,
                            username=demo["username"],
                            comment_text=demo["text"],
                            timestamp=comment_time
                        )
                    )

        return {
            "status": "success",
            "youtube_id": publish_res["youtube_id"],
            "youtube_url": publish_res["youtube_url"],
            "simulated": publish_res.get("simulated", True),
            "video": updated_video
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"YouTube upload execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve")
async def approve_video(payload: ApproveRequest):
    logger.info(f"Updating approval for video ID: {payload.video_id} to status: {payload.status}")
    try:
        video = supabase_svc.get_video(payload.video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video record not found")

        updated_video = supabase_svc.update_video_approval(payload.video_id, payload.status)
        return {"status": "success", "data": updated_video}
    except Exception as e:
        logger.error(f"Approval update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaign/{product_id}")
async def get_campaign(product_id: str):
    try:
        # Retrieve product
        product = supabase_svc.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Retrieve keywords
        keywords_list = supabase_svc.get_keywords_by_product(product_id)
        keywords = keywords_list[0] if keywords_list else None

        # Retrieve script (latest version)
        scripts = supabase_svc.get_scripts_by_product(product_id)
        if not scripts:
            raise HTTPException(status_code=404, detail="No campaign script found for this product")
        # Sort by version descending to get latest
        scripts = sorted(scripts, key=lambda s: s.get("version", 1), reverse=True)
        latest_script = scripts[0]

        # Retrieve thumbnail
        thumbnails = supabase_svc.get_thumbnails_by_script(latest_script["id"])
        thumbnail = thumbnails[0] if thumbnails else None

        # Retrieve translations
        translations = supabase_svc.get_translations_by_script(latest_script["id"])
        
        # Match voiceovers and videos
        voiceovers = supabase_svc._select_all("voiceovers")
        videos = supabase_svc._select_all("videos")

        translations_dict = {}
        voiceovers_dict = {}
        videos_dict = {}

        for trans in translations:
            lang = trans["language"]
            translations_dict[lang] = {
                "youtube_script": trans["youtube_script"],
                "reel_script": trans["reel_script"],
                "whatsapp_post": trans["whatsapp_post"],
                "google_business_post": trans["google_business_post"]
            }

            # Find matching voiceover
            voice_rec = next((v for v in voiceovers if v["translation_id"] == trans["id"]), None)
            if voice_rec:
                voiceovers_dict[lang] = {
                    "id": voice_rec["id"],
                    "audio_url": voice_rec["audio_url"],
                    "duration": voice_rec["duration"]
                }
                
                # Find matching video
                video_rec = next((vid for vid in videos if vid["voiceover_id"] == voice_rec["id"]), None)
                if video_rec:
                    videos_dict[lang] = {
                        "id": video_rec["id"],
                        "video_url": get_valid_video_url(video_rec["video_url"], lang),
                        "status": video_rec["status"],
                        "approval_status": video_rec["approval_status"],
                        "youtube_url": video_rec.get("youtube_url"),
                        "youtube_id": video_rec.get("youtube_id")
                    }

        return {
            "product": product,
            "keywords": {
                "primary": keywords.get("primary_keywords", []) if keywords else [],
                "secondary": keywords.get("secondary_keywords", []) if keywords else [],
                "long_tail": keywords.get("long_tail_keywords", []) if keywords else [],
                "intent": keywords.get("intent_keywords", []) if keywords else [],
                "regional": keywords.get("regional_keywords", []) if keywords else []
            },
            "script": {
                "id": latest_script["id"],
                "title": latest_script["title"],
                "hook": latest_script["hook"],
                "script_text": latest_script["script_text"],
                "scene_breakdown": latest_script["scene_breakdown"],
                "caption_timeline": latest_script["caption_timeline"],
                "thumbnail_text": latest_script["thumbnail_text"],
                "seo_description": latest_script["seo_description"],
                "hashtags": latest_script["hashtags"],
                "version": latest_script["version"]
            },
            "thumbnail": {
                "layout": thumbnail["layout"] if thumbnail else "",
                "text": thumbnail["text"] if thumbnail else "",
                "prompt": thumbnail["prompt"] if thumbnail else "",
                "image_url": thumbnail.get("image_url") if thumbnail else ""
            },
            "translations": translations_dict,
            "voiceovers": voiceovers_dict,
            "videos": videos_dict
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching campaign for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/video")
async def get_videos():
    try:
        videos = supabase_svc._select_all("videos")
        voiceovers = supabase_svc._select_all("voiceovers")
        translations = supabase_svc._select_all("translations")
        scripts = supabase_svc._select_all("scripts")
        products = supabase_svc.get_products()
        
        enriched_videos = []
        for vid in videos:
            # Find voiceover -> translation -> script -> product
            voice = next((v for v in voiceovers if v["id"] == vid["voiceover_id"]), None)
            if not voice:
                continue
                
            trans = next((t for t in translations if t["id"] == voice["translation_id"]), None)
            if not trans:
                continue
                
            script = next((s for s in scripts if s["id"] == trans["script_id"]), None)
            if not script:
                continue
                
            product = next((p for p in products if p["id"] == script["product_id"]), None)
            if not product:
                continue
                
            enriched_videos.append({
                "id": vid["id"],
                "video_url": get_valid_video_url(vid["video_url"], trans["language"]),
                "status": vid["status"],
                "approval_status": vid["approval_status"],
                "version": vid["version"],
                "youtube_url": vid.get("youtube_url"),
                "youtube_id": vid.get("youtube_id"),
                "views": vid.get("engagement_count", 0),
                "language": trans["language"],
                "product_name": product["name"],
                "product_id": product["id"],
                "campaign_title": script["title"]
            })
            
        return enriched_videos
    except Exception as e:
        logger.error(f"Error fetching enriched videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


