# backend/crews/marketing_crew.py
import os
import json
import logging
import random
from typing import Dict, Any, List
from crewai import Crew, Task, Process

from backend.agents.keyword_agent import make_keyword_agent
from backend.agents.trend_agent import make_trend_agent, get_trending_keywords
from backend.agents.script_agent import make_script_agent
from backend.agents.thumbnail_agent import make_thumbnail_agent
from backend.agents.quality_agent import make_quality_agent, audit_campaign_quality
from backend.agents.publishing_agent import make_publishing_agent

from backend.services.voice_service import voice_svc
from backend.services.video_service import video_svc
from backend.services.youtube_publishing_service import youtube_publish_svc
from backend.services.supabase_service import supabase_svc
from backend.config import settings

logger = logging.getLogger("vyaparai.crews.marketing_crew")

def get_randomized_script_data(product_name: str, description: str) -> dict:
    titles = [
        f"Why this {product_name} is a game changer! 💥",
        f"The secret behind pure {product_name} 🍃",
        f"Say goodbye to stale {product_name}! Sourced fresh 📦",
        f"Unboxing the best {product_name} in India 🇮🇳",
        f"Is your {product_name} actually pure? Let's check 🔍",
        f"How to use {product_name} for maximum health benefits ✨",
        f"From local farms to your home: {product_name} 🏡",
        f"Why everyone is switching to our {product_name} today! 🔥",
        f"Secrets of the highest quality {product_name} revealed! 🤫"
    ]
    
    hooks = [
        f"Are you tired of artificial, chemical-filled products? 🚫 Sourced directly from fresh local farms, our {product_name} is as pure as it gets!",
        f"If you're still buying normal market products, stop! 🛑 Here is why our premium {product_name} is completely different.",
        f"Want to know what real quality feels like? ✨ Let's talk about our fresh, handpicked {product_name}.",
        f"Is your family using stale, low-grade products? ☕ Upgrade to our premium {product_name} sourced straight from Idukki hills!",
        f"We're launching the freshest batch of {product_name} today! Sourced fresh and packed with nutrients. Check it out!",
        f"Did you know that most market options are colored and artificially flavored? 🧪 Our {product_name} is 100% natural, clean, and authentic.",
        f"Imagine having the rich, natural aroma of fresh {product_name} in your home. 🏡 Sourced responsibly, shipped direct."
    ]
    
    bodies = [
        f"Introducing our premium {product_name}. Sourced with high standards, it is chemical-free, natural, and rich in essential nutrients. Packaged with a fresh-lock seal to preserve active goodness.",
        f"Our {product_name} is handpicked by local farmers, vacuum-sealed, and shipped fresh within 24 hours. No artificial colors, preservatives, or fillers.",
        f"Experience the natural goodness of pure {product_name}. Cold-pressed and processed traditionally to maintain rich aroma and beneficial compounds.",
        f"We harvest {product_name} under strict organic controls. This guarantees maximum potency, longer shelf life, and unmatched freshness in every pack."
    ]
    
    ctas = [
        f"Reply now to get an exclusive 10% discount and free shipping on your first pack!",
        f"Message us today to claim our special launch offer: Buy 2 Get 1 Free!",
        f"Hurry! Tap the link or reply to this post to order your pack before stocks run out.",
        f"Send us a direct message now to order and get free cash-on-delivery across India!",
        f"Comment below or DM us 'ORDER' to get instant delivery updates and special pricing!"
    ]
    
    thumbnail_texts = [
        f"Pure {product_name}!",
        "100% Organic!",
        "Fresh & Natural!",
        "Secret Revealed!",
        "Best in India!",
        "Double Quality!",
        "Real vs Fake!"
    ]
    
    seo_descriptions = [
        f"Buy premium quality organic {product_name} online with nationwide shipping. Cash on delivery available.",
        f"Order fresh, chemical-free {product_name} directly from local farms. Best price and guaranteed authenticity.",
        f"Discover the health benefits of 100% natural {product_name}. Sourced sustainably, packed with fresh-lock seal."
    ]
    
    hashtags_pool = [
        ["LocalVyapar", "PremiumQuality", "IndianMade"],
        ["VocalForLocal", "OrganicSpices", "HealthyLiving"],
        ["PureNatural", "FarmFresh", "DirectToConsumer"],
        ["IndianBusiness", "HealthyChoices", "EcoFriendly"]
    ]
    
    title = random.choice(titles)
    hook = random.choice(hooks)
    body = random.choice(bodies)
    cta = random.choice(ctas)
    thumbnail_text = random.choice(thumbnail_texts)
    seo_desc = random.choice(seo_descriptions)
    
    full_script_text = f"{hook} {body} {cta}"
    
    scene_breakdown = [
        {
            "scene": 1,
            "instruction": f"Show a high-quality visual of the fresh {product_name} in a beautiful rustic setting.",
            "voiceover": hook
        },
        {
            "scene": 2,
            "instruction": f"Show product packaging with close-up highlights of the organic labels and fresh seal.",
            "voiceover": body
        },
        {
            "scene": 3,
            "instruction": f"Show a clean call-to-action screen with order instructions and a discount badge.",
            "voiceover": cta
        }
    ]
    
    cap1_end = min(7.0, len(hook.split()) * 0.4)
    cap2_end = cap1_end + min(7.0, len(body.split()) * 0.4)
    cap3_end = cap2_end + min(7.0, len(cta.split()) * 0.4)
    
    caption_timeline = [
        {"start": 0.0, "end": round(cap1_end, 1), "text": hook},
        {"start": round(cap1_end, 1), "end": round(cap2_end, 1), "text": body},
        {"start": round(cap2_end, 1), "end": round(cap3_end, 1), "text": cta}
    ]
    
    clean_product_name = "".join(c for c in product_name if c.isalnum())
    tags = [clean_product_name] + random.choice(hashtags_pool)
    
    return {
        "title": title,
        "hook": hook,
        "script_text": full_script_text,
        "scene_breakdown": scene_breakdown,
        "caption_timeline": caption_timeline,
        "thumbnail_text": thumbnail_text,
        "seo_description": seo_desc,
        "hashtags": tags
    }

