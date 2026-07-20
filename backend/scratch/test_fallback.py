# scratch/test_fallback.py
import sys, os, glob
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.config import settings

def get_fallback_video_url(language: str) -> str:
    media_dir = settings.MEDIA_DIR
    lang_pattern = f"video_{language.lower()}*.mp4"
    files = [f for f in glob.glob(str(media_dir / lang_pattern)) if os.path.getsize(f) > 1000 and not os.path.basename(f).startswith("temp_")]
    if files:
        files.sort(key=os.path.getmtime, reverse=True)
        return f"/static/media/{os.path.basename(files[0])}"
    
    # Try any valid mp4 file
    all_files = [f for f in glob.glob(str(media_dir / "*.mp4")) if os.path.getsize(f) > 1000 and not os.path.basename(f).startswith("temp_")]
    if all_files:
        all_files.sort(key=os.path.getmtime, reverse=True)
        return f"/static/media/{os.path.basename(all_files[0])}"
        
    return "/static/media/default_campaign_video.mp4"

print("English fallback:", get_fallback_video_url("English"))
print("Hindi fallback:", get_fallback_video_url("Hindi"))
print("Tamil fallback:", get_fallback_video_url("Tamil"))
print("Telugu fallback:", get_fallback_video_url("Telugu"))
print("Malayalam fallback:", get_fallback_video_url("Malayalam"))
