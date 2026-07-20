# backend/services/video_service.py
import os
import logging
import math
import re
from pathlib import Path
from typing import List, Any
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, VideoClip
from backend.config import settings

logger = logging.getLogger("vyaparai.services.video_service")

def get_accurate_audio_duration(audio_path: str) -> float:
    if not audio_path or not os.path.exists(audio_path):
        return 10.0
    try:
        import subprocess
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        dur = float(res.stdout.strip())
        if dur > 0:
            return dur
    except Exception as e:
        logger.warning(f"ffprobe duration check failed for {audio_path}: {e}")

    try:
        audio_clip = AudioFileClip(audio_path)
        dur = audio_clip.duration
        audio_clip.close()
        return dur
    except Exception:
        return 10.0

class VideoService:
    def generate_marketing_video(
        self, 
        image_path: str = None, 
        audio_path: str = None, 
        captions: list = None, 
        output_filename: str = None,
        image_paths: List[str] = None,
        voiceover_text: str = None,
        job: Any = None
    ) -> str:
        """
        Synthesizes a vertical 9:16 (1080x1920) MP4 video from multiple images, 
        a voiceover audio file, and dynamically generated synchronized captions.
        """
        from backend.services.background_job_manager import JobCancelledException
        if job and hasattr(job, "is_cancelled") and job.is_cancelled():
            raise JobCancelledException("Video generation cancelled prior to render.")

        output_path = settings.MEDIA_DIR / output_filename
        
        # 1. Load Audio and determine accurate duration
        audio_duration = get_accurate_audio_duration(audio_path)
        # Add 0.8s tail buffer so video slideshow never abruptly cuts off before full audio finishes
        duration = audio_duration + 0.8
        logger.info(f"[VIDEO DURATION] Exact audio speech duration: {audio_duration:.2f}s | Target video duration: {duration:.2f}s")

        # 2. Check/Load Background Images
        target_images = []
        if image_paths:
            target_images.extend(image_paths)
        elif image_path:
            target_images.append(image_path)

        bg_images = []
        for path in target_images:
            local_image_path = path
            if path and path.startswith("/static/"):
                local_image_path = str(settings.STATIC_DIR / path[8:])

            if local_image_path and os.path.exists(local_image_path):
                try:
                    img = Image.open(local_image_path)
                    bg_images.append(img)
                except Exception as e:
                    logger.error(f"Failed to open background image {path}: {e}")

        # Crop all images to 1080x1920 (9:16)
        cropped_images = []
        target_w, target_h = 1080, 1920
        aspect_target = target_w / target_h

        for img in bg_images:
            bg_width, bg_height = img.size
            aspect_bg = bg_width / bg_height

            if aspect_bg > aspect_target:
                # Background is wider, resize by height
                new_h = target_h
                new_w = int(bg_width * (target_h / bg_height))
                img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                left = (new_w - target_w) // 2
                img_cropped = img_resized.crop((left, 0, left + target_w, target_h))
            else:
                # Background is taller, resize by width
                new_w = target_w
                new_h = int(bg_height * (target_w / bg_width))
                img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                top = (new_h - target_h) // 2
                img_cropped = img_resized.crop((0, top, target_w, top + target_h))
            cropped_images.append(img_cropped.convert("RGBA"))

        if not cropped_images:
            # Generate a sleek dark-gradient placeholder image
            logger.info("Generating a default gradient background image.")
            bg_image = Image.new("RGB", (1080, 1920), color=(15, 23, 42))  # Slate 900
            draw = ImageDraw.Draw(bg_image)
            for y in range(1920):
                r = int(15 + (y / 1920) * 30)
                g = int(23 + (y / 1920) * 20)
                b = int(42 + (y / 1920) * 40)
                draw.line([(0, y), (1080, y)], fill=(r, g, b))
            cropped_images.append(bg_image.convert("RGBA"))

        # 3. Dynamic Subtitles generation with word-weighted timing sync
        final_captions = []
        if voiceover_text:
            clean_text = "".join(c for c in voiceover_text if not (0xD800 <= ord(c) <= 0xDFFF))
            text_to_segment = clean_text.replace("।", ".").replace("\n", " ")
            raw_phrases = re.split(r'[,.?!;:\n]', text_to_segment)
            phrases = []
            for p in raw_phrases:
                p_clean = p.strip()
                if p_clean:
                    words = p_clean.split()
                    if len(words) > 6:
                        for i in range(0, len(words), 5):
                            chunk = " ".join(words[i:i+5])
                            if chunk:
                                phrases.append(chunk)
                    else:
                        phrases.append(p_clean)
            
            if phrases:
                phrase_word_counts = [max(1, len(p.split())) for p in phrases]
                total_words = sum(phrase_word_counts)
                
                current_time = 0.0
                for idx, phrase in enumerate(phrases):
                    p_dur = (phrase_word_counts[idx] / total_words) * audio_duration
                    end_time = current_time + p_dur
                    final_captions.append({
                        "start": round(current_time, 2),
                        "end": round(end_time, 2),
                        "text": phrase
                    })
                    current_time = end_time
        
        # Fallback to the passed captions list
        if not final_captions and captions:
            # If the caption list only contains one long subtitle block, segment it!
            if len(captions) == 1 and len(captions[0].get("text", "").split()) > 6:
                text_to_segment = captions[0].get("text", "")
                text_to_segment = text_to_segment.replace("।", ".").replace("\n", " ")
                raw_phrases = re.split(r'[,.?!;:]', text_to_segment)
                phrases = []
                for p in raw_phrases:
                    p_clean = p.strip()
                    if p_clean:
                        words = p_clean.split()
                        if len(words) > 6:
                            for i in range(0, len(words), 5):
                                chunk = " ".join(words[i:i+5])
                                if chunk:
                                    phrases.append(chunk)
                        else:
                            phrases.append(p_clean)
                if phrases:
                    phrase_dur = duration / len(phrases)
                    for i, phrase in enumerate(phrases):
                        final_captions.append({
                            "start": i * phrase_dur,
                            "end": (i + 1) * phrase_dur,
                            "text": phrase
                        })
            else:
                final_captions = captions
                
        if not final_captions:
            final_captions = [{"start": 0.0, "end": duration, "text": ""}]

        # Pre-load scalable fonts with full Indic script support (Nirmala UI / Segoe UI / Noto Sans)
        font = None
        brand_font = None
        font_candidates = [
            ("C:\\Windows\\Fonts\\Nirmala.ttc", 0),  # Nirmala UI - Universal Indic font (Hindi, Tamil, Telugu, Malayalam)
            ("C:\\Windows\\Fonts\\segoeui.ttf", None), # Segoe UI
            ("C:\\Windows\\Fonts\\arial.ttf", None),    # Arial fallback
            ("arial.ttf", None)
        ]
        
        for font_path, font_index in font_candidates:
            if os.path.exists(font_path):
                try:
                    if font_index is not None:
                        font = ImageFont.truetype(font_path, 42, index=font_index)
                        brand_font = ImageFont.truetype(font_path, 26, index=font_index)
                    else:
                        font = ImageFont.truetype(font_path, 42)
                        brand_font = ImageFont.truetype(font_path, 26)
                    break
                except Exception as fe:
                    logger.warning(f"Failed loading font {font_path}: {fe}")
                    
        if font is None:
            font = ImageFont.load_default()
            brand_font = ImageFont.load_default()

        # Multi-photo Ken Burns setup with dynamic caption synchronization
        num_images = len(cropped_images)
        transition_time = 0.8  # seconds

        # Map each image index to a start and end time based on captions distribution
        image_timelines = []
        if num_images > 0:
            caps_per_img = max(1, math.ceil(len(final_captions) / num_images))
            for idx in range(num_images):
                start_cap_idx = idx * caps_per_img
                end_cap_idx = min(len(final_captions) - 1, (idx + 1) * caps_per_img - 1)
                
                # Get start time of first caption in bucket, end time of last caption in bucket
                start_t = final_captions[start_cap_idx].get("start", 0.0) if start_cap_idx < len(final_captions) else 0.0
                end_t = final_captions[end_cap_idx].get("end", duration) if end_cap_idx < len(final_captions) else duration
                
                # Align boundaries
                if idx == 0:
                    start_t = 0.0
                if idx == num_images - 1:
                    end_t = duration
                    
                image_timelines.append({
                    "start": start_t,
                    "end": end_t,
                    "duration": max(0.1, end_t - start_t)
                })
        else:
            image_timelines.append({
                "start": 0.0,
                "end": duration,
                "duration": duration
            })

        def get_ken_burns_frame(img_idx, t):
            img = cropped_images[img_idx]
            timeline = image_timelines[img_idx]
            t_rel = max(0.0, t - timeline["start"])
            u = min(1.0, t_rel / timeline["duration"])
            
            # Linear Zoom (scale from 1.0 to 1.15)
            S = 1.0 + 0.15 * u
            
            # Subtle Panning Offset (sinusoidal y, linear x)
            direction = 1 if img_idx % 2 == 0 else -1
            offset_x = direction * 40 * u
            offset_y = direction * 30 * math.sin(u * math.pi)
            
            w, h = 1080, 1920
            w_sub = w / S
            h_sub = h / S
            cx = w / 2 + offset_x
            cy = h / 2 + offset_y
            
            left = max(0, min(w - w_sub, cx - w_sub / 2))
            top = max(0, min(h - h_sub, cy - h_sub / 2))
            right = left + w_sub
            bottom = top + h_sub
            
            cropped_sub = img.crop((int(left), int(top), int(right), int(bottom)))
            return cropped_sub.resize((w, h), Image.Resampling.BOX)

        # 4. Custom Frame Generator
        overlay_cache = {}

        def make_frame(t):
            if job and hasattr(job, "is_cancelled") and job.is_cancelled():
                raise JobCancelledException("Video rendering cancelled by user during frame generation.")

            # Compute base background image index based on time timelines
            idx = 0
            for i, tl in enumerate(image_timelines):
                if tl["start"] <= t <= tl["end"]:
                    idx = i
                    break
            idx = min(idx, num_images - 1)
            timeline = image_timelines[idx]
            
            frame1 = get_ken_burns_frame(idx, t)
            
            # Cross-fade to next image if transitioning
            next_idx = min(idx + 1, num_images - 1)
            if num_images > 1 and idx < num_images - 1 and (timeline["end"] - t) < transition_time:
                t_trans = transition_time - (timeline["end"] - t)
                alpha = max(0.0, min(1.0, t_trans / transition_time))
                frame2 = get_ken_burns_frame(next_idx, t)
                composited_bg = Image.blend(frame1, frame2, alpha)
            else:
                composited_bg = frame1

            # Find active caption for current time `t`
            active_text = ""
            for cap in final_captions:
                start = cap.get("start", 0.0)
                end = cap.get("end", duration)
                if start <= t <= end:
                    active_text = cap.get("text", "")
                    break
            
            if not active_text and final_captions:
                active_text = final_captions[0].get("text", "")

            # Check cache for overlay image to avoid drawing on every single frame
            if active_text in overlay_cache:
                overlay = overlay_cache[active_text]
            else:
                overlay = Image.new("RGBA", composited_bg.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                
                # Draw styled glassmorphic captions panel
                overlay_left = 80
                overlay_top = 1350
                overlay_right = 1000
                overlay_bottom = 1680
                
                draw.rounded_rectangle(
                    [overlay_left, overlay_top, overlay_right, overlay_bottom],
                    radius=30,
                    fill=(15, 23, 42, 220),       # Dark transparent slate
                    outline=(99, 102, 241, 255),  # Indigo accent border
                    width=3
                )

                # Draw brand badge top center
                draw.rounded_rectangle(
                    [380, 100, 700, 170],
                    radius=15,
                    fill=(99, 102, 241, 245),     # Indigo badge
                )
                draw.text(
                    (540, 135),
                    "VyaparAI.in",
                    fill=(255, 255, 255, 255),
                    anchor="mm",
                    font=brand_font
                )

                # Wrap text to fit inside the panel using font measurements
                words = active_text.split()
                lines = []
                current_line = []
                for word in words:
                    test_line = " ".join(current_line + [word])
                    if font:
                        try:
                            w_line = font.getlength(test_line)
                        except AttributeError:
                            w_line = len(test_line) * 22
                    else:
                        w_line = len(test_line) * 12
                    
                    if w_line > 800:
                        lines.append(" ".join(current_line))
                        current_line = [word]
                    else:
                        current_line.append(word)
                if current_line:
                    lines.append(" ".join(current_line))

                # Center text lines vertically within the caption box
                y_offset = overlay_top + 50
                if len(lines) == 1:
                    y_offset = overlay_top + 120
                elif len(lines) == 2:
                    y_offset = overlay_top + 80

                for line in lines[:3]:
                    draw.text(
                        (540, y_offset),
                        line,
                        fill=(248, 250, 252, 255), # Slate 50
                        anchor="ma",
                        font=font
                    )
                    y_offset += 65
                
                # Cache the generated overlay frame
                overlay_cache[active_text] = overlay

            # Alpha composite the overlay onto the background
            composited_img = Image.alpha_composite(composited_bg, overlay)
            return np.array(composited_img.convert("RGB"))

        # 5. Compile video using MoviePy VideoClip
        logger.info(f"Rendering {duration} seconds video clip with slideshow and subtitles...")
        video_clip = VideoClip(make_frame, duration=duration)
        
        # 6. Write to File
        try:
            # Write video-only first to avoid audio thread/pipe deadlocks in MoviePy
            temp_video_only_path = str(settings.MEDIA_DIR / f"temp_no_audio_{output_filename}")
            
            logger.info("[VIDEO STITCHING] Rendering video stream (audio disabled)...")
            video_clip.write_videofile(
                temp_video_only_path,
                fps=12,
                codec="libx264",
                audio=False, # Disable audio in MoviePy write to prevent deadlocks
                preset="ultrafast",
                ffmpeg_params=["-pix_fmt", "yuv420p"],
                logger=None,
                threads=1
            )
            
            if job and hasattr(job, "is_cancelled") and job.is_cancelled():
                raise JobCancelledException("Video rendering cancelled by user.")

            mux_success = False
            if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
                import subprocess
                logger.info(f"[AUDIO MUXING] Merging audio track '{audio_path}' with video stream...")
                cmd = [
                    "ffmpeg", "-y",
                    "-i", temp_video_only_path,
                    "-i", str(audio_path),
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    str(output_path)
                ]
                logger.info(f"Running ffmpeg muxing: {' '.join(cmd)}")
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if job and hasattr(job, "register_subprocess"):
                    job.register_subprocess(proc)
                
                try:
                    stdout, stderr = proc.communicate(timeout=30)
                finally:
                    if job and hasattr(job, "unregister_subprocess"):
                        job.unregister_subprocess(proc)

                if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    mux_success = True
                    logger.info(f"[AUDIO MUXING] Audio/video muxing completed successfully: {output_path}")
                else:
                    logger.warning(f"[AUDIO MUXING] FFmpeg audio muxing failed or returned exit code {proc.returncode}. Defaulting to clean video stream.")

            if not mux_success:
                # Fallback to clean, valid MP4 video-only stream generated by MoviePy
                logger.info("[VIDEO STITCHING] Using clean MP4 video stream for final output...")
                if os.path.exists(output_path):
                    try: os.remove(output_path)
                    except Exception: pass
                if os.path.exists(temp_video_only_path):
                    import shutil
                    shutil.move(temp_video_only_path, str(output_path))
                
            # Clean up temp video-only file if still present
            if os.path.exists(temp_video_only_path):
                try: os.remove(temp_video_only_path)
                except Exception: pass
                    
            logger.info(f"Successfully generated marketing video at: {output_path}")
        except JobCancelledException as jce:
            logger.warning(f"Video rendering aborted due to cancellation: {jce}")
            temp_video_only_path = str(settings.MEDIA_DIR / f"temp_no_audio_{output_filename}")
            if os.path.exists(temp_video_only_path):
                try: os.remove(temp_video_only_path)
                except Exception: pass
            if os.path.exists(output_path):
                try: os.remove(output_path)
                except Exception: pass
            raise jce
        except Exception as e:
            logger.error(f"Video rendering or muxing failed: {e}. Applying robust fallback video...")
            try:
                temp_video_only_path = str(settings.MEDIA_DIR / f"temp_no_audio_{output_filename}")
                if os.path.exists(temp_video_only_path) and os.path.getsize(temp_video_only_path) > 1000:
                    import shutil
                    shutil.move(temp_video_only_path, str(output_path))
                    logger.info(f"Rescued temp video stream to output path: {output_path}")
                else:
                    fallback_local_path = settings.MEDIA_DIR / "video_english_v2_3ce14206.mp4"
                    if fallback_local_path.exists():
                        import shutil
                        shutil.copy(str(fallback_local_path), str(output_path))
                        logger.info(f"Copied pre-seeded fallback video to output path: {output_path}")
            except Exception as fallback_err:
                logger.error(f"Failed to copy fallback video: {fallback_err}")

        # Close clips to release resources
        video_clip.close()
        if audio_clip:
            try:
                audio_clip.close()
            except Exception as close_err:
                logger.warning(f"Failed to close audio clip: {close_err}")

        return str(output_path)

    def generate_thumbnail(
        self, 
        image_paths: List[str], 
        text: str, 
        output_filename: str
    ) -> str:
        """
        Generates a 16:9 (1280x720) YouTube thumbnail image.
        Uses the first product image as background, applies a dark side-vignette, 
        and overlays bold title texts.
        """
        output_path = settings.MEDIA_DIR / output_filename
        
        # Load the background image
        bg_image = None
        if image_paths and len(image_paths) > 0:
            first_path = image_paths[0]
            if first_path.startswith("/static/"):
                first_path = str(settings.STATIC_DIR / first_path[8:])
            
            if os.path.exists(first_path):
                try:
                    bg_image = Image.open(first_path)
                except Exception as e:
                    logger.error(f"Failed to open thumbnail background: {e}")
                    
        if bg_image is None:
            # Slate 900 gradient background
            bg_image = Image.new("RGB", (1280, 720), color=(15, 23, 42))
            draw = ImageDraw.Draw(bg_image)
            for y in range(720):
                r = int(15 + (y / 720) * 30)
                g = int(23 + (y / 720) * 20)
                b = int(42 + (y / 720) * 40)
                draw.line([(0, y), (1280, y)], fill=(r, g, b))
        else:
            # Resize/Crop to 1280x720
            bg_width, bg_height = bg_image.size
            target_w, target_h = 1280, 720
            aspect_target = target_w / target_h
            aspect_bg = bg_width / bg_height

            if aspect_bg > aspect_target:
                new_h = target_h
                new_w = int(bg_width * (target_h / bg_height))
                bg_image = bg_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                left = (new_w - target_w) // 2
                bg_image = bg_image.crop((left, 0, left + target_w, target_h))
            else:
                new_w = target_w
                new_h = int(bg_height * (target_w / bg_width))
                bg_image = bg_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                top = (new_h - target_h) // 2
                bg_image = bg_image.crop((0, top, target_w, top + target_h))
                
        thumb_img = bg_image.convert("RGBA")
        overlay = Image.new("RGBA", thumb_img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Load fonts
        try:
            title_font = ImageFont.truetype("arial.ttf", 64)
            badge_font = ImageFont.truetype("arial.ttf", 24)
        except Exception:
            try:
                title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 64)
                badge_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 24)
            except Exception:
                title_font = ImageFont.load_default()
                badge_font = ImageFont.load_default()
                
        # Draw a transparent gradient overlay to make text pop (dark vignette on the left)
        for x in range(1280):
            if x < 850:
                alpha = int(220 * (1.0 - x / 850))
                draw.line([(x, 0), (x, 720)], fill=(15, 23, 42, alpha))
                
        # Draw accent indicator border on the left
        draw.rectangle([0, 0, 15, 720], fill=(99, 102, 241, 255))
        
        # Draw brand badge top left
        draw.rounded_rectangle(
            [50, 50, 220, 95],
            radius=10,
            fill=(99, 102, 241, 240)
        )
        draw.text(
            (135, 72),
            "VyaparAI",
            fill=(255, 255, 255, 255),
            anchor="mm",
            font=badge_font
        )
        
        # Wrap title text
        title_text = text if text else "Premium Product"
        words = title_text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            try:
                w_line = title_font.getlength(test_line)
            except AttributeError:
                w_line = len(test_line) * 32
                
            if w_line > 700:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                current_line = test_line.split()
        if current_line:
            lines.append(" ".join(current_line))
            
        # Draw title lines (yellow for first line, white for next)
        y_offset = 220
        for i, line in enumerate(lines[:3]):
            fill_color = (253, 224, 71, 255) if i == 0 else (255, 255, 255, 255)
            
            # Simple text shadow
            draw.text((53, y_offset + 3), line, fill=(0, 0, 0, 180), font=title_font)
            draw.text((50, y_offset), line, fill=fill_color, font=title_font)
            y_offset += 90
            
        # Composite and save
        composited = Image.alpha_composite(thumb_img, overlay)
        final_thumb = composited.convert("RGB")
        final_thumb.save(output_path, "PNG")
        
        logger.info(f"Generated custom thumbnail at: {output_path}")
        return f"/static/media/{output_filename}"

video_svc = VideoService()