class MarketingCrew:
    def __init__(self):
        self.keyword_agent = make_keyword_agent()
        self.trend_agent = make_trend_agent()
        self.script_agent = make_script_agent()
        self.thumbnail_agent = make_thumbnail_agent()
        self.quality_agent = make_quality_agent()
        self.publishing_agent = make_publishing_agent()

    def run(
        self, 
        product_name: str, 
        description: str, 
        location: str, 
        product_images: List[str] = None,
        force_feedback: str = None,
        version: int = 1
    ) -> Dict[str, Any]:
        """
        Executes the expanded 8-agent CrewAI pipeline.
        Implements QualityAgent scoring and dynamic regeneration loop.
        """
        logger.info(f"Initiating Expanded Marketing Crew for product: {product_name} (Version: {version})")
        
        # Define image count string for prompt
        image_count = len(product_images) if product_images else 0
        img_info = f"Product has {image_count} visual images uploaded."

        # Step 1: Keyword Classification Task
        keyword_task = Task(
            description=f"""Analyze the product name: '{product_name}' and description: '{description}'.
Determine the target market. Categorize and generate:
- Primary Keywords (core product terms)
- Secondary Keywords (associated snack/craft tags)
- Long Tail Keywords (longer search phrases)
- Purchase Intent Keywords (e.g. 'buy', 'order')
- Regional Keywords (relating to local Indian regions/states)""",
            expected_output="JSON structure mapping: primary, secondary, long_tail, intent, regional",
            agent=self.keyword_agent
        )

        # Step 2: Trend Analysis Task
        trend_task = Task(
            description=f"Analyze search demand signals in location '{location}' for product '{product_name}'. List 10 viral video topics and 3 optimized SEO titles.",
            expected_output="JSON structure mapping: trending_topics, seo_titles",
            agent=self.trend_agent
        )

        # Step 3: Script Generation Task
        styles = [
            "storytelling (narrating a journey of how the product was created)",
            "highly energetic (hooking the viewer with fast-paced, high impact benefits)",
            "dramatic unboxing (focusing on the visual details and first impressions of the package)",
            "problem-solving (starting directly with a severe pain point the product solves)",
            "customer-testimony (speaking from the perspective of a passionate, satisfied buyer)",
            "educational (sharing an interesting fact or secret tip about the product category)",
            "casual local recommendation (speaking like a friendly neighbor sharing a great discovery)"
        ]
        chosen_style = random.choice(styles)
        
        script_desc = f"""Create a promotional script bundle for the specific product: '{product_name}'.
Product Description: {description}

IMPORTANT DIRECTIVES:
1. Identify the core product and exactly what makes it unique.
2. Formulate a unique sales strategy tailored to THIS exact product. Do not use generic templates.
3. Write completely innovative dialogues and hooks for this video. Avoid repeating past formats.
4. Write in a '{chosen_style}' style. Make it extremely unique and distinct from standard copies.

Output MUST be a JSON object containing EXACTLY these keys:
- "title"
- "hook" (0-10 sec, attention grabber)
- "script_text" (The full spoken narrative)
- "scene_breakdown" (Array of objects with "scene", "instruction", "voiceover")
- "caption_timeline" (Array of objects with "start", "end", "text")
- "thumbnail_text"
- "seo_description"
- "hashtags" (Array of strings)

Ensure the voice is warm, clear, and engaging.
{img_info}"""
        
        if force_feedback:
            script_desc += f"\n\nREGENERATION FEEDBACK FROM PREVIOUS AUDIT: {force_feedback}. Make sure to fix these points in this version."

        script_task = Task(
            description=script_desc,
            expected_output="JSON structure matching script layout tags.",
            agent=self.script_agent
        )

        # Step 4: Thumbnail Creation Task
        thumbnail_task = Task(
            description=f"Design a high-CTR thumbnail for '{product_name}'. Suggest a layout configuration, overlay text, and a prompt for image generation models.",
            expected_output="JSON structure mapping: layout, text, prompt",
            agent=self.thumbnail_agent
        )

        # Create Sequential Crew
        crew = Crew(
            agents=[self.keyword_agent, self.trend_agent, self.script_agent, self.thumbnail_agent],
            tasks=[keyword_task, trend_task, script_task, thumbnail_task],
            process=Process.sequential,
            verbose=True
        )

        # Kickoff Crew
        try:
            crew.kickoff()
            logger.info("Crew execution completed. Compiling and auditing results...")
        except Exception as e:
            logger.warning(f"CrewAI execution failed: {e}. Falling back to default campaign assets.")

        # Formulate fallback records to ensure resilient executions
        primary_kws = [f"{product_name} online", f"buy {product_name}"]
        secondary_kws = [f"handmade {product_name}", f"traditional {product_name}"]
        long_tail_kws = [f"best {product_name} in India", f"order organic {product_name} online"]
        intent_kws = [f"buy {product_name}", f"order {product_name} price"]
        regional_kws = [f"{product_name} south india", f"{product_name} kerala"]

        topics = [
            f"Why this {product_name} is going viral",
            f"How traditional {product_name} is made",
            f"Top 5 benefits of {product_name}"
        ]
        
        # Helper to parse agent output
        def extract_json(task_output):
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

        # Attempt to parse keywords from agent output
        keyword_data = extract_json(keyword_task.output)
        if keyword_data:
            primary_kws = keyword_data.get("primary", primary_kws)
            secondary_kws = keyword_data.get("secondary", secondary_kws)
            long_tail_kws = keyword_data.get("long_tail", long_tail_kws)
            intent_kws = keyword_data.get("intent", intent_kws)
            regional_kws = keyword_data.get("regional", regional_kws)
            logger.info(f"Successfully extracted custom keywords: {primary_kws}")
        else:
            logger.warning("Using hardcoded fallback keywords")

        # Attempt to parse trending topics from agent output
        trend_data = extract_json(trend_task.output)
        if trend_data:
            topics = trend_data.get("trending_topics", topics)
            logger.info(f"Successfully extracted custom trending topics: {topics}")
        else:
            logger.warning("Using hardcoded fallback topics")

        # Attempt to parse script data from agent output
        script_data = extract_json(script_task.output)

        if script_data and isinstance(script_data, dict):
            # Ensure all required keys exist to prevent KeyError
            required_keys = ["title", "hook", "script_text", "scene_breakdown", "caption_timeline", "thumbnail_text", "seo_description", "hashtags"]
            missing_keys = [k for k in required_keys if k not in script_data]
            if missing_keys:
                logger.warning(f"Script data is missing keys: {missing_keys}. Filling with dynamic fallback values.")
                rand_data = get_randomized_script_data(product_name, description)
                for k in missing_keys:
                    script_data[k] = rand_data[k]
        else:
            logger.warning("Failed to parse script JSON from agent. Using default fallback template.")
            script_data = get_randomized_script_data(product_name, description)

        thumbnail_data = extract_json(thumbnail_task.output)
        
        if thumbnail_data and isinstance(thumbnail_data, dict):
            if "layout" not in thumbnail_data:
                thumbnail_data["layout"] = "Product centered with bold yellow text overlay on dark slate background"
            if "text" not in thumbnail_data:
                thumbnail_data["text"] = script_data.get("thumbnail_text", f"Pure {product_name}!")
            if "prompt" not in thumbnail_data:
                thumbnail_data["prompt"] = f"Close-up photo of {product_name} on a wooden table, soft warm lighting, 8k resolution"
        else:
            thumbnail_data = {
                "layout": random.choice([
                    "Product centered with bold yellow text overlay on dark slate background",
                    "Premium packaging showcase with clean minimalist typography",
                    "Rustic close-up with bold organic badges and text overlay"
                ]),
                "text": script_data.get("thumbnail_text", f"Pure {product_name}!"),
                "prompt": random.choice([
                    f"Close-up photo of {product_name} on a wooden table, soft warm lighting, 8k resolution",
                    f"A beautiful rustic bowl overflowing with fresh {product_name}, dark moody background, studio lighting",
                    f"Premium packaging of {product_name} standing elegantly on a marble slab, natural sun rays"
                ])
            }

        # Quality Check Loop
        qa_result = audit_campaign_quality(script_data, primary_kws + long_tail_kws)
        
        # Simulate regeneration once if QA score fails (or if forced for loop testing)
        if qa_result["status"] == "REGENERATE" and version < 2:
            logger.warning("Quality score < 80. Triggering automatic regeneration loop...")
            return self.run(
                product_name=product_name,
                description=description,
                location=location,
                product_images=product_images,
                force_feedback=qa_result["feedback"],
                version=version + 1
            )

        # Generate physical custom thumbnail image file
        thumbnail_filename = f"thumbnail_v{version}_{os.urandom(4).hex()}.png"
        try:
            thumbnail_url = video_svc.generate_thumbnail(
                image_paths=product_images or [],
                text=thumbnail_data["text"],
                output_filename=thumbnail_filename
            )
            thumbnail_data["image_url"] = thumbnail_url
            logger.info(f"Custom thumbnail image generated: {thumbnail_url}")
        except Exception as e:
            logger.error(f"Failed to generate physical thumbnail image: {e}")
            thumbnail_data["image_url"] = None

        # Translations, voiceovers and video rendering pipeline in parallel
        from concurrent.futures import ThreadPoolExecutor

        languages = ["English", "Hindi", "Tamil", "Telugu", "Malayalam"]
        translations_dict = {}
        voiceovers_dict = {}
        videos_dict = {}

        def process_lang(lang):
            logger.info(f"Starting pipeline for language: {lang}")
            try:
                # Generate translated script texts (mock / IndicTrans2 wrapper fallback)
                from backend.agents.translation_agent import translate_content_indictrans2
                translated_reel = translate_content_indictrans2(script_data["script_text"], lang)
                
                lang_translations = {
                    "youtube_script": translate_content_indictrans2(script_data["script_text"], lang),
                    "reel_script": translated_reel,
                    "whatsapp_post": translate_content_indictrans2(script_data["seo_description"], lang),
                    "google_business_post": translate_content_indictrans2(script_data["title"], lang)
                }

                # Generate Voiceover MP3
                audio_filename = f"voiceover_{lang.lower()}_v{version}_{os.urandom(4).hex()}.mp3"
                audio_path = voice_svc.generate_voiceover(translated_reel, lang, audio_filename)
                
                # Dynamically load audio duration to ensure precise metadata sync
                try:
                    from moviepy.editor import AudioFileClip
                    audio_clip = AudioFileClip(audio_path)
                    audio_duration = audio_clip.duration
                    audio_clip.close()
                except Exception:
                    audio_duration = 10.0

                lang_voiceover = {
                    "audio_url": f"/static/media/{audio_filename}",
                    "local_path": audio_path,
                    "duration": audio_duration
                }

                # Generate Video MP4 with multi-photo support and subtitle timed rendering
                video_filename = f"video_{lang.lower()}_v{version}_{os.urandom(4).hex()}.mp4"
                video_path = video_svc.generate_marketing_video(
                    audio_path=audio_path,
                    image_paths=product_images,
                    voiceover_text=translated_reel,
                    output_filename=video_filename
                )

                lang_video = {
                    "video_url": f"/static/media/{video_filename}",
                    "local_path": video_path
                }
                
                logger.info(f"Finished pipeline successfully for language: {lang}")
                return lang, lang_translations, lang_voiceover, lang_video
            except Exception as e:
                logger.error(f"Error in processing pipeline for language {lang}: {e}")
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

        # Run translations, voiceovers, and videos in parallel threads
        with ThreadPoolExecutor(max_workers=len(languages)) as executor:
            results = list(executor.map(process_lang, languages))

        for lang, lang_translations, lang_voiceover, lang_video in results:
            translations_dict[lang] = lang_translations
            voiceovers_dict[lang] = lang_voiceover
            videos_dict[lang] = lang_video

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
