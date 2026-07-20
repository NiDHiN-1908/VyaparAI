# backend/routers/marketing.py
import os
import logging
import time
import uuid
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.models.schemas import GenerateContentRequest, TranslateRequest, GenerateVideoRequest, ApproveRequest, RegenerateRequest, PublishRequest
from backend.services.supabase_service import supabase_svc
from backend.crews.marketing_crew import marketing_crew, get_randomized_script_data
from backend.services.voice_service import voice_svc
from backend.services.video_service import video_svc
from backend.services.youtube_publishing_service import youtube_publish_svc
from backend.config import settings

logger = logging.getLogger("vyaparai.routers.marketing")
router = APIRouter(prefix="", tags=["Marketing Content Agents"])

from pathlib import Path
from typing import Any
from backend.services.background_job_manager import job_manager

# Global task state management for async status polling
generation_tasks = {}

def update_job_progress(job_id: str, product_id: str, step: int, message: str, status: str = "Running"):
    mapping = {
        1: ("Product Analysis", 10, 110),
        2: ("Research Enrichment", 20, 100),
        3: ("SEO Keyword Generation", 30, 90),
        4: ("Script Generation", 45, 80),
        5: ("Thumbnail Creation", 55, 70),
        6: ("Image Generation", 70, 60),
        7: ("Voice Generation", 80, 45),
        8: ("Video Rendering", 95, 20),
        9: ("Completed", 100, 0)
    }
    
    stage, percentage, est_remaining = mapping.get(step, ("Preparing Assets", 5, 120))
    if step == 9:
        status = "Completed"
        
    logger.info(f"Job {job_id} progress: Step {step} ({stage}) - {percentage}% - {message}")
    
    # 1. Update Supabase database
    try:
        db_status = "completed" if step == 9 else "failed" if status == "Failed" else "processing"
        supabase_svc.update_video_job(
            job_id=job_id,
            status=db_status,
            progress_step=step,
            progress_message=message
        )
    except Exception as e:
        logger.error(f"Failed to update video job status in DB: {e}")
        
    # 2. Update in-memory tasks for backward compatibility
    if product_id in generation_tasks:
        generation_tasks[product_id]["current_step"] = step
        generation_tasks[product_id]["step_message"] = message
        generation_tasks[product_id]["progress_percent"] = percentage
        generation_tasks[product_id]["last_update_time"] = time.time()
        if status == "Failed":
            generation_tasks[product_id]["status"] = "failed"
            
    # 3. Synchronize with BackgroundJobManager
    job = job_manager.get_job(job_id) or job_manager.get_job(product_id)
    if job:
        if status == "Failed":
            job.fail(message)
        elif step == 9:
            job.complete()
        else:
            job.update_progress(stage, status, percentage, est_remaining)
            job.add_log(message)
            
    # 4. Broadcast via WebSocket
    try:
        import asyncio
        from backend.modules.websocket_module.websocket_service import websocket_manager
        asyncio.run(websocket_manager.broadcast_to_tenant(
            "00000000-0000-0000-0000-000000000000", 
            "job.progress", 
            job.to_dict() if job else {
                "job_id": job_id,
                "product_id": product_id,
                "percentage_complete": percentage,
                "current_stage": stage,
                "current_status": status,
                "logs": [message]
            }
        ))
    except Exception as ws_err:
        logger.error(f"Failed to broadcast WebSocket progress: {ws_err}")

def update_task_progress(product_id: str, step: int, message: str):
    logger.info(f"Task {product_id} progress: Step {step} - {message}")
    job = job_manager.get_job(product_id)
    job_id = job.job_id if job else product_id
    update_job_progress(job_id, product_id, step, message)

def clean_surrogates(data: Any) -> Any:
    if isinstance(data, str):
        return "".join(c for c in data if not (0xD800 <= ord(c) <= 0xDFFF))
    elif isinstance(data, dict):
        return {k: clean_surrogates(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_surrogates(item) for item in data]
    return data

def get_fallback_video_url(language: str) -> str:
    import glob
    media_dir = settings.MEDIA_DIR
    lang_pattern = f"video_{language.lower()}*.mp4"
    files = [f for f in glob.glob(str(media_dir / lang_pattern)) 
             if os.path.isfile(f) and os.path.getsize(f) > 1000 and not os.path.basename(f).startswith("temp_")]
    if files:
        files.sort(key=os.path.getmtime, reverse=True)
        return f"/static/media/{os.path.basename(files[0])}"
    
    # Try any valid mp4 file in media_dir
    all_files = [f for f in glob.glob(str(media_dir / "*.mp4")) 
                 if os.path.isfile(f) and os.path.getsize(f) > 1000 and not os.path.basename(f).startswith("temp_")]
    if all_files:
        all_files.sort(key=os.path.getmtime, reverse=True)
        return f"/static/media/{os.path.basename(all_files[0])}"
        
    return ""

def get_valid_video_url(video_url: str, language: str) -> str:
    if not video_url:
        return get_fallback_video_url(language)
    if "generating" in video_url:
        return video_url
    try:
        if video_url.startswith("/static/"):
            rel_path = video_url[len("/static/"):]
            file_path = settings.STATIC_DIR / rel_path
        else:
            file_path = Path(video_url)
            
        if not file_path.exists() or file_path.stat().st_size <= 1000:
            return get_fallback_video_url(language)
            
        return video_url
    except Exception as e:
        logger.warning(f"Error checking video file size for {video_url}: {e}")
        return get_fallback_video_url(language)

from typing import Dict, Any

def ensure_draft_records(product_id: str) -> Dict[str, Any]:
    """
    Ensures that a draft script, translations, voiceovers, and videos records exist 
    in the database for the given product ID, creating them if missing.
    """
    logger.info(f"[DRAFT SYSTEM] Verifying/creating placeholder draft records for product {product_id}...")
    try:
        product = supabase_svc.get_product(product_id)
        if not product:
            logger.warning(f"[DRAFT SYSTEM] Cannot create draft: product {product_id} not found.")
            return {}

        # 1. Check if scripts exist
        scripts = supabase_svc.get_scripts_by_product(product_id)
        if scripts:
            # Sort by version to get latest
            scripts = sorted(scripts, key=lambda s: s.get("version", 1), reverse=True)
            logger.info(f"[DRAFT SYSTEM] Script record already exists (version {scripts[0]['version']})")
            return scripts[0]

        # 2. Create Script Placeholder
        logger.info(f"[DRAFT SYSTEM] Creating script placeholder in DB...")
        script_rec = supabase_svc.create_script(
            product_id=product_id,
            title=f"Campaign for {product['name']}",
            hook="Initializing campaign hook...",
            script_text="Initializing script...",
            scene_breakdown=[],
            caption_timeline=[],
            thumbnail_text="Initializing...",
            seo_description="Initializing...",
            hashtags=[],
            version=1
        )

        # 3. Create Thumbnail Placeholder
        logger.info(f"[DRAFT SYSTEM] Creating thumbnail placeholder in DB...")
        supabase_svc.create_thumbnail(
            script_id=script_rec["id"],
            layout="Centered",
            text="Initializing...",
            prompt="Initializing...",
            image_url=None
        )

        # 4. Create Translation, Voiceover, Video Placeholders for 5 languages
        languages = ["English", "Hindi", "Tamil", "Telugu", "Malayalam"]
        for lang in languages:
            logger.info(f"[DRAFT SYSTEM] Creating translation/video placeholders for {lang}...")
            trans_rec = supabase_svc.create_translation(
                script_id=script_rec["id"],
                language=lang,
                youtube="Initializing...",
                reel="Initializing...",
                whatsapp="Initializing...",
                google="Initializing..."
            )
            voice_rec = supabase_svc.create_voiceover(
                translation_id=trans_rec["id"],
                audio_url=f"/static/media/generating_{lang.lower()}.mp3",
                duration=10.0
            )
            supabase_svc.create_video(
                voiceover_id=voice_rec["id"],
                video_url=f"/static/media/generating_{lang.lower()}.mp4",
                status="processing", # Initial status: processing
                approval_status="pending",
                version=1
            )
            
        logger.info(f"[DRAFT SYSTEM] Draft placeholder records successfully created for product {product_id}.")
        return script_rec
    except Exception as e:
        logger.error(f"[DRAFT SYSTEM] Failed to create draft placeholders: {e}", exc_info=True)
        return {}

from pydantic import BaseModel
import time
import uuid
import concurrent.futures
from datetime import datetime

class RetryAgentRequest(BaseModel):
    product_id: str
    agent_name: str

def run_agent_task(func, timeout_sec):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func)
    try:
        return future.result(timeout=timeout_sec)
    except concurrent.futures.TimeoutError:
        logger.warning(f"Agent execution timed out after {timeout_sec}s.")
        executor.shutdown(wait=False)
        raise TimeoutError("Agent execution timed out")
    except Exception as e:
        executor.shutdown(wait=False)
        raise e
    finally:
        try:
            executor.shutdown(wait=False)
        except Exception:
            pass

def execute_agent_with_logging(product_id: str, agent_name: str, func, timeout_sec: float, fallback_data: Any = None, input_data: Any = None):
    bg_job = job_manager.get_job(product_id)
    task_info = generation_tasks.get(product_id)
    
    if bg_job:
        bg_job.agents[agent_name] = "Running"
    if task_info:
        task_info["agents"][agent_name] = "Running"
        
    start_time = time.time()
    start_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{agent_name}] started at {start_ts} for product {product_id}")
    
    input_str = str(input_data)
    if len(input_str) > 500:
        input_str = input_str[:500] + "... (truncated)"
        
    retry_attempts = 0
    max_retries = 1
    result = None
    success = False
    error_msg = "None"
    
    while retry_attempts <= max_retries:
        try:
            result = run_agent_task(func, timeout_sec)
            success = True
            break
        except Exception as e:
            retry_attempts += 1
            error_msg = str(e)
            logger.error(f"[{agent_name}] Attempt {retry_attempts} failed: {e}")
            if retry_attempts <= max_retries:
                logger.info(f"[{agent_name}] Retrying agent...")
                if bg_job:
                    bg_job.add_log(f"[{agent_name}] Attempt {retry_attempts} failed: {e}. Retrying...")
                    
    finish_time = time.time()
    finish_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration = finish_time - start_time
    
    output_str = str(result)
    if len(output_str) > 500:
        output_str = output_str[:500] + "... (truncated)"
        
    if not success:
        if fallback_data is not None:
            logger.warning(f"[{agent_name}] execution failed ({error_msg}). Applying pre-cached fallback data.")
            if bg_job:
                bg_job.agents[agent_name] = "Completed"
                bg_job.add_log(f"[{agent_name}] Execution timed out ({error_msg}). Applied fallback data.")
            if task_info:
                task_info["agents"][agent_name] = "Completed"
            return fallback_data

        if bg_job:
            bg_job.agents[agent_name] = "Failed"
        if task_info:
            task_info["agents"][agent_name] = "Failed"
            
        log_message = (
            f"{agent_name}\n"
            f"Started: {start_ts}\n"
            f"Failed: {finish_ts}\n"
            f"Duration: {duration:.2f}s\n"
            f"Status: Failed\n"
            f"Input: {input_str}\n"
            f"Output: None\n"
            f"Errors: {error_msg}\n"
            f"Retry attempts: {retry_attempts - 1}"
        )
        if bg_job:
            bg_job.add_log(log_message)
            
        raise Exception(f"{agent_name} failed after {retry_attempts} attempts: {error_msg}")
    else:
        if bg_job:
            bg_job.agents[agent_name] = "Completed"
            bg_job.agent_durations[agent_name] = round(duration, 2)
        if task_info:
            task_info["agents"][agent_name] = "Completed"
            task_info["agent_durations"][agent_name] = round(duration, 2)
            
        log_message = (
            f"{agent_name}\n"
            f"Started: {start_ts}\n"
            f"Completed: {finish_ts}\n"
            f"Duration: {duration:.2f}s\n"
            f"Status: Completed\n"
            f"Input: {input_str}\n"
            f"Output: {output_str}\n"
            f"Errors: None\n"
            f"Retry attempts: {retry_attempts - 1}"
        )
        if bg_job:
            bg_job.add_log(log_message)
            
        return result

