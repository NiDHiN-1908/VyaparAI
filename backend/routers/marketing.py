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
            prompt=t_data["prompt"]
        )

        # 4. Save Translations, Voiceovers, and Videos
        languages = ["Hindi", "Tamil", "Telugu", "Malayalam"]
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
            prompt=t_data["prompt"]
        )

        # 3. Save translations, voiceovers and videos
        languages = ["Hindi", "Tamil", "Telugu", "Malayalam"]
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

        # Publish file using service (triggers real upload or mock sandbox)
        publish_res = youtube_publish_svc.publish_video(
            video_path=str(settings.MEDIA_DIR / os.path.basename(video["video_url"])),
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
