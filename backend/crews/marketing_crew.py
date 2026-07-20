# backend/crews/marketing_crew.py
import os
import json
import logging
import random
from typing import Dict, Any, List, Callable
from crewai import Crew, Task, Process

from backend.agents.keyword_agent import make_keyword_agent
from backend.agents.trend_agent import make_trend_agent, get_trending_keywords
from backend.agents.script_agent import make_script_agent
from backend.agents.thumbnail_agent import make_thumbnail_agent
from backend.agents.quality_agent import make_quality_agent, audit_campaign_quality
from backend.agents.publishing_agent import make_publishing_agent
from backend.agents.image_prompt_agent import make_image_prompt_agent
from backend.agents.product_agent import make_product_agent
from backend.agents.research_agent import make_research_agent

from backend.services.voice_service import voice_svc
from backend.services.video_service import video_svc
from backend.services.youtube_publishing_service import youtube_publish_svc
from backend.services.supabase_service import supabase_svc
from backend.config import settings

logger = logging.getLogger("vyaparai.crews.marketing_crew")

from backend.services.script_generator import script_generator_svc

def get_randomized_script_data(product_name: str, description: str) -> dict:
    style, platform = script_generator_svc.select_script_parameters()
    rag_context = ""
    try:
        from backend.services.rag_service import rag_svc
        rag_context = rag_svc.retrieve(f"{product_name} {description}")
    except Exception as e:
        logger.warning(f"RAG retrieval failed in legacy redirect: {e}")
    return script_generator_svc.procedural_generate(product_name, description, style, platform, rag_context)

