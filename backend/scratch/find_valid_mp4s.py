# scratch/find_valid_mp4s.py
import os
import glob
from pathlib import Path

media_dir = Path("backend/static/media")
files = glob.glob(str(media_dir / "*.mp4"))
valid_mp4s = []

for f in files:
    size = os.path.getsize(f)
    if size > 1000:
        valid_mp4s.append((os.path.basename(f), size))

print(f"Total valid MP4 files: {len(valid_mp4s)}")
for name, size in valid_mp4s[:10]:
    print(f"  {name}: {size / (1024*1024):.2f} MB")
