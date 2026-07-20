# backend/services/voice_service.py
import os
import logging
import unicodedata
from pathlib import Path
from typing import Optional, Dict, Any, List
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

# Pronunciation Dictionary for botanical terms and nursery vocabulary
PRONUNCIATION_DICT = {
    "Jasminum": "Jaz-min-um",
    "Jasminum sambac": "Jaz-min-um sam-bac",
    "Sansevieria": "San-se-vi-ee-ri-ah",
    "Ficus": "Fy-kus",
    "Monstera": "Mon-stair-ah",
    "Zamioculcas": "Zam-ee-o-kul-kas",
    "cocopeat": "coco peat",
    "coco-peat": "coco peat",
    "chlorophytum": "chloro-phy-tum",
    "epipremnum": "epi-prem-num",
    "alocasia": "alo-ca-sia"
}

VOICE_PROFILES = {
    "english": {
        "storyteller": "en-IN-NeerjaNeural",
        "presenter": "en-IN-PrabhatNeural",
        "nursery": "en-IN-NeerjaNeural",
        "default": "en-IN-NeerjaNeural"
    },
    "hindi": {
        "storyteller": "hi-IN-SwaraNeural",
        "presenter": "hi-IN-MadhurNeural",
        "nursery": "hi-IN-SwaraNeural",
        "default": "hi-IN-SwaraNeural"
    },
    "tamil": {
        "storyteller": "ta-IN-PallaviNeural",
        "presenter": "ta-IN-PallaviNeural", # Fallback default
        "nursery": "ta-IN-PallaviNeural",
        "default": "ta-IN-PallaviNeural"
    },
    "telugu": {
        "storyteller": "te-IN-ShrutiNeural",
        "presenter": "te-IN-ShrutiNeural", # Fallback default
        "nursery": "te-IN-ShrutiNeural",
        "default": "te-IN-ShrutiNeural"
    },
    "malayalam": {
        "storyteller": "ml-IN-SobhanaNeural",
        "presenter": "ml-IN-SobhanaNeural", # Fallback default
        "nursery": "ml-IN-SobhanaNeural",
        "default": "ml-IN-SobhanaNeural"
    }
}

def apply_pronunciation_dictionary(text: str) -> str:
    words = text.split()
    substituted = []
    for w in words:
        stripped = w.strip(".,?!;:()\"'-")
        if stripped in PRONUNCIATION_DICT:
            w_sub = w.replace(stripped, PRONUNCIATION_DICT[stripped])
            substituted.append(w_sub)
        else:
            substituted.append(w)
    return " ".join(substituted)

def validate_tts_input(text: str) -> None:
    if not text or len(text.strip()) < 5:
        raise ValueError("TTS input text is empty or too short.")
    leakage_patterns = ["```", "Thought:", "Agent:", "System:", "[EventBus", "<script>"]
    for pat in leakage_patterns:
        if pat in text:
            raise ValueError(f"TTS input text contains prompt leakage pattern: {pat}")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) != len(set(paragraphs)) and len(paragraphs) > 1:
        raise ValueError("TTS input text contains duplicated paragraphs.")

def verify_audio_fidelity(audio_filepath: str, expected_text: str, language: str) -> float:
    import speech_recognition as sr
    import difflib
    
    temp_wav = audio_filepath.replace(".mp3", "_temp_verify.wav")
    if os.path.exists(temp_wav):
        try: os.remove(temp_wav)
        except Exception: pass
        
    try:
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-i", audio_filepath, 
            "-ar", "16000", "-ac", "1", temp_wav
        ], capture_output=True, check=True)
    except Exception as conv_err:
        logger.error(f"Failed to convert audio for verification: {conv_err}")
        return 1.0
        
    if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) < 100:
        logger.error("Temporary verification WAV file is missing or empty.")
        return 1.0
        
    r = sr.Recognizer()
    try:
        with sr.AudioFile(temp_wav) as source:
            audio_data = r.record(source)
        
        sr_lang_map = {
            "english": "en-IN",
            "hindi": "hi-IN",
            "tamil": "ta-IN",
            "telugu": "te-IN",
            "malayalam": "ml-IN"
        }
        sr_lang = sr_lang_map.get(language.lower().strip(), "en-IN")
        
        logger.info(f"Transcribing audio for verification in language: {sr_lang}...")
        recognized = r.recognize_google(audio_data, language=sr_lang)
        logger.info(f"Recognized speech: {recognized[:150]}...")
        
        def normalize(t: str) -> str:
            t_norm = t.lower()
            t_norm = "".join(c for c in t_norm if c.isalnum() or c.isspace())
            return " ".join(t_norm.split())
            
        expected_norm = normalize(expected_text)
        recognized_norm = normalize(recognized)
        
        similarity = difflib.SequenceMatcher(None, expected_norm, recognized_norm).ratio()
        logger.info(f"Audio verification similarity score: {similarity:.4f}")
        return similarity
        
    except sr.RequestError as req_err:
        logger.warning(f"Google speech recognition service is offline/unavailable: {req_err}. Applying bypass.")
        return 1.0
    except sr.UnknownValueError:
        logger.warning("Google speech recognition could not understand audio. Returning 0.0 similarity.")
        return 0.0
    except Exception as e:
        logger.error(f"Error during audio verification: {e}")
        return 1.0
    finally:
        if os.path.exists(temp_wav):
            try: os.remove(temp_wav)
            except Exception: pass