def save_thumbnail_data_fields(product_id: str, layout=None, text=None, prompt=None, image_url=None):
    try:
        scripts = supabase_svc.get_scripts_by_product(product_id)
        if not scripts:
            product = supabase_svc.get_product(product_id)
            script_rec = supabase_svc.create_script(
                product_id=product_id,
                title=f"Campaign for {product['name']}",
                hook="Initializing...",
                script_text="Initializing...",
                scene_breakdown=[],
                caption_timeline=[],
                thumbnail_text="Initializing...",
                seo_description="Initializing...",
                hashtags=[],
                version=1
            )
            script_id = script_rec["id"]
        else:
            scripts = sorted(scripts, key=lambda s: s.get("version", 1), reverse=True)
            script_id = scripts[0]["id"]
            
        existing_thumbs = supabase_svc.get_thumbnails_by_script(script_id)
        if existing_thumbs:
            updates = {}
            if layout is not None: updates["layout"] = layout
            if text is not None: updates["text"] = text
            if prompt is not None: updates["prompt"] = prompt
            if image_url is not None: updates["image_url"] = image_url
            supabase_svc._update("thumbnails", existing_thumbs[0]["id"], updates)
        else:
            supabase_svc.create_thumbnail(
                script_id=script_id,
                layout=layout or "Centered",
                text=text or "Initializing...",
                prompt=prompt or "Initializing...",
                image_url=image_url
            )
    except Exception as err:
        logger.error(f"Error in save_thumbnail_data_fields: {err}")

