# backend/services/voice_service.py
import os
import logging
from pathlib import Path
from gtts import gTTS
from backend.config import settings

logger = logging.getLogger("vyaparai.services.voice_service")

# Map target Indian languages to gTTS locale codes
LANG_CODE_MAP = {
    "hindi": "hi",
    "tamil": "ta",
    "telugu": "te",
    "malayalam": "ml",
    "english": "en"
}

class VoiceService:
    def __init__(self):
        self.coqui_available = False
        # Coqui TTS import check
        try:
            from TTS.api import TTS
            self.coqui_model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
            # We don't initialize on startup to avoid blocking API loads
            self.coqui_available = True
            logger.info("Coqui TTS libraries detected.")
        except ImportError:
            logger.info("Coqui TTS not installed. Falling back to gTTS (Google TTS) service.")

    def generate_voiceover(self, text: str, language: str, output_filename: str) -> str:
        """
        Synthesizes text into a voiceover file (MP3/WAV).
        Returns the absolute filepath to the created audio file.
        """
        output_path = settings.MEDIA_DIR / output_filename
        lang_key = language.lower().strip()
        lang_code = LANG_CODE_MAP.get(lang_key, "en")

        # Clean the text (remove brackets or headers)
        clean_text = text.replace("[Translated to Hindi]:", "").replace("[Translated to Tamil]:", "")
        clean_text = clean_text.replace("[Translated to Telugu]:", "").replace("[Translated to Malayalam]:", "")
        clean_text = clean_text.strip()[:400] # Limit length for stable generation

        # edge-tts voice mapping for natural and soft voices
        EDGE_VOICE_MAP = {
            "english": "en-IN-NeerjaNeural",
            "hindi": "hi-IN-SwaraNeural",
            "tamil": "ta-IN-PallaviNeural",
            "telugu": "te-IN-ShrutiNeural",
            "malayalam": "ml-IN-SobhanaNeural"
        }

        # Try edge-tts first
        try:
            import edge_tts
            import asyncio
            import threading

            voice_name = EDGE_VOICE_MAP.get(lang_key, "en-IN-NeerjaNeural")
            logger.info(f"Synthesizing voiceover with edge-tts using voice: {voice_name}")

            async def _synthesize_edge_tts(text_to_speak, voice_name, dest_path):
                communicate = edge_tts.Communicate(text_to_speak, voice_name)
                await communicate.save(dest_path)

            # Run in a dedicated thread to avoid any conflicts with existing event loops in FastAPI/uvicorn
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(_synthesize_edge_tts(clean_text, voice_name, str(output_path)))
                new_loop.close()

            t = threading.Thread(target=run_in_thread)
            t.start()
            t.join()

            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                logger.info(f"edge-tts successfully generated audio: {output_path}")
                return str(output_path)
            else:
                raise Exception("Generated audio file is empty or missing")

        except Exception as e:
            logger.error(f"edge-tts generation failed: {e}. Falling back to Coqui/gTTS.")

        if self.coqui_available:
            try:
                from TTS.api import TTS
                logger.info(f"Synthesizing voiceover with Coqui TTS for language: {language}")
                # XTTS supports multi-lingual, needs a speaker reference wav
                # We initialize locally here
                tts = TTS(self.coqui_model_name).to("cpu")
                # Synthesize directly
                tts.tts_to_file(
                    text=clean_text,
                    file_path=str(output_path),
                    speaker_wav=None, # In XTTS, can pass a speaker file or default
                    language=lang_code
                )
                logger.info(f"Coqui TTS successfully generated audio: {output_path}")
                return str(output_path)
            except Exception as e:
                logger.error(f"Coqui TTS generation failed: {e}. Falling back to gTTS.")

        # Fallback 1: gTTS (highly reliable online text-to-speech)
        try:
            logger.info(f"Synthesizing voiceover with gTTS for language: {language} (code: {lang_code})")
            tts_obj = gTTS(text=clean_text, lang=lang_code, slow=False)
            tts_obj.save(str(output_path))
            logger.info(f"gTTS successfully generated audio: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"gTTS failed: {e}. Generating a programmatic placeholder audio file.")

        # Fallback 2: Generate a programmatic simple wav if completely offline
        import wave
        import struct
        import math

        logger.info("Generating a programmatic sine-wave placeholder audio file.")
        wav_path = output_path.with_suffix(".wav")
        sample_rate = 8000.0
        duration = 5.0  # 5 seconds placeholder
        num_samples = int(duration * sample_rate)
        
        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setparams((1, 2, int(sample_rate), num_samples, "NONE", "not compressed"))
            for i in range(num_samples):
                # Simple 440Hz tone
                value = int(32767.0 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
                wav_file.writeframes(struct.pack("h", value))
        
        # Rename or keep wav as mp3 (since standard players can play it or we label it)
        os.rename(str(wav_path), str(output_path))
        return str(output_path)

voice_svc = VoiceService()