class MarketingCrew:
    def __init__(self):
        self.reset_agents()

    def reset_agents(self):
        logger.info("Wiping agent instances and clearing CrewAI cache to prevent context contamination.")
        self._keyword_agent = None
        self._trend_agent = None
        self._script_agent = None
        self._thumbnail_agent = None
        self._quality_agent = None
        self._publishing_agent = None
        self._image_prompt_agent = None
        self._product_agent = None
        self._research_agent = None

    @property
    def product_agent(self):
        if self._product_agent is None:
            self._product_agent = make_product_agent()
        return self._product_agent

    @property
    def research_agent(self):
        if self._research_agent is None:
            self._research_agent = make_research_agent()
        return self._research_agent

    @property
    def image_prompt_agent(self):
        if self._image_prompt_agent is None:
            self._image_prompt_agent = make_image_prompt_agent()
        return self._image_prompt_agent

    @property
    def keyword_agent(self):
        if self._keyword_agent is None:
            self._keyword_agent = make_keyword_agent()
        return self._keyword_agent

    @property
    def trend_agent(self):
        if self._trend_agent is None:
            self._trend_agent = make_trend_agent()
        return self._trend_agent

    @property
    def script_agent(self):
        if self._script_agent is None:
            self._script_agent = make_script_agent()
        return self._script_agent

    @property
    def thumbnail_agent(self):
        if self._thumbnail_agent is None:
            self._thumbnail_agent = make_thumbnail_agent()
        return self._thumbnail_agent

    @property
    def quality_agent(self):
        if self._quality_agent is None:
            self._quality_agent = make_quality_agent()
        return self._quality_agent

    @property
    def publishing_agent(self):
        if self._publishing_agent is None:
            self._publishing_agent = make_publishing_agent()
        return self._publishing_agent

    def extract_json(self, task_output):
        if not task_output:
            logger.warning("extract_json received None task_output")
            return None
        
        # Check for json_dict first
        json_dict = getattr(task_output, "json_dict", None)
        if json_dict and isinstance(json_dict, dict):
            logger.info("Found parsed json_dict in task_output")
            return json_dict
        
        # Retrieve raw text
        raw_text = getattr(task_output, "raw", None)
        if not raw_text:
            raw_text = getattr(task_output, "raw_output", None)
        
        if not raw_text:
            if isinstance(task_output, str):
                raw_text = task_output
            else:
                logger.warning(f"task_output has no raw or raw_output. Type: {type(task_output)}")
                return None
        
        logger.info(f"Extracted raw text (first 200 chars): {raw_text[:200]}")
        
        import re
        cleaned = raw_text.strip()
        # Clean markdown code block wraps
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()
        
        try:
            parsed = json.loads(cleaned)
            logger.info("Successfully parsed cleaned raw JSON directly")
            return parsed
        except Exception as e:
            logger.info(f"Direct JSON load failed: {e}. Trying regex extraction...")
        
        # Try finding a JSON object using regex
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                logger.info("Successfully parsed regex-matched JSON")
                return parsed
            except Exception as e:
                logger.warning(f"Regex JSON loads failed: {e}")
        
        return None

    def run_product_agent(self, product_name: str, description: str) -> dict:
        self.reset_agents()
        
        # Pre-fill standard characteristics if in botanical DB to seed the LLM
        from backend.services.script_generator import BOTANICAL_DB
        n_clean = product_name.lower().strip()
        matched_facts = None
        for key, val in BOTANICAL_DB.items():
            if key in n_clean or n_clean in key:
                matched_facts = val
                break

        seed_info = ""
        if matched_facts:
            seed_info = f"""
BOTANICAL DATABASE SEED TRACE:
- Scientific Name: {matched_facts.get('scientific_name', '')}
- Category: {matched_facts.get('category', '')}
- Care: {matched_facts.get('care_instructions', '')}
- Benefits: {', '.join(matched_facts.get('benefits', []))}
- Common Mistakes: {matched_facts.get('common_mistakes', '')}
"""

        task = Task(
            description=f"""Analyze the product name: '{product_name}' and description: '{description}'.
Match against known plant characteristics and extract a structured Product Context JSON matching the target schema.
The JSON must have the following keys:
product_name, category, botanical_name, indoor_outdoor, flowering, foliage, fragrance, medicinal, air_purifying, flowering_season, sunlight, watering, soil, fertilizer, propagation, care_level, unique_features, customer_benefits, emotional_benefits, common_mistakes, FAQs, target_audience.

{seed_info}

Ensure the output is a strict, valid JSON object with boolean fields for flowering, foliage, fragrance, medicinal, air_purifying.""",
            expected_output="JSON structure matching the Product Context schema.",
            agent=self.product_agent
        )
        crew = Crew(agents=[self.product_agent], tasks=[task], verbose=False, memory=False)
        res = crew.kickoff()
        parsed = self.extract_json(res)
        if not parsed:
            raise Exception("Failed to parse product context JSON output")
        return parsed

    def run_research_agent(self, product_context: dict, rag_context: str) -> dict:
        self.reset_agents()
        task = Task(
            description=f"""Enrich the following Product Context JSON with verified horticultural details from the provided RAG knowledge base context.
Product Context:
{json.dumps(product_context)}

RAG Knowledge Base Details:
{rag_context}

Update and fill in any missing or partial fields in the Product Context. Ensure 100% botanical accuracy.
Return the updated Product Context as a strict, valid JSON object with the exact same keys.""",
            expected_output="Updated JSON structure matching the Product Context schema.",
            agent=self.research_agent
        )
        crew = Crew(agents=[self.research_agent], tasks=[task], verbose=False, memory=False)
        res = crew.kickoff()
        parsed = self.extract_json(res)
        if not parsed:
            raise Exception("Failed to parse enriched product context JSON output")
        return parsed

    def run_keyword_agent(self, product_context_or_name: Any, description: str = None) -> dict:
        self.reset_agents()
        if isinstance(product_context_or_name, dict):
            product_context = product_context_or_name
            product_name = product_context.get("product_name", "Plant")
            desc_str = json.dumps(product_context)
        else:
            product_name = product_context_or_name
            desc_str = description or ""
            
        task = Task(
            description=f"""Analyze the product context:
'{desc_str}'
Determine the target market. Categorize and generate:
- Primary Keywords (core product terms)
- Secondary Keywords (associated snack/craft tags)
- Long Tail Keywords (longer search phrases)
- Purchase Intent Keywords (e.g. 'buy', 'order')
- Regional Keywords (relating to local Indian regions/states)""",
            expected_output="JSON structure mapping: primary, secondary, long_tail, intent, regional",
            agent=self.keyword_agent
        )
        crew = Crew(agents=[self.keyword_agent], tasks=[task], verbose=False, memory=False)
        res = crew.kickoff()
        parsed = self.extract_json(res)
        if not parsed:
            raise Exception("Failed to parse keyword JSON output")
        return parsed

    def get_cached_keywords_for_product(self, product_context_or_name: Any) -> dict:
        name = ""
        if isinstance(product_context_or_name, dict):
            name = product_context_or_name.get("product_name", "")
        else:
            name = str(product_context_or_name)
        
        name_lower = name.lower()
        from backend.services.script_generator import BOTANICAL_DB
        for key, val in BOTANICAL_DB.items():
            if key in name_lower or name_lower in key:
                kws = val.get("keywords", [])
                return {
                    "primary": kws[:2] if len(kws) >= 2 else [name, f"buy {name}"],
                    "secondary": kws[2:4] if len(kws) >= 4 else ["nursery", "plants"],
                    "long_tail": [f"best {name} online", f"how to care for {name}"],
                    "intent": [f"buy {name} online", f"order {name}"],
                    "regional": [f"{name} in india", f"{name} delivery"]
                }
        
        return {
            "primary": [name, f"buy {name}"],
            "secondary": ["home decor", "gardening"],
            "long_tail": [f"best {name} online", f"organic {name} care"],
            "intent": [f"order {name}", f"buy {name} price"],
            "regional": [f"{name} nursery india", f"deliver {name}"]
        }

    def run_keyword_agent_with_recovery(self, product_context_or_name: Any, description: str = None) -> dict:
        import time
        for attempt in range(1, 4):
            try:
                logger.info(f"Running KeywordAgent (attempt {attempt})...")
                return self.run_keyword_agent(product_context_or_name, description)
            except Exception as e:
                logger.warning(f"KeywordAgent attempt {attempt} failed: {e}")
                if attempt == 3:
                    logger.warning("KeywordAgent recovery triggered. Loading cached keywords...")
                    return self.get_cached_keywords_for_product(product_context_or_name)
                time.sleep(1)

    def run_script_agent_with_validation(self, product_context: dict, product_images: list = None, force_feedback: str = None) -> dict:
        return script_generator_svc.generate(
            product_name=product_context.get("product_name", "Plant"),
            description=product_context.get("description", ""),
            product_images=product_images,
            force_feedback=force_feedback,
            product_context=product_context
        )

    def run_script_agent(self, product_name: str, description: str, product_images: list = None, force_feedback: str = None) -> dict:
        product_context = self.run_product_agent(product_name, description)
        return self.run_script_agent_with_validation(product_context, product_images, force_feedback)

    def run_trend_agent(self, product_name: str, location: str) -> dict:
        task = Task(
            description=f"Analyze search demand signals in location '{location}' for product '{product_name}'. List 10 viral video topics and 3 optimized SEO titles.",
            expected_output="JSON structure mapping: trending_topics, seo_titles",
            agent=self.trend_agent
        )
        crew = Crew(agents=[self.trend_agent], tasks=[task], verbose=False)
        res = crew.kickoff()
        parsed = self.extract_json(res)
        if not parsed:
            raise Exception("Failed to parse trend JSON output")
        return parsed

    def run_thumbnail_agent(self, product_name: str) -> dict:
        task = Task(
            description=f"Design a high-CTR thumbnail for '{product_name}'. Suggest a layout configuration, overlay text, and a prompt for image generation models.",
            expected_output="JSON structure mapping: layout, text, prompt",
            agent=self.thumbnail_agent
        )
        crew = Crew(agents=[self.thumbnail_agent], tasks=[task], verbose=False)
        res = crew.kickoff()
        parsed = self.extract_json(res)
        if not parsed:
            raise Exception("Failed to parse thumbnail JSON output")
        return parsed

    def run_image_prompt_agent(self, product_name: str, description: str) -> str:
        task = Task(
            description=f"Create a photorealistic image prompt for a product advertisement thumbnail for '{product_name}'. Description: '{description}'. State camera angle, style, lighting, and elements.",
            expected_output="A descriptive text prompt for an image generator.",
            agent=self.image_prompt_agent
        )
        crew = Crew(agents=[self.image_prompt_agent], tasks=[task], verbose=False)
        res = crew.kickoff()
        raw_text = getattr(res, "raw", None)
        if not raw_text:
            raw_text = getattr(res, "raw_output", None)
        if not raw_text and isinstance(res, str):
            raw_text = res
        if not raw_text:
            raise Exception("Failed to generate image prompt")
        return raw_text.strip()

    def run(
        self, 
        product_name: str, 
        description: str, 
        location: str, 
        product_images: List[str] = None,
        force_feedback: str = None,
        version: int = 1,
        status_callback: Callable[[int, str], None] = None
    ) -> Dict[str, Any]:
        """
        Executes the fully synchronized, sequential multi-agent pipeline.
        Clears memory between executions to avoid cross-product leakage.
        """
        import time
        start_time = time.time()
        logger.info(f"Initiating Sequentially Synchronized Marketing Crew for product: {product_name} (Version: {version})")
        
        # Reset lazy-loaded agents and empty cache
        self.reset_agents()

        # Step 1: Product Agent Profile Extraction
        if status_callback:
            status_callback(1, "Running ProductAgent: Extracting structured context...")
        product_context = self.run_product_agent(product_name, description)
        logger.info(f"[STAGE 1] Extracted Product Context: {json.dumps(product_context)}")

        # Step 2: Research Agent Enrichment
        if status_callback:
            status_callback(2, "Running ResearchAgent: Fetching botanical facts & RAG context...")
        rag_context = ""
        try:
            from backend.services.rag_service import rag_svc
            rag_context = rag_svc.retrieve(f"{product_name} {description}")
            logger.info(f"[STAGE 2] Retrieved RAG context (first 100 chars): {rag_context[:100]}")
        except Exception as e:
            logger.warning(f"[STAGE 2] RAG retrieval failed: {e}")
            
        product_context = self.run_research_agent(product_context, rag_context)
        logger.info(f"[STAGE 2] Enriched Product Context: {json.dumps(product_context)}")

        # Step 3: Keyword Agent Generation with Recovery
        if status_callback:
            status_callback(3, "Running KeywordAgent: Generating SEO keywords...")
        keyword_data = self.run_keyword_agent_with_recovery(product_context)
        primary_kws = keyword_data.get("primary", [product_name])
        secondary_kws = keyword_data.get("secondary", ["plants"])
        long_tail_kws = keyword_data.get("long_tail", [f"best {product_name} online"])
        intent_kws = keyword_data.get("intent", [f"buy {product_name}"])
        regional_kws = keyword_data.get("regional", [f"{product_name} delivery"])

        # Step 4: Trend Analysis
        if status_callback:
            status_callback(4, "Running TrendAgent: Analyzing location search signals...")
        try:
            trend_data = self.run_trend_agent(product_name, location)
            topics = trend_data.get("trending_topics", [f"Top 5 benefits of {product_name}"])
        except Exception as e:
            logger.warning(f"TrendAgent failed: {e}. Using fallback topics.")
            topics = [
                f"Why this {product_name} is going viral",
                f"How traditional {product_name} is grown",
                f"Top 5 benefits of {product_name}"
            ]

        # Step 5: Script Generation with Validation
        if status_callback:
            status_callback(5, "Running ScriptAgent: Writing and validating screenplay...")
        script_data = self.run_script_agent_with_validation(product_context, product_images, force_feedback)

        # Step 6: Thumbnail Design
        if status_callback:
            status_callback(6, "Running ThumbnailAgent: Creating overlay blueprint...")
        try:
            thumbnail_data = self.run_thumbnail_agent(product_name)
            if "layout" not in thumbnail_data:
                thumbnail_data["layout"] = "Product centered with bold yellow text overlay on dark slate background"
            if "text" not in thumbnail_data:
                thumbnail_data["text"] = script_data.get("thumbnail_text", f"Pure {product_name}!")
            if "prompt" not in thumbnail_data:
                thumbnail_data["prompt"] = f"Close-up photo of {product_name} on a wooden table, soft warm lighting, 8k resolution"
        except Exception as e:
            logger.warning(f"ThumbnailAgent failed: {e}. Using fallback layout.")
            thumbnail_data = {
                "layout": "Product centered with bold yellow text overlay on dark slate background",
                "text": script_data.get("thumbnail_text", f"Pure {product_name}!"),
                "prompt": f"Close-up photo of {product_name} on a wooden table, soft warm lighting, 8k resolution"
            }

        # Quality Check Loop
        if status_callback:
            status_callback(7, "Auditing script copy with QualityAgent...")
        qa_result = audit_campaign_quality(script_data, primary_kws + long_tail_kws, product_name=product_name)
        
        # Simulate regeneration once if QA score fails
        if qa_result["status"] == "REGENERATE" and version < 2:
            logger.warning("Quality score < 80. Triggering automatic regeneration loop...")
            return self.run(
                product_name=product_name,
                description=description,
                location=location,
                product_images=product_images,
                force_feedback=qa_result["feedback"],
                version=version + 1,
                status_callback=status_callback
            )

        # Generate physical custom thumbnail image file
        if status_callback:
            status_callback(8, "Generating visual thumbnail blueprint...")
        thumbnail_filename = f"thumbnail_v{version}_{os.urandom(4).hex()}.png"
        try:
            thumb_start = time.time()
            thumbnail_url = video_svc.generate_thumbnail(
                image_paths=product_images or [],
                text=thumbnail_data["text"],
                output_filename=thumbnail_filename
            )
            thumb_duration = time.time() - thumb_start
            logger.info(f"[PERFORMANCE PROFILING] Thumbnail image generation completed in {thumb_duration:.2f} seconds.")
            thumbnail_data["image_url"] = thumbnail_url
            logger.info(f"Custom thumbnail image generated: {thumbnail_url}")
        except Exception as e:
            logger.error(f"Error generating custom thumbnail: {e}", exc_info=True)
            thumbnail_data["image_url"] = ""

        # Translations, voiceovers and video rendering pipeline in parallel
        if status_callback:
            status_callback(8, "Stitching regional voiceovers & rendering MP4 video clips...")
        from concurrent.futures import ThreadPoolExecutor

        languages = ["English", "Hindi", "Tamil", "Telugu", "Malayalam"]
        translations_dict = {}
        voiceovers_dict = {}
        videos_dict = {}

        def process_lang(lang):
            logger.info(f"[STAGE 85%+] Starting pipeline for language: {lang}")
            lang_start = time.time()
            try:
                # Generate translated script texts (mock / IndicTrans2 wrapper fallback)
                logger.info(f"[STAGE 85%+] [1/4 TRANSLATION] Starting translation to '{lang}'...")
                t_start = time.time()
                from backend.agents.translation_agent import translate_content_indictrans2
                translated_reel = translate_content_indictrans2(script_data["script_text"], lang)
                
                lang_translations = {
                    "youtube_script": translate_content_indictrans2(script_data["script_text"], lang),
                    "reel_script": translated_reel,
                    "whatsapp_post": translate_content_indictrans2(script_data["seo_description"], lang),
                    "google_business_post": translate_content_indictrans2(script_data["title"], lang)
                }
                t_duration = time.time() - t_start
                logger.info(f"[PERFORMANCE PROFILING] [{lang}] [1/4 TRANSLATION] Translation complete in {t_duration:.2f}s. Hook preview: '{translated_reel[:40]}...'")

                # Generate Voiceover MP3
                audio_filename = f"voiceover_{lang.lower()}_v{version}_{os.urandom(4).hex()}.mp3"
                logger.info(f"[STAGE 85%+] [2/4 VOICEOVER] Launching TTS voiceover generation for '{lang}' (filename: {audio_filename})...")
                v_start = time.time()
                audio_path = voice_svc.generate_voiceover(translated_reel, lang, audio_filename)
                v_duration = time.time() - v_start
                logger.info(f"[PERFORMANCE PROFILING] [{lang}] [2/4 VOICEOVER] Voiceover synthesis complete in {v_duration:.2f}s. Path: {audio_path}")
                
                # Dynamically load audio duration to ensure precise metadata sync
                try:
                    logger.info(f"[STAGE 85%+] [3/4 DURATION] Loading moviepy AudioFileClip to check audio duration for '{lang}'...")
                    d_start = time.time()
                    from moviepy.editor import AudioFileClip
                    audio_clip = AudioFileClip(audio_path)
                    audio_duration = audio_clip.duration
                    audio_clip.close()
                    d_duration = time.time() - d_start
                    logger.info(f"[PERFORMANCE PROFILING] [{lang}] [3/4 DURATION] Inspected audio duration in {d_duration:.2f}s. Value: {audio_duration}s")
                except Exception as duration_err:
                    logger.error(f"[STAGE 85%+] [3/4 DURATION] Failed to inspect audio clip duration: {duration_err}. Defaulting to 10.0s.")
                    audio_duration = 10.0

                lang_voiceover = {
                    "audio_url": f"/static/media/{audio_filename}",
                    "local_path": audio_path,
                    "duration": audio_duration
                }

                # Generate Video MP4 with multi-photo support and subtitle timed rendering
                video_filename = f"video_{lang.lower()}_v{version}_{os.urandom(4).hex()}.mp4"
                logger.info(f"[STAGE 85%+] [4/4 VIDEO] Initializing video rendering & subtitles for '{lang}' (filename: {video_filename})...")
                vid_start = time.time()
                video_path = video_svc.generate_marketing_video(
                    audio_path=audio_path,
                    image_paths=product_images,
                    voiceover_text=translated_reel,
                    output_filename=video_filename
                )
                vid_duration = time.time() - vid_start
                logger.info(f"[PERFORMANCE PROFILING] [{lang}] [4/4 VIDEO] Video rendering complete in {vid_duration:.2f}s. Path: {video_path}")

                lang_video = {
                    "video_url": f"/static/media/{video_filename}",
                    "local_path": video_path
                }
                
                lang_total = time.time() - lang_start
                logger.info(f"[PERFORMANCE PROFILING] [{lang}] TOTAL PIPELINE completed in {lang_total:.2f}s")
                return lang, lang_translations, lang_voiceover, lang_video
            except Exception as e:
                logger.error(f"[STAGE 85%+] ERROR in processing pipeline for language {lang}: {e}", exc_info=True)
                # Return fallbacks so the entire pipeline doesn't crash if one language fails
                fallback_audio = f"voiceover_{lang.lower()}_v{version}_fallback.mp3"
                fallback_video = f"video_{lang.lower()}_v{version}_fallback.mp4"
                return (
                    lang,
                    {
                        "youtube_script": script_data["script_text"],
                        "reel_script": script_data["script_text"],
                        "whatsapp_post": script_data["seo_description"],
                        "google_business_post": script_data["title"]
                    },
                    {
                        "audio_url": f"/static/media/{fallback_audio}",
                        "local_path": "",
                        "duration": 10.0
                    },
                    {
                        "video_url": f"/static/media/{fallback_video}",
                        "local_path": ""
                    }
                )

        # Run translations, voiceovers, and videos in parallel to maximize speed
        logger.info(f"[PERFORMANCE OPTIMIZATION] Spawning ThreadPoolExecutor to run 5 Indic languages in parallel...")
        parallel_start = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_lang, languages))
            
        parallel_duration = time.time() - parallel_start
        logger.info(f"[PERFORMANCE PROFILING] Parallel regional rendering (5 languages) completed in {parallel_duration:.2f} seconds.")

        for lang, lang_translations, lang_voiceover, lang_video in results:
            translations_dict[lang] = lang_translations
            voiceovers_dict[lang] = lang_voiceover
            videos_dict[lang] = lang_video
            
        total_duration = time.time() - start_time
        logger.info(f"[PERFORMANCE PROFILING] TOTAL CAMPAIGN GENERATION PIPELINE completed in {total_duration:.2f} seconds.")

        return {

            "version": version,
            "qa_score": qa_result["score"],
            "qa_status": qa_result["status"],
            "keywords": {
                "primary": primary_kws,
                "secondary": secondary_kws,
                "long_tail": long_tail_kws,
                "intent": intent_kws,
                "regional": regional_kws
            },
            "topics": topics,
            "script": script_data,
            "thumbnail": thumbnail_data,
            "translations": translations_dict,
            "voiceovers": voiceovers_dict,
            "videos": videos_dict
        }

marketing_crew = MarketingCrew()