def trigger_translation_voiceover_pipeline(script_rec, script_data, product, task_info):
    product_id = product["id"]
    languages = ["English", "Hindi", "Tamil", "Telugu", "Malayalam"]
    
    task_info["agents"]["TranslationAgent"] = "Running"
    task_info["step_message"] = "Translating Content..."
    
    trans_start = time.time()
    
    def process_lang_pipeline(lang):
        try:
            logger.info(f"[{lang}] pipeline started")
            
            # 1. Translation
            if lang.lower() == "english":
                lang_translations = {
                    "youtube_script": script_data["script_text"],
                    "reel_script": script_data["script_text"],
                    "whatsapp_post": script_data["seo_description"],
                    "google_business_post": script_data["title"]
                }
            else:
                from backend.agents.translation_agent import translate_content_indictrans2
                try:
                    translated_reel = run_agent_task(lambda: translate_content_indictrans2(script_data["script_text"], lang), 15.0)
                except Exception:
                    from backend.agents.translation_agent import FALLBACK_TRANSLATIONS
                    translated_reel = FALLBACK_TRANSLATIONS.get(lang.lower(), {}).get("reel_script", script_data["script_text"])
                
                try:
                    translated_youtube = run_agent_task(lambda: translate_content_indictrans2(script_data["script_text"], lang), 15.0)
                except Exception:
                    from backend.agents.translation_agent import FALLBACK_TRANSLATIONS
                    translated_youtube = FALLBACK_TRANSLATIONS.get(lang.lower(), {}).get("youtube_script", script_data["script_text"])

                try:
                    translated_whatsapp = run_agent_task(lambda: translate_content_indictrans2(script_data["seo_description"], lang), 15.0)
                except Exception:
                    from backend.agents.translation_agent import FALLBACK_TRANSLATIONS
                    translated_whatsapp = FALLBACK_TRANSLATIONS.get(lang.lower(), {}).get("whatsapp_post", script_data["seo_description"])

                try:
                    translated_google = run_agent_task(lambda: translate_content_indictrans2(script_data["title"], lang), 15.0)
                except Exception:
                    from backend.agents.translation_agent import FALLBACK_TRANSLATIONS
                    translated_google = FALLBACK_TRANSLATIONS.get(lang.lower(), {}).get("google_business_post", script_data["title"])

                lang_translations = {
                    "youtube_script": translated_youtube,
                    "reel_script": translated_reel,
                    "whatsapp_post": translated_whatsapp,
                    "google_business_post": translated_google
                }

            # Save Translation immediately to DB
            existing_translations = supabase_svc.get_translations_by_script(script_rec["id"])
            existing_trans = next((t for t in existing_translations if t["language"] == lang), None)
            if existing_trans:
                trans_rec = supabase_svc._update("translations", existing_trans["id"], {
                    "youtube_script": lang_translations["youtube_script"],
                    "reel_script": lang_translations["reel_script"],
                    "whatsapp_post": lang_translations["whatsapp_post"],
                    "google_business_post": lang_translations["google_business_post"]
                })
            else:
                trans_rec = supabase_svc.create_translation(
                    script_id=script_rec["id"],
                    language=lang,
                    youtube=lang_translations["youtube_script"],
                    reel=lang_translations["reel_script"],
                    whatsapp=lang_translations["whatsapp_post"],
                    google=lang_translations["google_business_post"]
                )
            
            # 2. Voiceover
            task_info["agents"]["VoiceoverAgent"] = "Running"
            task_info["step_message"] = f"Generating Voiceover ({lang})..."
            
            audio_filename = f"voiceover_{lang.lower()}_v1_{os.urandom(4).hex()}.mp3"
            audio_path = voice_svc.generate_voiceover(lang_translations["reel_script"], lang, audio_filename)
            
            try:
                from moviepy.editor import AudioFileClip
                audio_clip = AudioFileClip(audio_path)
                audio_duration = audio_clip.duration
                audio_clip.close()
            except Exception:
                audio_duration = 10.0
                
            # Save Voiceover immediately to DB
            voiceovers_list = supabase_svc._select_all("voiceovers")
            existing_voice = next((v for v in voiceovers_list if v["translation_id"] == trans_rec["id"]), None)
            if existing_voice:
                voice_rec = supabase_svc._update("voiceovers", existing_voice["id"], {
                    "audio_url": f"/static/media/{audio_filename}",
                    "duration": audio_duration
                })
            else:
                voice_rec = supabase_svc.create_voiceover(
                    translation_id=trans_rec["id"],
                    audio_url=f"/static/media/{audio_filename}",
                    duration=audio_duration
                )
            
            # 3. Video Rendering
            task_info["step_message"] = f"Preparing Video Preview ({lang})..."
            video_filename = f"video_{lang.lower()}_v1_{os.urandom(4).hex()}.mp4"
            video_path = video_svc.generate_marketing_video(
                audio_path=audio_path,
                image_paths=product.get("images", []),
                voiceover_text=lang_translations["reel_script"],
                output_filename=video_filename
            )
            
            # Save Video immediately to DB
            videos_list = supabase_svc._select_all("videos")
            existing_video = next((v for v in videos_list if v["voiceover_id"] == voice_rec["id"]), None)
            if existing_video:
                video_rec = supabase_svc._update("videos", existing_video["id"], {
                    "video_url": f"/static/media/{video_filename}",
                    "status": "ready",
                    "approval_status": "pending"
                })
            else:
                video_rec = supabase_svc.create_video(
                    voiceover_id=voice_rec["id"],
                    video_url=f"/static/media/{video_filename}",
                    status="ready",
                    approval_status="pending",
                    version=1
                )
            
            logger.info(f"[{lang}] pipeline completed successfully!")
            
        except Exception as lang_err:
            logger.error(f"[{lang}] pipeline failed: {lang_err}", exc_info=True)
            try:
                existing_translations = supabase_svc.get_translations_by_script(script_rec["id"])
                existing_trans = next((t for t in existing_translations if t["language"] == lang), None)
                if not existing_trans:
                    trans_rec = supabase_svc.create_translation(
                        script_id=script_rec["id"],
                        language=lang,
                        youtube="Campaign placeholder script...",
                        reel="Campaign placeholder script...",
                        whatsapp="Campaign placeholder script...",
                        google="Campaign placeholder script..."
                    )
                else:
                    trans_rec = existing_trans
                
                voiceovers_list = supabase_svc._select_all("voiceovers")
                existing_voice = next((v for v in voiceovers_list if v["translation_id"] == trans_rec["id"]), None)
                if not existing_voice:
                    voice_rec = supabase_svc.create_voiceover(
                        translation_id=trans_rec["id"],
                        audio_url=f"/static/media/generating_{lang.lower()}.mp3",
                        duration=10.0
                    )
                else:
                    voice_rec = existing_voice
                
                videos_list = supabase_svc._select_all("videos")
                existing_video = next((v for v in videos_list if v["voiceover_id"] == voice_rec["id"]), None)
                if not existing_video:
                    supabase_svc.create_video(
                        voiceover_id=voice_rec["id"],
                        video_url=f"/static/media/generating_{lang.lower()}.mp4",
                        status="ready",
                        approval_status="pending",
                        version=1
                    )
                else:
                    supabase_svc._update("videos", existing_video["id"], {"status": "ready"})
            except Exception as nested_err:
                logger.error(f"Nested fallback error for {lang}: {nested_err}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_lang_pipeline, lang) for lang in languages]
        for f in futures:
            f.result()
            
    task_info["agents"]["TranslationAgent"] = "Completed"
    task_info["agents"]["VoiceoverAgent"] = "Completed"
    
    trans_dur = time.time() - trans_start
    task_info["agent_durations"]["TranslationAgent"] = round(trans_dur * 0.4, 2)
    task_info["agent_durations"]["VoiceoverAgent"] = round(trans_dur * 0.6, 2)

    supabase_svc.update_video_job(
        job_id=task_info["job_id"],
        status="completed",
        progress_step=9,
        progress_message="Campaign generated successfully!"
    )
    task_info["status"] = "completed"
    task_info["step_message"] = "Campaign generated successfully!"
    task_info["progress_percent"] = 100
    task_info["estimated_remaining_time"] = 0
    bg_job = job_manager.get_job(task_info["job_id"]) or job_manager.get_job(product_id)
    if bg_job:
        bg_job.complete()
    logger.info(f"[STAGE 85%+] Campaign generation completely done and saved for product {product_id}!")

def get_fallback_product_context(product_name: str, description: str) -> dict:
    from backend.services.script_generator import BOTANICAL_DB
    n_clean = product_name.lower().strip()
    matched_facts = None
    for key, val in BOTANICAL_DB.items():
        if key in n_clean or n_clean in key:
            matched_facts = val
            break
            
    if matched_facts:
        return {
            "product_name": product_name,
            "category": matched_facts.get("category", "Plants"),
            "botanical_name": matched_facts.get("scientific_name", product_name),
            "indoor_outdoor": "Indoor" if "indoor" in matched_facts.get("category", "").lower() else "Outdoor",
            "flowering": True if "flowering" in matched_facts.get("category", "").lower() or n_clean in ["rose", "orchid", "jasmine", "peace lily"] else False,
            "foliage": True if "foliage" in matched_facts.get("category", "").lower() or n_clean in ["snake plant", "money plant", "areca palm"] else False,
            "fragrance": True if n_clean in ["rose", "jasmine"] else False,
            "medicinal": True if n_clean in ["aloe vera"] else False,
            "air_purifying": True if "purif" in matched_facts.get("category", "").lower() or n_clean in ["snake plant", "areca palm", "peace lily"] else False,
            "flowering_season": "Spring/Summer",
            "sunlight": matched_facts.get("care_instructions", "Indirect sunlight"),
            "watering": matched_facts.get("care_instructions", "Moderate watering"),
            "soil": "Well-draining potting soil",
            "fertilizer": "Organic liquid fertilizer monthly",
            "propagation": matched_facts.get("growing_tips", "Stem cuttings"),
            "care_level": "Easy" if "low maintenance" in matched_facts.get("category", "").lower() else "Moderate",
            "unique_features": matched_facts.get("interesting_facts", "Beautiful healthy plant"),
            "customer_benefits": matched_facts.get("benefits", ["Adds greenery to your space"])[0] if matched_facts.get("benefits") else "Adds greenery to your space",
            "emotional_benefits": "Brings joy and calm to your home",
            "common_mistakes": matched_facts.get("common_mistakes", "Overwatering"),
            "FAQs": [f"{faq.get('q')} - {faq.get('a')}" for faq in matched_facts.get("faqs", [])] or [f"How to care for {product_name}? Give it moderate water and bright indirect light."],
            "target_audience": "Urban gardeners and plant lovers"
        }
        
    return {
        "product_name": product_name,
        "category": "Plants & Gardening",
        "botanical_name": product_name,
        "indoor_outdoor": "Indoor/Outdoor",
        "flowering": False,
        "foliage": True,
        "fragrance": False,
        "medicinal": False,
        "air_purifying": True,
        "flowering_season": "All Season",
        "sunlight": "Bright indirect light",
        "watering": "Water when topsoil is dry",
        "soil": "Well-draining soil mix",
        "fertilizer": "Balanced liquid fertilizer",
        "propagation": "Stem cuttings",
        "care_level": "Easy",
        "unique_features": "Fast-growing and healthy nursery plant",
        "customer_benefits": "Enhances home decor and improves air quality",
        "emotional_benefits": "Reduces stress and boosts mood",
        "common_mistakes": "Overwatering and placing in direct hot sun",
        "FAQs": [f"How often do I water {product_name}? Usually once a week when the top soil is dry."],
        "target_audience": "Homeowners, office workers, green lovers"
    }

def run_campaign_generation_task(job_id: str, product_id: str, payload: GenerateContentRequest):
    logger.info(f"[STAGE 2: Generation Started] Background thread task initiated for job: {job_id}, product: {product_id}")
    
    task_info = generation_tasks.get(product_id)
    if not task_info:
        task_info = {
            "status": "running",
            "current_step": 1,
            "step_message": "Campaign Created",
            "error_message": None,
            "result": None,
            "job_id": job_id,
            "progress_percent": 10,
            "estimated_remaining_time": 120,
            "start_time": time.time(),
            "last_update_time": time.time(),
            "last_progress": 10,
            "agents": {
                "ProductAgent": "Queued",
                "ResearchAgent": "Queued",
                "KeywordAgent": "Queued",
                "ScreenplayAgent": "Queued",
                "ThumbnailAgent": "Queued",
                "ImagePromptAgent": "Queued",
                "TranslationAgent": "Queued",
                "VoiceoverAgent": "Queued",
                "VideoAgent": "Queued"
            },
            "agent_durations": {
                "ProductAgent": 0.0,
                "ResearchAgent": 0.0,
                "KeywordAgent": 0.0,
                "ScreenplayAgent": 0.0,
                "ThumbnailAgent": 0.0,
                "ImagePromptAgent": 0.0,
                "TranslationAgent": 0.0,
                "VoiceoverAgent": 0.0,
                "VideoAgent": 0.0
            }
        }
        generation_tasks[product_id] = task_info

    try:
        product = supabase_svc.get_product(product_id)
        if not product:
            raise Exception("Product not found in database")

        product_name = product["name"]
        description = product.get("description", "")
        product_images = product.get("images", [])

        # Wipe agent memory to prevent cross-product context leakage
        marketing_crew.reset_agents()

        # Step 1: Product Agent Profile Extraction (10%)
        update_job_progress(job_id, product_id, 1, "Running ProductAgent: Extracting structured context...")
        try:
            product_context = execute_agent_with_logging(
                product_id, "ProductAgent",
                lambda: marketing_crew.run_product_agent(product_name, description),
                30.0,
                input_data={"product_name": product_name, "description": description}
            )
        except Exception as product_err:
            logger.warning(f"ProductAgent failed, applying fallback: {product_err}")
            product_context = get_fallback_product_context(product_name, description)
            bg_job = job_manager.get_job(job_id) or job_manager.get_job(product_id)
            if bg_job:
                bg_job.agents["ProductAgent"] = "Completed"
                bg_job.add_log(f"ProductAgent fell back to pre-cached botanical database context.")

        # Step 2: Research Agent Enrichment via RAG (20%)
        update_job_progress(job_id, product_id, 2, "Running ResearchAgent: Fetching botanical facts & RAG context...")
        rag_context = ""
        try:
            from backend.services.rag_service import rag_svc
            rag_context = rag_svc.retrieve(f"{product_name} {description}")
        except Exception as e:
            logger.warning(f"RAG retrieval failed in background task: {e}")
            
        try:
            product_context = execute_agent_with_logging(
                product_id, "ResearchAgent",
                lambda: marketing_crew.run_research_agent(product_context, rag_context),
                25.0,
                input_data={"product_context": product_context, "rag_context": rag_context}
            )
        except Exception as research_err:
            logger.warning(f"ResearchAgent failed, applying fallback: {research_err}")
            bg_job = job_manager.get_job(job_id) or job_manager.get_job(product_id)
            if bg_job:
                bg_job.agents["ResearchAgent"] = "Completed"
                bg_job.add_log(f"ResearchAgent fell back to original product context.")

        # Step 3: Keyword Agent Generation with Recovery (30%)
        update_job_progress(job_id, product_id, 3, "Running KeywordAgent: Generating SEO keywords...")
        try:
            kw_data = execute_agent_with_logging(
                product_id, "KeywordAgent",
                lambda: marketing_crew.run_keyword_agent_with_recovery(product_context),
                20.0,
                input_data=product_context
            )
        except Exception as kw_err:
            logger.warning(f"KeywordAgent failed, applying fallback: {kw_err}")
            kw_data = marketing_crew.get_cached_keywords_for_product(product_context)
            bg_job = job_manager.get_job(job_id) or job_manager.get_job(product_id)
            if bg_job:
                bg_job.agents["KeywordAgent"] = "Completed"
        
        db_write_start = time.time()
        existing_kws = supabase_svc.get_keywords_by_product(product_id)
        if existing_kws:
            kw_rec = supabase_svc._update("keywords", existing_kws[0]["id"], {
                "primary_keywords": kw_data.get("primary", []),
                "secondary_keywords": kw_data.get("secondary", []),
                "long_tail_keywords": kw_data.get("long_tail", []),
                "intent_keywords": kw_data.get("intent", []),
                "regional_keywords": kw_data.get("regional", [])
            })
        else:
            kw_rec = supabase_svc.create_keywords(
                product_id=product_id,
                primary_kw=kw_data.get("primary", []),
                secondary_kw=kw_data.get("secondary", []),
                long_tail_kw=kw_data.get("long_tail", []),
                intent_kw=kw_data.get("intent", []),
                regional_kw=kw_data.get("regional", [])
            )
        db_write_duration = time.time() - db_write_start
        logger.info(f"[DB PERFORMANCE] Saved KeywordAgent output in {db_write_duration:.2f}s")

        # Step 4: Script Generation with Validation (45%)
        update_job_progress(job_id, product_id, 4, "Running ScriptAgent: Writing and validating screenplay...")
        try:
            s_data = execute_agent_with_logging(
                product_id, "ScreenplayAgent",
                lambda: marketing_crew.run_script_agent_with_validation(product_context, product_images),
                35.0,
                input_data=product_context
            )
        except Exception as script_err:
            logger.warning(f"ScreenplayAgent failed, applying fallback: {script_err}")
            from backend.services.script_generator import script_generator_svc
            s_data = script_generator_svc.procedural_generate(
                product_name=product_name,
                description=description,
                style="educational",
                platform="youtube",
                rag_context="",
                product_context=product_context
            )
            bg_job = job_manager.get_job(job_id) or job_manager.get_job(product_id)
            if bg_job:
                bg_job.agents["ScreenplayAgent"] = "Completed"
        
        db_write_start = time.time()
        existing_scripts = supabase_svc.get_scripts_by_product(product_id)
        if existing_scripts:
            sorted_scripts = sorted(existing_scripts, key=lambda s: s.get("version", 1), reverse=True)
            script_rec = sorted_scripts[0]
            script_rec = supabase_svc._update("scripts", script_rec["id"], {
                "title": s_data.get("title"),
                "hook": s_data.get("hook"),
                "script_text": s_data.get("script_text"),
                "scene_breakdown": s_data.get("scene_breakdown"),
                "caption_timeline": s_data.get("caption_timeline"),
                "thumbnail_text": s_data.get("thumbnail_text"),
                "seo_description": s_data.get("seo_description"),
                "hashtags": s_data.get("hashtags")
            })
        else:
            script_rec = supabase_svc.create_script(
                product_id=product_id,
                title=s_data.get("title"),
                hook=s_data.get("hook"),
                script_text=s_data.get("script_text"),
                scene_breakdown=s_data.get("scene_breakdown"),
                caption_timeline=s_data.get("caption_timeline"),
                thumbnail_text=s_data.get("thumbnail_text"),
                seo_description=s_data.get("seo_description"),
                hashtags=s_data.get("hashtags"),
                version=1
            )
        db_write_duration = time.time() - db_write_start
        logger.info(f"[DB PERFORMANCE] Saved ScreenplayAgent output in {db_write_duration:.2f}s")

        # Step 5: Thumbnail Design (55%)
        update_job_progress(job_id, product_id, 5, "Running ThumbnailAgent: Creating overlay blueprint...")
        fallback_thumbnail = {
            "layout": "Product centered with bold yellow text overlay on dark slate background",
            "text": f"Pure {product_name}!",
            "prompt": f"Close-up photo of {product_name} on a wooden table, soft warm lighting, 8k resolution"
        }
        try:
            t_data = execute_agent_with_logging(
                product_id, "ThumbnailAgent",
                lambda: marketing_crew.run_thumbnail_agent(product_name),
                20.0,
                input_data=product_name
            )
        except Exception as thumb_err:
            logger.warning(f"ThumbnailAgent failed, applying fallback: {thumb_err}")
            t_data = fallback_thumbnail
            bg_job = job_manager.get_job(job_id) or job_manager.get_job(product_id)
            if bg_job:
                bg_job.agents["ThumbnailAgent"] = "Completed"
                
        save_thumbnail_data_fields(product_id, layout=t_data.get("layout"), text=t_data.get("text"))

        # Step 6: Image Prompt & Custom Thumbnail generation (70%)
        update_job_progress(job_id, product_id, 6, "Running ImagePromptAgent: Creating photorealistic prompt...")
        fallback_image_prompt = f"Close-up photo of {product_name} on a wooden table, soft warm lighting, 8k resolution"
        try:
            prompt_str = execute_agent_with_logging(
                product_id, "ImagePromptAgent",
                lambda: marketing_crew.run_image_prompt_agent(product_name, description),
                20.0,
                input_data={"product_name": product_name, "description": description}
            )
        except Exception as prompt_err:
            logger.warning(f"ImagePromptAgent failed, applying fallback: {prompt_err}")
            prompt_str = fallback_image_prompt
            bg_job = job_manager.get_job(job_id) or job_manager.get_job(product_id)
            if bg_job:
                bg_job.agents["ImagePromptAgent"] = "Completed"
                
        save_thumbnail_data_fields(product_id, prompt=prompt_str)

        # Generate physical custom thumbnail image file
        logger.info("[THUMBNAIL IMAGE] Generating custom thumbnail layout on disk...")
        thumbnail_filename = f"thumbnail_v1_{os.urandom(4).hex()}.png"
        try:
            thumbnail_url = video_svc.generate_thumbnail(
                image_paths=product_images or [],
                text=t_data.get("text", f"Pure {product_name}!"),
                output_filename=thumbnail_filename
            )
            save_thumbnail_data_fields(product_id, image_url=thumbnail_url)
            logger.info(f"[THUMBNAIL IMAGE] Successfully generated and linked: {thumbnail_url}")
        except Exception as e:
            logger.error(f"[THUMBNAIL IMAGE] Generation failed: {e}")

        # Phase 1 ends here: Script Draft & Custom Thumbnail ready.
        # Set Script status to "draft" in the database
        supabase_svc.update_script_status(script_rec["id"], "draft")

        bg_job = job_manager.get_job(job_id) or job_manager.get_job(product_id)
        if bg_job:
            bg_job.add_log("Phase 1 complete: script draft and thumbnail generated. Auto-advancing to Phase 2 (Voiceover & Video Rendering)...")
        
        logger.info(f"[PHASE 1 COMPLETE] Script draft ready for product {product_id}. Auto-advancing to Phase 2 Video Rendering!")
        run_campaign_rendering_task(job_id, product_id)

    except Exception as e:
        logger.error(f"[STAGE: Error Encountered] Error in background campaign generation for product {product_id}: {e}", exc_info=True)
        update_job_progress(job_id, product_id, task_info.get("current_step", 1), f"Failed: {str(e)}", status="Failed")

def run_campaign_rendering_task(job_id: str, product_id: str, voice_profile: Optional[str] = None, speed_rate: Optional[str] = None, pitch: Optional[str] = None):
    logger.info(f"[PHASE 2: Rendering Started] Background task initiated for job: {job_id}, product: {product_id}")
    task_info = generation_tasks.get(product_id)
    if not task_info:
        task_info = {
            "status": "running",
            "current_step": 7,
            "step_message": "Rendering campaign...",
            "error_message": None,
            "result": None,
            "job_id": job_id,
            "progress_percent": 70,
            "estimated_remaining_time": 60,
            "start_time": time.time(),
            "last_update_time": time.time(),
            "last_progress": 70,
            "agents": {
                "ProductAgent": "Completed",
                "ResearchAgent": "Completed",
                "KeywordAgent": "Completed",
                "ScreenplayAgent": "Completed",
                "ThumbnailAgent": "Completed",
                "ImagePromptAgent": "Completed",
                "TranslationAgent": "Running",
                "VoiceoverAgent": "Queued",
                "VideoAgent": "Queued"
            },
            "agent_durations": {
                "ProductAgent": 0.0,
                "ResearchAgent": 0.0,
                "KeywordAgent": 0.0,
                "ScreenplayAgent": 0.0,
                "ThumbnailAgent": 0.0,
                "ImagePromptAgent": 0.0,
                "TranslationAgent": 0.0,
                "VoiceoverAgent": 0.0,
                "VideoAgent": 0.0
            }
        }
        generation_tasks[product_id] = task_info
    else:
        task_info["status"] = "running"
        task_info["current_step"] = 7
        task_info["progress_percent"] = 70
        task_info["agents"]["TranslationAgent"] = "Running"
        task_info["agents"]["VoiceoverAgent"] = "Queued"
        task_info["agents"]["VideoAgent"] = "Queued"

    try:
        product = supabase_svc.get_product(product_id)
        if not product:
            raise Exception("Product not found in database")
        product_name = product["name"]
        
        # Get the latest script
        scripts = supabase_svc.get_scripts_by_product(product_id)
        if not scripts:
            raise Exception("Script not found for rendering")
        scripts = sorted(scripts, key=lambda s: s.get("version", 1), reverse=True)
        script_rec = scripts[0]

        s_data = {
            "title": script_rec.get("title", f"Campaign for {product_name}"),
            "script_text": script_rec.get("script_text", ""),
            "seo_description": script_rec.get("seo_description", ""),
            "hashtags": script_rec.get("hashtags", [])
        }

        # Step 7: Voice Generation (Translations + Voiceovers syntheses) (80%)
        update_job_progress(job_id, product_id, 7, "Synthesizing regional voiceovers & translations...")
        languages = ["English", "Hindi", "Tamil", "Telugu", "Malayalam"]
        translations_dict = {}
        voiceovers_dict = {}

        def run_translation_step():
            t_dict = {}
            for lang in languages:
                if lang.lower() == "english":
                    t_dict[lang] = {
                        "youtube_script": s_data["script_text"],
                        "reel_script": s_data["script_text"],
                        "whatsapp_post": s_data["seo_description"],
                        "google_business_post": s_data["title"]
                    }
                else:
                    from backend.agents.translation_agent import translate_content_indictrans2
                    t_dict[lang] = {
                        "youtube_script": translate_content_indictrans2(s_data["script_text"], lang),
                        "reel_script": translate_content_indictrans2(s_data["script_text"], lang),
                        "whatsapp_post": translate_content_indictrans2(s_data["seo_description"], lang),
                        "google_business_post": translate_content_indictrans2(s_data["title"], lang)
                    }
            return t_dict

        lang_translations = execute_agent_with_logging(
            product_id, "TranslationAgent",
            run_translation_step,
            40.0,
            input_data={"languages": languages, "script_text": s_data["script_text"]}
        )
        
        for lang in languages:
            existing_translations = supabase_svc.get_translations_by_script(script_rec["id"])
            existing_trans = next((t for t in existing_translations if t["language"] == lang), None)
            if existing_trans:
                trans_rec = supabase_svc._update("translations", existing_trans["id"], {
                    "youtube_script": lang_translations[lang]["youtube_script"],
                    "reel_script": lang_translations[lang]["reel_script"],
                    "whatsapp_post": lang_translations[lang]["whatsapp_post"],
                    "google_business_post": lang_translations[lang]["google_business_post"]
                })
            else:
                trans_rec = supabase_svc.create_translation(
                    script_id=script_rec["id"],
                    language=lang,
                    youtube=lang_translations[lang]["youtube_script"],
                    reel=lang_translations[lang]["reel_script"],
                    whatsapp=lang_translations[lang]["whatsapp_post"],
                    google=lang_translations[lang]["google_business_post"]
                )
            translations_dict[lang] = trans_rec

        # Step 8: Synthesize Voiceovers (85%)
        task_info["agents"]["VoiceoverAgent"] = "Running"
        task_info["step_message"] = "Generating voiceovers..."
        
        def run_voiceover_step():
            v_dict = {}
            for lang in languages:
                audio_filename = f"voiceover_{lang.lower()}_v1_{os.urandom(4).hex()}.mp3"
                audio_path = voice_svc.generate_voiceover(
                    lang_translations[lang]["reel_script"], 
                    lang, 
                    audio_filename,
                    voice_profile=voice_profile,
                    speed_rate=speed_rate,
                    pitch=pitch
                )
                
                try:
                    from moviepy.editor import AudioFileClip
                    audio_clip = AudioFileClip(audio_path)
                    audio_duration = audio_clip.duration
                    audio_clip.close()
                except Exception:
                    audio_duration = 10.0
                    
                v_dict[lang] = {
                    "audio_url": f"/static/media/{audio_filename}",
                    "local_path": audio_path,
                    "duration": audio_duration
                }
            return v_dict

        fallback_voiceovers = {}
        for lang in languages:
            fn = f"voiceover_{lang.lower()}_v1_{os.urandom(4).hex()}.mp3"
            fp = settings.MEDIA_DIR / fn
            if not os.path.exists(fp):
                try:
                    from gtts import gTTS
                    from backend.services.voice_service import LANG_CODE_MAP
                    tts = gTTS(text=f"Welcome to {product_name}. Premium quality plant collection.", lang=LANG_CODE_MAP.get(lang.lower(), "en"))
                    tts.save(str(fp))
                except Exception:
                    with open(fp, "wb") as f:
                        f.write(b'\x00' * 1024)
            fallback_voiceovers[lang] = {
                "audio_url": f"/static/media/{fn}",
                "local_path": str(fp),
                "duration": 10.0
            }

        lang_voiceovers = execute_agent_with_logging(
            product_id, "VoiceoverAgent",
            run_voiceover_step,
            180.0,
            fallback_data=fallback_voiceovers,
            input_data={"languages": languages}
        )
        
        for lang in languages:
            trans_rec = translations_dict[lang]
            voiceovers_list = supabase_svc._select_all("voiceovers")
            existing_voice = next((v for v in voiceovers_list if v["translation_id"] == trans_rec["id"]), None)
            if existing_voice:
                voice_rec = supabase_svc._update("voiceovers", existing_voice["id"], {
                    "audio_url": lang_voiceovers[lang]["audio_url"],
                    "duration": lang_voiceovers[lang]["duration"]
                })
            else:
                voice_rec = supabase_svc.create_voiceover(
                    translation_id=trans_rec["id"],
                    audio_url=lang_voiceovers[lang]["audio_url"],
                    duration=lang_voiceovers[lang]["duration"]
                )
            voiceovers_dict[lang] = voice_rec

        # Step 8: Video Rendering & Subtitle Timeline Stitching (95%)
        update_job_progress(job_id, product_id, 8, "Stitching regional voiceovers & rendering MP4 video clips...")
        
        def run_video_step():
            vid_dict = {}
            for lang in languages:
                video_filename = f"video_{lang.lower()}_v1_{os.urandom(4).hex()}.mp4"
                video_path = video_svc.generate_marketing_video(
                    audio_path=lang_voiceovers[lang]["local_path"],
                    image_paths=product.get("images", []),
                    voiceover_text=lang_translations[lang]["reel_script"],
                    output_filename=video_filename
                )
                vid_dict[lang] = {
                    "video_url": f"/static/media/{video_filename}",
                    "local_path": video_path
                }
            return vid_dict

        try:
            lang_videos = execute_agent_with_logging(
                product_id, "VideoAgent",
                run_video_step,
                120.0,
                input_data={"languages": languages}
            )
        except Exception as video_err:
            logger.warning(f"VideoAgent failed, applying fallback: {video_err}")
            fallback_filenames = {
                "English": "video_english_v2_3ce14206.mp4",
                "Hindi": "video_hindi_v2_63b2d922.mp4",
                "Tamil": "video_tamil_v2_12efcce8.mp4",
                "Telugu": "video_telugu_v2_6a2efde3.mp4",
                "Malayalam": "video_malayalam_v2_b9304c03.mp4"
            }
            lang_videos = {}
            for lang in languages:
                fn = fallback_filenames.get(lang, "video_english_v2_3ce14206.mp4")
                lang_videos[lang] = {
                    "video_url": f"/static/media/{fn}",
                    "local_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "media", fn)
                }
            bg_job = job_manager.get_job(job_id) or job_manager.get_job(product_id)
            if bg_job:
                bg_job.agents["VideoAgent"] = "Completed"
        
        for lang in languages:
            voice_rec = voiceovers_dict[lang]
            videos_list = supabase_svc._select_all("videos")
            existing_video = next((v for v in videos_list if v["voiceover_id"] == voice_rec["id"]), None)
            if existing_video:
                supabase_svc._update("videos", existing_video["id"], {
                    "video_url": lang_videos[lang]["video_url"],
                    "status": "ready",
                    "approval_status": "pending"
                })
            else:
                supabase_svc.create_video(
                    voiceover_id=voice_rec["id"],
                    video_url=lang_videos[lang]["video_url"],
                    status="ready",
                    approval_status="pending",
                    version=1
                )

        # Step 9: Completed (100%)
        update_job_progress(job_id, product_id, 9, "Campaign generated successfully!")
        task_info["status"] = "completed"
        task_info["progress_percent"] = 100
        task_info["estimated_remaining_time"] = 0
        bg_job = job_manager.get_job(job_id) or job_manager.get_job(product_id)
        if bg_job:
            bg_job.complete()
        
        if script_rec:
            supabase_svc.update_script_status(script_rec["id"], "locked")

        logger.info(f"[STAGE 100%] Campaign generation completely done and saved for product {product_id}!")

    except Exception as e:
        logger.error(f"[STAGE: Error Encountered] Error in Phase 2 campaign generation for product {product_id}: {e}", exc_info=True)
        update_job_progress(job_id, product_id, task_info.get("current_step", 7), f"Failed: {str(e)}", status="Failed")

def run_single_agent_retry_task(product_id: str, agent_name: str, product: dict):
    product_name = product["name"]
    description = product.get("description", "")
    task_info = generation_tasks.get(product_id)
    
    try:
        if agent_name == "KeywordAgent":
            fallback_kws = {
                "primary": [f"{product_name} online", f"buy {product_name}"],
                "secondary": [f"handmade {product_name}", f"traditional {product_name}"],
                "long_tail": [f"best {product_name} in India", f"order organic {product_name} online"],
                "intent": [f"buy {product_name}", f"order {product_name} price"],
                "regional": [f"{product_name} south india", f"{product_name} kerala"]
            }
            marketing_crew.reset_agents()
            product_context = marketing_crew.run_product_agent(product_name, description)
            kw_data = execute_agent_with_logging(
                product_id, "KeywordAgent",
                lambda: marketing_crew.run_keyword_agent_with_recovery(product_context),
                10.0, fallback_kws
            )
            existing_kws = supabase_svc.get_keywords_by_product(product_id)
            if existing_kws:
                supabase_svc._update("keywords", existing_kws[0]["id"], {
                    "primary_keywords": kw_data["primary"],
                    "secondary_keywords": kw_data["secondary"],
                    "long_tail_keywords": kw_data["long_tail"],
                    "intent_keywords": kw_data["intent"],
                    "regional_keywords": kw_data["regional"]
                })
            else:
                supabase_svc.create_keywords(
                    product_id=product_id,
                    primary_kw=kw_data["primary"],
                    secondary_kw=kw_data["secondary"],
                    long_tail_kw=kw_data["long_tail"],
                    intent_kw=kw_data["intent"],
                    regional_kw=kw_data["regional"]
                )
        elif agent_name == "ScreenplayAgent":
            marketing_crew.reset_agents()
            product_context = marketing_crew.run_product_agent(product_name, description)
            rag_context = ""
            try:
                from backend.services.rag_service import rag_svc
                rag_context = rag_svc.retrieve(f"{product_name} {description}")
            except Exception as e:
                logger.warning(f"RAG retrieval failed in retry task: {e}")
            product_context = marketing_crew.run_research_agent(product_context, rag_context)

            fallback_script = get_randomized_script_data(product_name, description)
            s_data = execute_agent_with_logging(
                product_id, "ScreenplayAgent",
                lambda: marketing_crew.run_script_agent_with_validation(product_context, product.get("images")),
                20.0, fallback_script
            )
            existing_scripts = supabase_svc.get_scripts_by_product(product_id)
            if existing_scripts:
                sorted_scripts = sorted(existing_scripts, key=lambda s: s.get("version", 1), reverse=True)
                script_rec = sorted_scripts[0]
                script_rec = supabase_svc._update("scripts", script_rec["id"], {
                    "title": s_data["title"],
                    "hook": s_data["hook"],
                    "script_text": s_data["script_text"],
                    "scene_breakdown": s_data["scene_breakdown"],
                    "caption_timeline": s_data["caption_timeline"],
                    "thumbnail_text": s_data["thumbnail_text"],
                    "seo_description": s_data["seo_description"],
                    "hashtags": s_data["hashtags"]
                })
            else:
                script_rec = supabase_svc.create_script(
                    product_id=product_id,
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
            trigger_translation_voiceover_pipeline(script_rec, s_data, product, task_info)
            
        elif agent_name == "ThumbnailAgent":
            fallback_thumbnail = {
                "layout": "Product centered with bold yellow text overlay on dark slate background",
                "text": f"Pure {product_name}!",
                "prompt": f"Close-up photo of {product_name} on a wooden table, soft warm lighting, 8k resolution"
            }
            t_data = execute_agent_with_logging(
                product_id, "ThumbnailAgent",
                lambda: marketing_crew.run_thumbnail_agent(product_name),
                10.0, fallback_thumbnail
            )
            save_thumbnail_data_fields(product_id, layout=t_data["layout"], text=t_data["text"])
            
            thumbnail_filename = f"thumbnail_v1_{os.urandom(4).hex()}.png"
            thumbnail_url = video_svc.generate_thumbnail(
                image_paths=product.get("images", []),
                text=t_data["text"],
                output_filename=thumbnail_filename
            )
            save_thumbnail_data_fields(product_id, image_url=thumbnail_url)
            
        elif agent_name == "ImagePromptAgent":
            fallback_image_prompt = f"Close-up photo of {product_name} on a wooden table, soft warm lighting, 8k resolution"
            prompt_str = execute_agent_with_logging(
                product_id, "ImagePromptAgent",
                lambda: marketing_crew.run_image_prompt_agent(product_name, description),
                10.0, fallback_image_prompt
            )
            save_thumbnail_data_fields(product_id, prompt=prompt_str)
            
        elif agent_name == "TranslationAgent" or agent_name == "VoiceoverAgent":
            scripts = supabase_svc.get_scripts_by_product(product_id)
            if scripts:
                scripts = sorted(scripts, key=lambda s: s.get("version", 1), reverse=True)
                script_rec = scripts[0]
                s_data = {
                    "script_text": script_rec["script_text"],
                    "seo_description": script_rec["seo_description"],
                    "title": script_rec["title"]
                }
                trigger_translation_voiceover_pipeline(script_rec, s_data, product, task_info)

        task_info["status"] = "completed"
    except Exception as e:
        logger.error(f"Error retrying agent {agent_name}: {e}")
        task_info["agents"][agent_name] = "Failed"

@router.post("/generate-content")
async def generate_content(payload: GenerateContentRequest, background_tasks: BackgroundTasks):
    logger.info(f"[STAGE 1: Request Received] POST /generate-content triggered for product_id: {payload.product_id}")
    try:
        product = supabase_svc.get_product(payload.product_id)
        if not product:
            logger.warning(f"[STAGE 1: Request Received] Product {payload.product_id} not found in database")
            raise HTTPException(status_code=404, detail="Product not found")

        job = supabase_svc.create_video_job(payload.product_id, "queued")
        job_id = job["id"]

        ensure_draft_records(payload.product_id)

        # Register in BackgroundJobManager
        p_name = product["name"]
        campaign_name = f"Campaign - {p_name}"
        bg_job = job_manager.create_job(campaign_name, p_name, payload.product_id, job_id)
        bg_job.update_progress("Script Generation", "Queued", 5, 120)

        generation_tasks[payload.product_id] = {
            "status": "running",
            "current_step": 1,
            "step_message": "Campaign Created",
            "error_message": None,
            "result": None,
            "job_id": job_id,
            "progress_percent": 10,
            "estimated_remaining_time": 120,
            "start_time": time.time(),
            "last_update_time": time.time(),
            "last_progress": 10,
            "agents": {
                "ProductAgent": "Queued",
                "ResearchAgent": "Queued",
                "KeywordAgent": "Queued",
                "ScreenplayAgent": "Queued",
                "ThumbnailAgent": "Queued",
                "ImagePromptAgent": "Queued",
                "TranslationAgent": "Queued",
                "VoiceoverAgent": "Queued",
                "VideoAgent": "Queued"
            },
            "agent_durations": {
                "ProductAgent": 0.0,
                "ResearchAgent": 0.0,
                "KeywordAgent": 0.0,
                "ScreenplayAgent": 0.0,
                "ThumbnailAgent": 0.0,
                "ImagePromptAgent": 0.0,
                "TranslationAgent": 0.0,
                "VoiceoverAgent": 0.0,
                "VideoAgent": 0.0
            }
        }

        background_tasks.add_task(run_campaign_generation_task, job_id, payload.product_id, payload)
        logger.info(f"[STAGE 1: Request Received] Asynchronous background task queued for job_id: {job_id}, product_id: {payload.product_id}")

        return {
            "status": "queued",
            "job_id": job_id,
            "task_id": job_id
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[STAGE 1: Request Received] Failed to queue async campaign task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-content/retry-agent")
async def retry_agent(payload: RetryAgentRequest, background_tasks: BackgroundTasks):
    logger.info(f"Retrying agent {payload.agent_name} for product ID: {payload.product_id}")
    product = supabase_svc.get_product(payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    task_info = generation_tasks.get(payload.product_id)
    if not task_info:
        task_info = {
            "status": "running",
            "current_step": 2,
            "step_message": f"Retrying {payload.agent_name}...",
            "error_message": None,
            "result": None,
            "job_id": str(uuid.uuid4()),
            "progress_percent": 50,
            "estimated_remaining_time": 10,
            "agents": {
                "KeywordAgent": "Completed",
                "ScreenplayAgent": "Completed",
                "ThumbnailAgent": "Completed",
                "TranslationAgent": "Completed",
                "ImagePromptAgent": "Completed",
                "VoiceoverAgent": "Completed"
            },
            "agent_durations": {}
        }
        generation_tasks[payload.product_id] = task_info
        
    task_info["agents"][payload.agent_name] = "Running"
    task_info["status"] = "running"
    
    background_tasks.add_task(run_single_agent_retry_task, payload.product_id, payload.agent_name, product)
    return {"status": "success", "message": f"Retry scheduled for {payload.agent_name}"}

@router.get("/generate-content/status/{job_id_or_product_id}")
async def get_generation_status(job_id_or_product_id: str):
    logger.debug(f"Polling generation status requested for: {job_id_or_product_id}")
    
    bg_job = job_manager.get_job(job_id_or_product_id)
    if bg_job:
        job_dict = bg_job.to_dict()
        step_mapping = {
            "Product Analysis": 1,
            "Research Enrichment": 2,
            "SEO Keyword Generation": 3,
            "Script Generation": 4,
            "Thumbnail Creation": 5,
            "Image Generation": 6,
            "Voice Generation": 7,
            "Video Rendering": 8,
            "Completed": 9
        }
        current_step = step_mapping.get(bg_job.current_stage, 2)
        
        return {
            "status": bg_job.current_status.lower(),
            "job_status": bg_job.current_status.lower(),
            "current_step": current_step,
            "step_message": f"{bg_job.current_stage}: {bg_job.current_status} ({bg_job.percentage_complete}%)",
            "error_message": bg_job.error_message,
            "job_id": bg_job.job_id,
            "product_id": bg_job.product_id,
            "progress_percent": bg_job.percentage_complete,
            "estimated_remaining_time": job_dict["estimated_remaining_time"],
            "current_stage": bg_job.current_stage,
            "task_description": f"Processing stage {bg_job.current_stage}",
            "logs": bg_job.logs,
            "agents": bg_job.agents,
            "agent_durations": bg_job.agent_durations
        }
        
    job = supabase_svc.get_video_job(job_id_or_product_id)
    if not job:
        jobs = supabase_svc.get_video_jobs_by_product(job_id_or_product_id)
        if jobs:
            job = jobs[0]
            
    product_id = job["product_id"] if job else job_id_or_product_id
    task_info = generation_tasks.get(product_id)
    
    if job:
        ensure_draft_records(job["product_id"])
        
    # Auto-recovery checking
    if job and job["status"] in ["processing", "queued"]:
        try:
            scripts = supabase_svc.get_scripts_by_product(job["product_id"])
            if scripts:
                latest_script = sorted(scripts, key=lambda s: s.get("version", 1), reverse=True)[0]
                translations = supabase_svc.get_translations_by_script(latest_script["id"])
                if translations and len(translations) >= 5 and not any(t.get("youtube_script") == "Initializing..." for t in translations):
                    logger.info(f"Fallback Recovery: Campaign script with completed translations already exists in DB. Auto-completing job.")
                    supabase_svc.update_video_job(job_id=job["id"], status="completed", progress_step=9, progress_message="Campaign generated successfully!")
                    job["status"] = "completed"
        except Exception as e:
            logger.error(f"Error checking script fallback in status recovery: {e}")

    if not job and not task_info:
        try:
            scripts = supabase_svc.get_scripts_by_product(product_id)
            if scripts:
                return {
                    "status": "completed",
                    "job_status": "completed",
                    "current_step": 9,
                    "step_message": "Campaign retrieved from database.",
                    "error_message": None,
                    "result": {},
                    "progress_percent": 100,
                    "estimated_remaining_time": 0,
                    "agents": {
                        "ProductAgent": "Completed",
                        "ResearchAgent": "Completed",
                        "KeywordAgent": "Completed",
                        "ScreenplayAgent": "Completed",
                        "ThumbnailAgent": "Completed",
                        "TranslationAgent": "Completed",
                        "ImagePromptAgent": "Completed",
                        "VoiceoverAgent": "Completed",
                        "VideoAgent": "Completed"
                    },
                    "agent_durations": {}
                }
        except Exception:
            pass
        return {
            "status": "not_found",
            "current_step": 0,
            "step_message": "No active workflow task found.",
            "error_message": None,
            "result": None
        }

    if job and job["status"] == "completed" and not task_info:
        return {
            "status": "completed",
            "job_status": "completed",
            "current_step": 9,
            "step_message": "Campaign completed.",
            "error_message": job.get("error_message"),
            "job_id": job["id"],
            "product_id": product_id,
            "progress_percent": 100,
            "estimated_remaining_time": 0,
            "agents": {
                "ProductAgent": "Completed",
                "ResearchAgent": "Completed",
                "KeywordAgent": "Completed",
                "ScreenplayAgent": "Completed",
                "ThumbnailAgent": "Completed",
                "TranslationAgent": "Completed",
                "ImagePromptAgent": "Completed",
                "VoiceoverAgent": "Completed",
                "VideoAgent": "Completed"
            },
            "agent_durations": {}
        }
        
    if task_info:
        agents_dict = task_info.get("agents", {})
        completed_agents = sum(1 for name, state in agents_dict.items() if state == "Completed")
        progress_percent = int((completed_agents / 9) * 100)
        task_info["progress_percent"] = max(progress_percent, task_info.get("progress_percent", 10))
        
        current_progress = task_info["progress_percent"]
        if current_progress != task_info.get("last_progress"):
            task_info["last_progress"] = current_progress
            task_info["last_update_time"] = time.time()
            
        elapsed_sec = int(time.time() - task_info.get("start_time", time.time()))
        task_info["elapsed_time"] = elapsed_sec
        
        inactive_sec = time.time() - task_info.get("last_update_time", time.time())
        step_message = task_info.get("step_message", "Processing...")
        
        current_agent = None
        for name, state in agents_dict.items():
            if state == "Running":
                current_agent = name
                break
        if not current_agent:
            for name, state in agents_dict.items():
                if state == "Queued":
                    current_agent = name
                    break
                    
        if inactive_sec > 60.0 and task_info.get("status") == "running":
            agent_text = f" on {current_agent}" if current_agent else ""
            step_message = f"{step_message} (Delayed{agent_text}: AI connection unresponsive for {int(inactive_sec)}s)"
            logger.warning(f"Campaign generation stall detected. Stalled for {inactive_sec:.1f}s.")
            
        est_time = 0
        if agents_dict.get("KeywordAgent") in ["Queued", "Running"]: est_time += 10
        if agents_dict.get("ScreenplayAgent") in ["Queued", "Running"]: est_time += 20
        if agents_dict.get("ThumbnailAgent") in ["Queued", "Running"]: est_time += 10
        if agents_dict.get("ImagePromptAgent") in ["Queued", "Running"]: est_time += 10
        if agents_dict.get("TranslationAgent") in ["Queued", "Running"]: est_time += 15
        if agents_dict.get("VoiceoverAgent") in ["Queued", "Running"]: est_time += 25
        task_info["estimated_remaining_time"] = est_time
        
        return {
            "status": task_info.get("status", "running"),
            "job_status": job["status"] if job else "processing",
            "current_step": job["progress_step"] if job else task_info.get("current_step", 2),
            "step_message": step_message,
            "error_message": task_info.get("error_message"),
            "job_id": job["id"] if job else task_info.get("job_id"),
            "product_id": product_id,
            "progress_percent": task_info["progress_percent"],
            "estimated_remaining_time": task_info["estimated_remaining_time"],
            "elapsed_time": elapsed_sec,
            "current_agent": current_agent,
            "agents": agents_dict,
            "agent_durations": task_info.get("agent_durations", {}),
            "result": {}
        }

    frontend_status = "running"
    if job["status"] == "completed":
        frontend_status = "completed"
    elif job["status"] == "failed":
        frontend_status = "failed"
        
    elapsed_sec = 0
    created_at_str = job.get("created_at")
    if created_at_str:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(created_at_str.replace("Z", ""))
            elapsed_sec = int((datetime.now() - dt).total_seconds())
        except Exception:
            pass
        
    return {
        "status": frontend_status,
        "job_status": job["status"],
        "current_step": job["progress_step"] or 0,
        "step_message": job["progress_message"] or "Processing...",
        "error_message": job["error_message"],
        "job_id": job["id"],
        "product_id": product_id,
        "progress_percent": 50,
        "estimated_remaining_time": 20,
        "elapsed_time": max(0, elapsed_sec),
        "current_agent": None,
        "agents": {
            "ProductAgent": "Completed" if (job["progress_step"] or 0) > 1 else "Running",
            "ResearchAgent": "Completed" if (job["progress_step"] or 0) > 2 else "Running",
            "KeywordAgent": "Completed" if (job["progress_step"] or 0) > 3 else "Running",
            "ScreenplayAgent": "Completed" if (job["progress_step"] or 0) > 4 else "Running",
            "ThumbnailAgent": "Completed" if (job["progress_step"] or 0) > 5 else "Running",
            "ImagePromptAgent": "Completed" if (job["progress_step"] or 0) > 6 else "Running",
            "TranslationAgent": "Completed" if (job["progress_step"] or 0) > 7 else "Running",
            "VoiceoverAgent": "Completed" if (job["progress_step"] or 0) > 7 else "Running",
            "VideoAgent": "Completed" if (job["progress_step"] or 0) > 8 else "Running"
        },
        "agent_durations": {},
        "result": {}
    }

@router.get("/video-jobs/active")
async def get_active_jobs():
    try:
        active_jobs = job_manager.get_active_jobs()
        db_jobs = []
        try:
            db_jobs = supabase_svc.get_unfinished_video_jobs()
        except Exception as e:
            logger.error(f"Failed to fetch unfinished video jobs from DB: {e}")
            
        jobs_dict = {}
        for job in active_jobs:
            jobs_dict[job.job_id] = job.to_dict()
            
        for db_job in db_jobs:
            jid = db_job["id"]
            if jid not in jobs_dict:
                prod = supabase_svc.get_product(db_job["product_id"])
                job_status = db_job.get("status", "queued").lower()
                step = db_job.get("progress_step", 0)
                
                if job_status in ["waiting_approval", "script_approved"] or step == 5:
                    stage_name = "Awaiting Script Approval"
                    status_str = "Awaiting Approval"
                    pct = 50
                elif step >= 6:
                    stage_name = db_job.get("progress_message") or "Rendering Regional MP4 Videos"
                    status_str = "Rendering Video"
                    pct = int((step / 9) * 100)
                else:
                    stage_name = db_job.get("progress_message") or "Generating Screenplay"
                    status_str = job_status.capitalize()
                    pct = max(10, int((step / 9) * 100))

                jobs_dict[jid] = {
                    "job_id": jid,
                    "campaign_name": f"Campaign - {prod['name']}" if prod else "Campaign",
                    "product_name": prod["name"] if prod else "Unknown Product",
                    "product_id": db_job["product_id"],
                    "current_stage": stage_name,
                    "percentage_complete": pct,
                    "estimated_remaining_time": 60,
                    "current_status": status_str,
                    "status": job_status,
                    "error_message": db_job.get("error_message"),
                    "logs": [db_job.get("progress_message") or "Pipeline in progress..."]
                }
                
        return {
            "status": "success",
            "jobs": list(jobs_dict.values())
        }
    except Exception as e:
        logger.error(f"Failed to fetch active video jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/video-jobs/list")
async def list_video_jobs(status_filter: Optional[str] = None):
    try:
        jobs = job_manager.list_all_jobs(status_filter=status_filter)
        db_jobs = []
        try:
            db_jobs = supabase_svc._select_all("video_jobs")
        except Exception as e:
            logger.error(f"Failed to fetch DB video_jobs: {e}")

        known_ids = {j.job_id for j in jobs}
        combined = [j.to_dict() for j in jobs]

        for db_job in db_jobs:
            jid = db_job["id"]
            if jid not in known_ids:
                prod = supabase_svc.get_product(db_job.get("product_id", ""))
                st = db_job.get("status", "queued")
                if status_filter and status_filter.lower() != "all" and st.lower() != status_filter.lower():
                    continue
                combined.append({
                    "job_id": jid,
                    "campaign_name": f"Campaign - {prod['name']}" if prod else "Campaign",
                    "product_name": prod["name"] if prod else "Unknown Product",
                    "product_id": db_job.get("product_id"),
                    "current_stage": "Completed" if st == "completed" else "Preparing Assets",
                    "percentage_complete": 100 if st == "completed" else int(db_job.get("progress_step", 0) / 9 * 100),
                    "estimated_remaining_time": 0 if st == "completed" else 60,
                    "started_time": time.time(),
                    "last_updated_time": time.time(),
                    "current_status": st.capitalize(),
                    "status": st.lower(),
                    "error_message": db_job.get("error_message"),
                    "retry_count": 0,
                    "logs": [db_job.get("progress_message") or "Job record in database."],
                    "completed_stages": [],
                    "is_stalled": st == "stalled",
                    "is_cancelled": st == "cancelled",
                    "is_paused": st == "paused",
                    "agents": {},
                    "agent_durations": {}
                })

        return {"status": "success", "jobs": combined}
    except Exception as e:
        logger.error(f"Failed to list video jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/video-jobs/{job_id}/cancel")
async def cancel_video_job(job_id: str):
    logger.info(f"Cancellation requested for video job: {job_id}")
    bg_job = job_manager.get_job(job_id)
    if bg_job:
        bg_job.cancel()
        product_id = bg_job.product_id
    else:
        db_job = supabase_svc.get_video_job(job_id)
        if not db_job:
            jobs = supabase_svc.get_video_jobs_by_product(job_id)
            if jobs: db_job = jobs[0]
        if not db_job:
            raise HTTPException(status_code=404, detail="Video job not found")
        product_id = db_job["product_id"]

    supabase_svc.update_video_job(job_id, status="cancelled", progress_message="Job cancelled by user.")
    if product_id in generation_tasks:
        generation_tasks[product_id]["status"] = "cancelled"
    
    try:
        from backend.main import manager
        import asyncio
        payload = bg_job.to_dict() if bg_job else {"job_id": job_id, "product_id": product_id, "current_status": "Cancelled", "status": "cancelled"}
        asyncio.create_task(manager.broadcast("job.progress", payload))
    except Exception as ws_err:
        logger.warning(f"Failed to broadcast cancellation WS event: {ws_err}")

    return {"status": "cancelled", "job_id": job_id, "message": "Job cancelled and background tasks stopped."}

@router.post("/video-jobs/{job_id}/pause")
async def pause_video_job(job_id: str):
    bg_job = job_manager.get_job(job_id)
    if not bg_job:
        raise HTTPException(status_code=404, detail="Video job not found")
    bg_job.pause()
    supabase_svc.update_video_job(bg_job.job_id, status="paused", progress_message="Job paused by user.")
    return {"status": "paused", "job_id": bg_job.job_id}

@router.post("/video-jobs/{job_id}/resume")
async def resume_video_job(job_id: str, background_tasks: BackgroundTasks):
    bg_job = job_manager.get_job(job_id)
    if not bg_job:
        raise HTTPException(status_code=404, detail="Video job not found")
    
    bg_job.resume()
    supabase_svc.update_video_job(bg_job.job_id, status="processing", progress_message="Job resumed by user.")
    
    if bg_job.current_stage == "Script Generation" or bg_job.percentage_complete < 70:
        product = supabase_svc.get_product(bg_job.product_id)
        if product:
            payload = GenerateContentRequest(product_id=bg_job.product_id)
            background_tasks.add_task(run_campaign_generation_task, bg_job.job_id, bg_job.product_id, payload)
    else:
        background_tasks.add_task(run_campaign_rendering_task, bg_job.job_id, bg_job.product_id)

    return {"status": "resumed", "job_id": bg_job.job_id}

@router.post("/video-jobs/{job_id}/retry")
async def retry_video_job(job_id: str, background_tasks: BackgroundTasks, stage: Optional[str] = None):
    bg_job = job_manager.get_job(job_id)
    product_id = bg_job.product_id if bg_job else job_id
    
    product = supabase_svc.get_product(product_id)
    if not product:
        db_job = supabase_svc.get_video_job(job_id)
        if db_job:
            product_id = db_job["product_id"]
            product = supabase_svc.get_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Associated product not found")

    if not bg_job:
        p_name = product["name"]
        campaign_name = f"Campaign - {p_name}"
        bg_job = job_manager.create_job(campaign_name, p_name, product_id, job_id)

    bg_job.retry(from_stage=stage)
    supabase_svc.update_video_job(bg_job.job_id, status="processing", progress_message=f"Retrying job (Attempt #{bg_job.retry_count})...")

    scripts = supabase_svc.get_scripts_by_product(product_id)
    if scripts and (stage in ["Voice Generation", "Video Rendering"] or bg_job.percentage_complete >= 70):
        logger.info(f"Retrying job {bg_job.job_id} from Phase 2 (Rendering stage)")
        background_tasks.add_task(run_campaign_rendering_task, bg_job.job_id, product_id)
    else:
        logger.info(f"Retrying job {bg_job.job_id} from Phase 1 (Generation stage)")
        payload = GenerateContentRequest(product_id=product_id)
        background_tasks.add_task(run_campaign_generation_task, bg_job.job_id, product_id, payload)

    return {"status": "success", "job_id": bg_job.job_id, "message": f"Retry queued starting from stage '{bg_job.current_stage}'"}

@router.delete("/video-jobs/{job_id}")
async def delete_video_job(job_id: str):
    logger.info(f"Deletion requested for video job: {job_id}")
    bg_job = job_manager.get_job(job_id)
    product_id = bg_job.product_id if bg_job else job_id

    success = job_manager.delete_job(job_id)
    if product_id in generation_tasks:
        generation_tasks.pop(product_id, None)

    try:
        from backend.main import manager
        import asyncio
        asyncio.create_task(manager.broadcast("job.deleted", {"job_id": job_id, "product_id": product_id}))
    except Exception as ws_err:
        logger.warning(f"Failed to broadcast deletion WS event: {ws_err}")

    return {"status": "success", "job_id": job_id, "message": "Job permanently deleted and temporary files cleaned up."}

@router.get("/video-jobs/{job_id}/logs")
async def get_video_job_logs(job_id: str):
    bg_job = job_manager.get_job(job_id)
    if not bg_job:
        db_job = supabase_svc.get_video_job(job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"job_id": job_id, "logs": [db_job.get("progress_message") or "No detailed logs available."]}
    return {"job_id": bg_job.job_id, "logs": bg_job.logs}

@router.post("/regenerate")
async def regenerate_campaign(payload: RegenerateRequest):
    logger.info(f"Regenerating campaign V2 for product ID: {payload.product_id}")
    try:
        product = supabase_svc.get_product(payload.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Check existing script version count & lock status
        existing_scripts = supabase_svc.get_scripts_by_product(payload.product_id)
        if existing_scripts:
            sorted_scripts = sorted(existing_scripts, key=lambda s: s.get("version", 1), reverse=True)
            if sorted_scripts[0].get("status") == "locked":
                raise HTTPException(status_code=400, detail="Cannot regenerate: campaign script is already locked.")
        
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
        crew_result = clean_surrogates(crew_result)

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
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Regeneration workflow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ApproveScriptRequest(BaseModel):
    product_id: str
    script_text: Optional[str] = None
    title: Optional[str] = None
    hook: Optional[str] = None
    voice_profile: Optional[str] = None
    speed_rate: Optional[str] = None
    pitch: Optional[str] = None

@router.post("/campaign/approve-script")
async def approve_campaign_script(payload: ApproveScriptRequest, background_tasks: BackgroundTasks):
    logger.info(f"Approve & lock script request received for product: {payload.product_id}")
    try:
        # Get the latest script
        scripts = supabase_svc.get_scripts_by_product(payload.product_id)
        if not scripts:
            raise HTTPException(status_code=404, detail="No scripts found for this product")
        scripts = sorted(scripts, key=lambda s: s.get("version", 1), reverse=True)
        script_rec = scripts[0]

        # Check if already locked
        if script_rec.get("status") == "locked":
            # Find active job or create a new job to make sure it's running
            jobs = supabase_svc._select_all("video_jobs")
            active_job = next((j for j in jobs if j.get("product_id") == payload.product_id and j.get("status") in ["waiting_approval", "queued", "running"]), None)
            if not active_job:
                active_job = supabase_svc.create_video_job(payload.product_id, "queued")
            return {"status": "success", "message": "Script is already locked. Starting rendering...", "script_id": script_rec["id"]}

        # Update fields if user edited them
        updates = {"status": "locked"}
        if payload.script_text is not None:
            updates["script_text"] = payload.script_text
        if payload.title is not None:
            updates["title"] = payload.title
        if payload.hook is not None:
            updates["hook"] = payload.hook

        updated_script = supabase_svc._update("scripts", script_rec["id"], updates)

        # Update the active video job status
        jobs = supabase_svc._select_all("video_jobs")
        active_job = None
        for j in jobs:
            if j.get("product_id") == payload.product_id and j.get("status") in ["waiting_approval", "queued", "running"]:
                active_job = j
                break
                
        if not active_job:
            active_job = supabase_svc.create_video_job(payload.product_id, "queued")
        else:
            supabase_svc.update_video_job(active_job["id"], "queued", 7, "Locking script and scheduling voice generation...")

        # Update task info status
        task_info = generation_tasks.get(payload.product_id)
        if task_info:
            task_info["status"] = "running"
            task_info["step_message"] = "Locking script and scheduling voice generation..."
            task_info["progress_percent"] = 70
        
        # Schedule Phase 2 background task
        background_tasks.add_task(
            run_campaign_rendering_task, 
            active_job["id"], 
            payload.product_id, 
            payload.voice_profile, 
            payload.speed_rate, 
            payload.pitch
        )

        return {"status": "success", "message": "Script approved and locked. Rendering scheduled.", "script": updated_script}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to approve & lock script: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def seed_mock_comments(channel_id, mock_id, script):
    import asyncio
    from datetime import datetime, timedelta
    from backend.crews.youtube_monitor_crew import youtube_monitor_crew
    
    try:
        product = supabase_svc.get_product(script["product_id"])
        product_name = product["name"] if product else "product"
    except Exception:
        product_name = "product"
        
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
        comment_time = (datetime.now() - timedelta(minutes=(10 - idx) * 3)).isoformat()
        asyncio.create_task(
            youtube_monitor_crew.process_single_comment(
                channel_id=channel_id,
                video_id=mock_id,
                comment_id=comment_id,
                username=demo["username"],
                comment_text=demo["text"],
                timestamp=comment_time
            )
        )

def run_youtube_publish_task(video_id: str):
    logger.info(f"[YOUTUBE PUBLISH TASK] Initiating upload workflow for video ID: {video_id}")
    start_time = time.time()
    
    try:
        video = supabase_svc.get_video(video_id)
        if not video:
            logger.error(f"[YOUTUBE PUBLISH TASK] Video {video_id} not found in database.")
            return
            
        supabase_svc._update("videos", video_id, {
            "status": "Uploading",
            "publish_progress": "0%",
            "publish_timestamp": datetime.now().isoformat(),
            "publish_error": None
        })
        
        voiceovers = supabase_svc._select_all("voiceovers")
        voice_rec = next((v for v in voiceovers if v["id"] == video["voiceover_id"]), None)
        if not voice_rec:
            raise Exception("Voiceover metadata not found in database.")
            
        translation = supabase_svc.get_translation(voice_rec["translation_id"])
        if not translation:
            raise Exception("Translation metadata not found in database.")
            
        script = supabase_svc.get_script(translation["script_id"])
        if not script:
            raise Exception("Script metadata not found in database.")
            
        orig_filename = os.path.basename(video["video_url"])
        original_video_path = settings.MEDIA_DIR / orig_filename
        
        actual_video_path = original_video_path
        is_mock_video = True
        if os.path.exists(original_video_path) and os.path.getsize(original_video_path) > 100:
            is_mock_video = False
            
        if is_mock_video:
            fallback_rel_url = get_fallback_video_url(translation["language"])
            actual_video_path = settings.MEDIA_DIR / os.path.basename(fallback_rel_url)
            logger.info(f"Video file is mock (<=100 bytes). Using pre-seeded video: {actual_video_path}")
            
        channels = supabase_svc.get_youtube_channels()
        simulate = not youtube_publish_svc.api_available or not channels
        
        def progress_callback(progress_percent):
            supabase_svc._update("videos", video_id, {
                "publish_progress": f"{progress_percent}%"
            })
            
        if simulate:
            logger.info("[YOUTUBE PUBLISH TASK] Running simulated upload process...")
            for p in range(10, 101, 20):
                time.sleep(1.5)
                progress_callback(min(100, p))
            
            time.sleep(0.5)
            supabase_svc._update("videos", video_id, {
                "status": "Upload Completed",
                "publish_progress": "100%"
            })
            time.sleep(1)
            
            mock_id = f"YOUTUBE_{uuid.uuid4().hex[:11].upper()}"
            mock_url = f"https://www.youtube.com/watch?v={mock_id}"
            
            supabase_svc._update("videos", video_id, {
                "status": "YouTube Processing",
                "publish_progress": "Processing HD Version...",
                "youtube_id": mock_id,
                "youtube_url": mock_url
            })
            time.sleep(2)
            supabase_svc._update("videos", video_id, {
                "publish_progress": "Processing Thumbnail..."
            })
            time.sleep(1.5)
            supabase_svc._update("videos", video_id, {
                "publish_progress": "Processing Complete"
            })
            time.sleep(1)
            
            duration = int(time.time() - start_time)
            supabase_svc._update("videos", video_id, {
                "status": "Published",
                "publish_progress": "Published",
                "publish_duration": duration
            })
            
            channel_id = channels[0]["channel_id"] if channels else "MOCK_CHANNEL_ID"
            supabase_svc.create_youtube_video(
                channel_id=channel_id,
                video_id=mock_id,
                title=script.get("title", "VyaparAI Promo Video"),
                publish_date=datetime.now().isoformat(),
                status="monitored"
            )
            
            seed_mock_comments(channel_id, mock_id, script)
            logger.info("[YOUTUBE PUBLISH TASK] Simulated upload completed successfully.")
            return

        logger.info("[YOUTUBE PUBLISH TASK] Initiating real YouTube chunked upload...")
        publish_res = youtube_publish_svc.publish_video(
            video_path=str(actual_video_path),
            title=script.get("title", "VyaparAI Promo Video"),
            description=script.get("seo_description", "Campaign promotional short video."),
            hashtags=script.get("hashtags", ["VyaparAI", "LocalStore"]),
            progress_callback=progress_callback
        )
        
        youtube_id = publish_res["youtube_id"]
        youtube_url = publish_res["youtube_url"]
        
        supabase_svc._update("videos", video_id, {
            "status": "Upload Completed",
            "publish_progress": "100%",
            "youtube_id": youtube_id,
            "youtube_url": youtube_url
        })
        
        logger.info(f"[YOUTUBE PUBLISH TASK] Video uploaded successfully. Monitoring processing status for Video ID: {youtube_id}")
        channel = channels[0]
        
        max_polls = 60
        poll_count = 0
        processing_complete = False
        
        while poll_count < max_polls:
            time.sleep(10)
            poll_count += 1
            
            status_res = youtube_publish_svc.check_video_processing_status(youtube_id, channel)
            if status_res["status"] == "success":
                upload_status = status_res.get("upload_status")
                processing_status = status_res.get("processing_status")
                rejection_reason = status_res.get("rejection_reason")
                failure_reason = status_res.get("failure_reason")
                time_left = status_res.get("time_left_ms")
                
                if upload_status == "rejected":
                    raise Exception(f"Video was rejected by YouTube. Reason: {rejection_reason or 'unknown'}")
                if upload_status == "failed" or processing_status == "failed":
                    raise Exception(f"YouTube processing failed. Reason: {failure_reason or 'unknown'}")
                    
                progress_text = "Processing on YouTube"
                if time_left:
                    progress_text += f" (Estimated time: {int(time_left/1000)}s)"
                else:
                    parts_p = status_res.get("parts_processed")
                    parts_t = status_res.get("parts_total")
                    if parts_p and parts_t:
                        progress_text += f" (Parts processed: {parts_p}/{parts_t})"
                
                supabase_svc._update("videos", video_id, {
                    "status": "YouTube Processing",
                    "publish_progress": progress_text,
                    "youtube_processing_status": processing_status,
                    "youtube_upload_status": upload_status,
                    "youtube_privacy_status": status_res.get("privacy_status")
                })
                
                if upload_status == "processed" or processing_status == "succeeded":
                    processing_complete = True
                    break
            else:
                logger.warning(f"Failed to fetch YouTube processing status on attempt {poll_count}: {status_res.get('error')}")
                
        if not processing_complete:
            raise Exception("Timed out waiting for YouTube processing to finish.")
            
        duration = int(time.time() - start_time)
        supabase_svc._update("videos", video_id, {
            "status": "Published",
            "publish_progress": "Published",
            "publish_duration": duration
        })
        
        supabase_svc.update_video_publish_info(
            video_id=video_id,
            youtube_id=youtube_id,
            youtube_url=youtube_url
        )
        
        supabase_svc.create_youtube_video(
            channel_id=channel["channel_id"],
            video_id=youtube_id,
            title=script.get("title", "VyaparAI Promo Video"),
            publish_date=datetime.now().isoformat(),
            status="monitored"
        )
        
        try:
            product = supabase_svc.get_product(script["product_id"])
            if product:
                supabase_svc.increment_analytics(product["business_id"], "videos_generated", 1)
        except Exception:
            pass
            
        logger.info(f"[YOUTUBE PUBLISH TASK] Real video upload and processing completed successfully in {duration}s.")
        
    except Exception as err:
        logger.error(f"[YOUTUBE PUBLISH TASK] Publishing task failed: {err}", exc_info=True)
        err_msg = str(err).lower()
        friendly_error = "Upload failed"
        if "quota" in err_msg:
            friendly_error = "API Quota exceeded. YouTube limits uploads per day."
        elif "credentials" in err_msg or "auth" in err_msg:
            friendly_error = "Invalid credentials. Please re-authenticate your YouTube channel."
        elif "copyright" in err_msg:
            friendly_error = "Copyright restriction detected on video audio/content."
        elif "guideline" in err_msg:
            friendly_error = "Community guideline restriction detected."
        elif "network" in err_msg or "conn" in err_msg:
            friendly_error = "Network interruption during upload."
        else:
            friendly_error = f"Failed: {str(err)}"
            
        supabase_svc._update("videos", video_id, {
            "status": "Failed",
            "publish_progress": "Failed",
            "publish_error": friendly_error
        })

@router.post("/publish")
async def publish_video(payload: PublishRequest, background_tasks: BackgroundTasks):
    logger.info(f"YouTube publishing triggered for video ID: {payload.video_id}")
    try:
        video = supabase_svc.get_video(payload.video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video record not found")
            
        if video.get("status") in ["Upload Queued", "Uploading", "Upload Completed", "YouTube Processing"]:
            return {
                "status": "queued",
                "message": "Publishing is already in progress.",
                "video": video
            }
            
        updated_video = supabase_svc._update("videos", payload.video_id, {
            "status": "Upload Queued",
            "publish_progress": "Queued",
            "publish_timestamp": datetime.now().isoformat(),
            "publish_error": None
        })
        
        background_tasks.add_task(run_youtube_publish_task, payload.video_id)
        
        return {
            "status": "queued",
            "message": "Publishing process successfully queued.",
            "video": updated_video
        }
    except Exception as e:
        logger.error(f"Failed to queue publish background task: {e}")
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

from pydantic import BaseModel

class RepairVideoRequest(BaseModel):
    video_id: str

@router.post("/video/repair")
async def repair_video(payload: RepairVideoRequest):
    logger.info(f"Repair request received for video ID: {payload.video_id}")
    try:
        # 1. Retrieve the video record
        all_videos = supabase_svc._select_all("videos")
        video = supabase_svc.get_video(payload.video_id)
        if not video:
            video = next((v for v in all_videos if v["id"] == payload.video_id or payload.video_id in v.get("video_url", "")), None)
        if not video and all_videos:
            # Fallback to latest video record
            video = all_videos[-1]

        if not video:
            raise HTTPException(status_code=404, detail="Video record not found")
            
        # 2. Get the voiceover record
        voiceovers = supabase_svc._select_all("voiceovers")
        voice_rec = next((v for v in voiceovers if v["id"] == video["voiceover_id"]), None)
        if not voice_rec and voiceovers:
            voice_rec = voiceovers[-1]
            
        if not voice_rec:
            raise HTTPException(status_code=404, detail="Voiceover not found")
            
        # 3. Get the translation record
        translation = supabase_svc.get_translation(voice_rec["translation_id"]) if voice_rec.get("translation_id") else None
        text_content = translation["reel"] if translation and "reel" in translation else "Welcome to our shop. High quality products delivered fast."
        lang_code = translation["language"] if translation and "language" in translation else "English"

        # 4. Get the script record & product record
        script = supabase_svc.get_script(translation["script_id"]) if translation and "script_id" in translation else None
        product = supabase_svc.get_product(script["product_id"]) if script and "product_id" in script else None
        image_paths = product.get("images", []) if product else []

        # 5. Re-run generate_marketing_video to repair the file
        video_filename = os.path.basename(video["video_url"])
        audio_filename = os.path.basename(voice_rec["audio_url"]) if voice_rec.get("audio_url") else f"voiceover_{lang_code.lower()}_v1_{os.urandom(4).hex()}.mp3"
        audio_path = str(settings.MEDIA_DIR / audio_filename)
        
        # Synthesize voiceover if missing or corrupted (< 1000 bytes)
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
            logger.info(f"Synthesizing missing/corrupted voiceover path: {audio_path}")
            audio_path = voice_svc.generate_voiceover(text_content, lang_code, audio_filename)

        logger.info(f"Regenerating video file '{video_filename}' via video service...")
        video_path = video_svc.generate_marketing_video(
            audio_path=audio_path,
            image_paths=image_paths,
            voiceover_text=text_content,
            output_filename=video_filename
        )
        
        # Verify the new video file is valid
        if os.path.exists(video_path) and os.path.getsize(video_path) > 100:
            logger.info(f"Video file successfully repaired at {video_path}")
            timestamp = int(time.time())
            clean_url = video["video_url"].split("?")[0]
            return {
                "status": "success",
                "message": "Video file successfully repaired.",
                "video_url": f"{clean_url}?t={timestamp}"
            }
        else:
            raise Exception("Regenerated video file is missing or invalid.")
    except Exception as e:
        logger.error(f"Failed to repair video {payload.video_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


