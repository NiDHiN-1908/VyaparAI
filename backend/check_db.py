import os
import json

mock_db_path = os.path.expanduser("~/.vyapar_mock_db.json")
old_mock_db_path = "backend/database/mock_db.json"

print("CWD:", os.getcwd())
print("Mock db path exists:", os.path.exists(mock_db_path))
if os.path.exists(mock_db_path):
    with open(mock_db_path, "r", encoding="utf-8") as f:
        db = json.load(f)
        print("Number of products:", len(db.get("products", [])))
        for p in db.get("products", []):
            print(f"Product: {p.get('name')} (ID: {p.get('id')})")
        print("\nNumber of videos in mock DB:", len(db.get("videos", [])))
        for v in db.get("videos", []):
            print(f"Video ID {v.get('id')}: voiceover_id={v.get('voiceover_id')}, url={v.get('video_url')}, status={v.get('status')}")
        print("\nNumber of voiceovers in mock DB:", len(db.get("voiceovers", [])))
        for v in db.get("voiceovers", []):
            print(f"Voiceover ID {v.get('id')}: translation_id={v.get('translation_id')}, audio_url={v.get('audio_url')}")
        print("\nNumber of translations in mock DB:", len(db.get("translations", [])))
        for t in db.get("translations", []):
            print(f"Translation ID {t.get('id')}: product_id={t.get('product_id')}, lang={t.get('language')}")
else:
    print("No mock db found at", mock_db_path)
