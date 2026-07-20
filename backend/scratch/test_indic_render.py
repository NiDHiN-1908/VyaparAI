# scratch/test_indic_render.py
import sys, os
from PIL import Image, ImageDraw, ImageFont

font_path = "C:\\Windows\\Fonts\\Nirmala.ttc"
font = ImageFont.truetype(font_path, 44, index=0)
brand_font = ImageFont.truetype(font_path, 28, index=0)

texts = {
    "Hindi": "क्या आपके घर के पौधे बार-बार सूख जाते हैं?",
    "Tamil": "உங்கள் வீட்டு செடிகள் அடிக்கடி காய்ந்து விடுகிறதா?",
    "Telugu": "మీ ఇంట్లోని మొక్కలు తరచుగా ఎండిపోతున్నాయా?",
    "Malayalam": "നിങ്ങളുടെ വീട്ടിലെ ചെടികൾ പെട്ടെന്ന് ഉണങ്ങിപ്പോകാറുണ്ടോ?"
}

out_dir = "backend/static/media"
for lang, text in texts.items():
    img = Image.new("RGBA", (1080, 1920), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    
    # Glass panel
    draw.rounded_rectangle([80, 1350, 1000, 1680], radius=30, fill=(15, 23, 42, 220), outline=(99, 102, 241, 255), width=3)
    draw.text((540, 1420), text, fill=(248, 250, 252, 255), anchor="ma", font=font)
    
    fn = os.path.join(out_dir, f"test_indic_{lang.lower()}.png")
    img.convert("RGB").save(fn)
    print(f"Saved {lang} test image to {fn}")
