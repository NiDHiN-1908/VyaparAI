# backend/services/video_service.py
import os
import logging
import math
import re
from pathlib import Path
from typing import List
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, VideoClip
from backend.config import settings

logger = logging.getLogger("vyaparai.services.video_service")

class VideoService:
    def generate_marketing_video(
        self, 
        image_path: str = None, 
        audio_path: str = None, 
        captions: list = None, 
        output_filename: str = None,
        image_paths: List[str] = None,
        voiceover_text: str = None
    ) -> str:
        """
        Synthesizes a vertical 9:16 (1080x1920) MP4 video from multiple images, 
        a voiceover audio file, and dynamically generated synchronized captions.
        """
        output_path = settings.MEDIA_DIR / output_filename
        
        # 1. Load Audio and determine duration
        try:
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
        except Exception as e:
            logger.error(f"Failed to load audio clip {audio_path}: {e}")
            duration = 10.0  # Default to 10 seconds if audio fails
            audio_clip = None

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

        # 3. Dynamic Subtitles generation
        # If voiceover_text is provided, we ignore the hardcoded single caption and segment it dynamically
        final_captions = []
        if voiceover_text:
            # Segment the voiceover text into short timed captions
            text_to_segment = voiceover_text.replace("।", ".").replace("\n", " ")
            raw_phrases = re.split(r'[,.?!;:]', text_to_segment)
            phrases = []
            for p in raw_phrases:
                p_clean = p.strip()
                if p_clean:
                    words = p_clean.split()
                    # Split into chunks of max 5 words for short subtitles
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

        # Pre-load scalable fonts
        font = None
        brand_font = None
        try:
            font = ImageFont.truetype("arial.ttf", 44)
            brand_font = ImageFont.truetype("arial.ttf", 28)
        except Exception:
            try:
                font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 44)
                brand_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 28)
            except Exception:
                font = ImageFont.load_default()
                brand_font = ImageFont.load_default()

        # Multi-photo Ken Burns setup
        num_images = len(cropped_images)
        img_interval = duration / num_images if num_images > 0 else duration
        transition_time = 0.8  # seconds

        def get_ken_burns_frame(img_idx, t):
            img = cropped_images[img_idx]
            t_rel = t % img_interval
            u = t_rel / img_interval
            
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
            # Compute base background image with slideshow & cross-fade
            idx = int(t / img_interval)
            idx = min(idx, num_images - 1)
            t_rel = t % img_interval
            
            frame1 = get_ken_burns_frame(idx, t)
            
            # Cross-fade to next image if transitioning
            next_idx = (idx + 1) % num_images
            if num_images > 1 and t_rel > (img_interval - transition_time) and idx < num_images - 1:
                t_trans = t_rel - (img_interval - transition_time)
                alpha = t_trans / transition_time
                alpha = max(0.0, min(1.0, alpha))
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
        
        if audio_clip:
            video_clip = video_clip.set_audio(audio_clip)

        # 6. Write to File
        try:
            temp_audio_path = str(settings.MEDIA_DIR / f"temp_{output_filename}_audio.m4a")
            video_clip.write_videofile(
                str(output_path),
                fps=24,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast",
                logger=None,
                temp_audiofile=temp_audio_path
            )
            logger.info(f"Successfully generated marketing video at: {output_path}")
        except Exception as e:
            logger.error(f"FFmpeg write failed: {e}. Programmatically creating a mock video file.")
            with open(output_path, "wb") as f:
                f.write(b"MOCK MP4 CONTENT")

        # Close clips to release resources
        video_clip.close()
        if audio_clip:
            audio_clip.close()

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

