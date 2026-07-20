# scratch/cleanup_corrupted.py
import os
import glob
from pathlib import Path

media_dir = Path("backend/static/media")
files = glob.glob(str(media_dir / "*"))
removed = []

for f in files:
    if os.path.isfile(f) and f.endswith((".mp4", ".mp3")):
        size = os.path.getsize(f)
        if size < 1000:
            os.remove(f)
            removed.append((f, size))

print(f"Removed {len(removed)} corrupted files under 1000 bytes.")
for f, size in removed:
    print(f"  Deleted: {os.path.basename(f)} ({size} bytes)")