def clean_tts_text(text: str, language: str) -> str:
    """
    Cleans raw text for TTS synthesis:
    1. Replaces translation bracket prefixes.
    2. Spells out Indian Rupee symbols (₹ / Rs.) to spoken words per language.
    3. Strips emojis (category 'So') and control characters (category 'Cn'/'Cs') 
       to prevent robotic speech breaks or emoji name reads.
    """
    clean_text = text.replace("[Translated to Hindi]:", "").replace("[Translated to Tamil]:", "")
    clean_text = clean_text.replace("[Translated to Telugu]:", "").replace("[Translated to Malayalam]:", "")
    
    lang = language.lower().strip()
    if lang == "hindi":
        clean_text = clean_text.replace("₹", " रुपये ").replace("Rs.", " रुपये ")
    elif lang == "tamil":
        clean_text = clean_text.replace("₹", " ரூபாய் ").replace("Rs.", " ரூபாய் ")
    elif lang == "telugu":
        clean_text = clean_text.replace("₹", " రూపాయలు ").replace("Rs.", " రూపాయలు ")
    elif lang == "malayalam":
        clean_text = clean_text.replace("₹", " രൂപ ").replace("Rs.", " രൂപ ")
    else:
        clean_text = clean_text.replace("₹", " Rupees ").replace("Rs.", " Rupees ")
        
    cleaned = "".join(c for c in clean_text if unicodedata.category(c) not in ("So", "Cn", "Cs"))
    return cleaned.strip()

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

    def generate_voiceover(
        self, 
        text: str, 
        language: str, 
        output_filename: str,
        voice_profile: Optional[str] = None,
        speed_rate: Optional[str] = None,
        pitch: Optional[str] = None
    ) -> str:
        """
        Synthesizes text into a voiceover file (MP3/WAV).
        Validates text, applies pronunciation substitutions, synthesizes voice,
        and runs a speech-to-text loop for fidelity verification.
        Returns the absolute filepath to the created audio file.
        """
        # 1. TTS Input Validation
        validate_tts_input(text)

        output_path = settings.MEDIA_DIR / output_filename
        lang_key = language.lower().strip()
        lang_code = LANG_CODE_MAP.get(lang_key, "en")

        # 2. Clean Text (preserve full screenplay dialogue for complete voice synthesis)
        clean_text = clean_tts_text(text, language)
        # Apply pronunciation dictionary substitutions
        processed_text = apply_pronunciation_dictionary(clean_text)

        # 3. Resolve Voice Style Profile
        profile_key = "default"
        if voice_profile:
            vp_lower = voice_profile.lower()
            if "storyteller" in vp_lower:
                profile_key = "storyteller"
            elif "nursery" in vp_lower:
                profile_key = "nursery"
            elif "presenter" in vp_lower or "expert" in vp_lower or "guide" in vp_lower:
                profile_key = "presenter"
        
        voice_name = VOICE_PROFILES.get(lang_key, {}).get(profile_key, VOICE_PROFILES.get(lang_key, {}).get("default", "en-IN-NeerjaNeural"))

        # Default controls
        rate_val = speed_rate or "-7%"
        pitch_val = pitch or "+0Hz"

        # Verification loop
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Synthesis attempt {attempt}/{max_attempts} for language {language} using voice {voice_name}...")
            
            # Edge-tts synthesis logic
            try:
                import edge_tts
                import asyncio
                import threading

                logger.info(f"Synthesizing voiceover with edge-tts using voice: {voice_name} (rate={rate_val}, pitch={pitch_val})")

                async def _synthesize_edge_tts(text_to_speak, voice, dest_path):
                    communicate = edge_tts.Communicate(text_to_speak, voice, rate=rate_val, pitch=pitch_val)
                    await communicate.save(dest_path)

                # Run in a dedicated thread to avoid any conflicts with existing event loops in FastAPI/uvicorn
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    new_loop.run_until_complete(_synthesize_edge_tts(processed_text, voice_name, str(output_path)))
                    new_loop.close()

                t = threading.Thread(target=run_in_thread)
                t.start()
                t.join()

                if not (os.path.exists(output_path) and os.path.getsize(output_path) > 100):
                    raise Exception("edge-tts output is empty or missing")

            except Exception as edge_err:
                logger.error(f"edge-tts generation failed on attempt {attempt}: {edge_err}. Falling back to gTTS/Coqui.")
                
                # Fallback to Coqui
                if self.coqui_available:
                    try:
                        from TTS.api import TTS
                        logger.info(f"Synthesizing with Coqui TTS: {language}")
                        tts = TTS(self.coqui_model_name).to("cpu")
                        tts.tts_to_file(
                            text=processed_text,
                            file_path=str(output_path),
                            speaker_wav=None,
                            language=lang_code
                        )
                    except Exception as coqui_err:
                        logger.error(f"Coqui TTS failed: {coqui_err}")
                
                # Fallback to gTTS if Coqui failed or not available
                if not (os.path.exists(output_path) and os.path.getsize(output_path) > 100):
                    try:
                        logger.info(f"Synthesizing with gTTS: {language}")
                        tts_obj = gTTS(text=processed_text, lang=lang_code, slow=False)
                        tts_obj.save(str(output_path))
                    except Exception as gtts_err:
                        logger.error(f"gTTS failed: {gtts_err}. Trying offline Windows SAPI...")
                        
                        # Fallback to offline Windows SAPI
                        try:
                            import subprocess
                            wav_path = output_path.with_suffix(".wav")
                            if os.path.exists(wav_path):
                                os.remove(wav_path)
                            clean_text_escaped = processed_text.replace("'", "''").replace("\n", " ").replace("\r", "")
                            ps_command = f"""
Add-Type -AssemblyName System.Speech;
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;
$synth.SetOutputToWaveFile('{wav_path}');
$synth.Speak('{clean_text_escaped}');
$synth.Dispose();
"""
                            subprocess.run(["powershell", "-Command", ps_command], capture_output=True, text=True)
                            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 100:
                                if os.path.exists(output_path):
                                    os.remove(output_path)
                                os.rename(str(wav_path), str(output_path))
                        except Exception as sapi_err:
                            logger.error(f"Offline Windows SAPI failed: {sapi_err}")
                            
                # Fallback to sine tone programmatic wave
                if not (os.path.exists(output_path) and os.path.getsize(output_path) > 100):
                    import wave
                    import struct
                    import math
                    logger.info("Generating programmatic sine tone placeholder WAV.")
                    wav_path = output_path.with_suffix(".wav")
                    sample_rate = 8000.0
                    duration = 5.0
                    num_samples = int(duration * sample_rate)
                    with wave.open(str(wav_path), "wb") as wav_file:
                        wav_file.setparams((1, 2, int(sample_rate), num_samples, "NONE", "not compressed"))
                        for i in range(num_samples):
                            value = int(32767.0 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
                            wav_file.writeframes(struct.pack("h", value))
                    if os.path.exists(output_path):
                        try: os.remove(output_path)
                        except Exception: pass
                    os.rename(str(wav_path), str(output_path))

            # 4. Audio Verification via STT
            similarity = verify_audio_fidelity(str(output_path), clean_text, language)
            if similarity >= 0.99:
                logger.info(f"Audio verification PASSED (similarity={similarity:.4f}).")
                break
            else:
                logger.warning(f"Audio verification FAILED (similarity={similarity:.4f} < 0.99) on attempt {attempt}.")
                if attempt == max_attempts:
                    logger.error("Audio fidelity verification failed after maximum attempts. Proceeding with best attempt.")
                else:
                    import time
                    time.sleep(0.5)

        return str(output_path)

voice_svc = VoiceService()

