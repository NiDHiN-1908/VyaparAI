# backend/main.py
import os
from pathlib import Path
# Set working directory to project root to allow writing temporary files
project_root = Path(__file__).resolve().parent.parent
os.chdir(project_root)

import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.routers import business, marketing, lead, sales, analytics, youtube_auth, youtube_monitor, whatsapp
from backend.services.youtube_monitor_service import youtube_monitor_svc

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("vyaparai.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount media static directory to serve generated MP3s and MP4s
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Register modular routers
app.include_router(business.router)
app.include_router(marketing.router)
app.include_router(lead.router)
app.include_router(sales.router)
app.include_router(analytics.router)
app.include_router(youtube_auth.router)
app.include_router(youtube_monitor.router)
app.include_router(whatsapp.router)

# Background Polling Service Startup
@app.on_event("startup")
async def start_youtube_monitor():
    youtube_monitor_svc.start()
    
    # Seed default mock data if running in mock mode and DB is empty
    from backend.services.supabase_service import supabase_svc
    if supabase_svc.is_mock:
        businesses = supabase_svc.get_businesses()
        if not businesses:
            biz = supabase_svc.create_business(
                name="Kochi Spice Farm",
                location="Kochi, Kerala",
                contact="+91 7306796590",
                industry="Agriculture"
            )
            # Create a default cardamom product
            prod = supabase_svc.create_product(
                business_id=biz["id"],
                name="Organic Cardamom",
                description="Premium 8mm bold green cardamom pods, direct from Munnar hills.",
                price=350.00,
                images=["/static/media/prod_eb2705d428d74da489cdff6685567b1a.png"]
            )
            
            # Seed script
            script = supabase_svc.create_script(
                product_id=prod["id"],
                title="Festive Spice Campaign",
                hook="Is your tea missing that authentic kerala aroma? ☕",
                script_text="Are you looking for the best organic green elaichi? Introducing our premium Kochi Spice Farm cardamom. Sourced directly from local farms in Idukki. It is high quality, chemical free, and vacuum sealed. Order yours today!",
                scene_breakdown=[
                    {"scene": 1, "instruction": "Show organic cardamom pods", "voiceover": "Are you looking for the best organic green elaichi?"}
                ],
                caption_timeline=[
                    {"start": 0.0, "end": 5.0, "text": "Are you looking for the best organic green elaichi?"}
                ],
                thumbnail_text="Pure Elaichi!",
                seo_description="Buy premium quality organic cardamom online with nationwide shipping.",
                hashtags=["Cardamom", "LocalSpices", "KochiFarm"],
                version=1
            )
            
            # Seed thumbnail
            supabase_svc.create_thumbnail(
                script_id=script["id"],
                layout="Product centered with bold yellow text overlay",
                text="Pure Elaichi!",
                prompt="Cardamom pods overflowing from a clay bowl, dark rustic background"
            )
            
            # Seed translation, voiceover, and video for multiple languages
            lang_files = {
                "English": {
                    "audio": "voiceover_english_v2_cf375002.mp3", "audio_len": 11.59,
                    "video": "video_english_v2_3ce14206.mp4",
                    "text": "Are you looking for the best organic green elaichi? Sourced directly from local farms. It is high quality, chemical free, and vacuum sealed. Order yours today!"
                },
                "Hindi": {
                    "audio": "voiceover_hindi_v2_0e98b3b2.mp3", "audio_len": 20.23,
                    "video": "video_hindi_v2_63b2d922.mp4",
                    "text": "क्या आपकी चाय में केरल की असली खुशबू गायब है? हमारी प्रीमियम इलायची सीधे इडुक्की के खेतों से लाई गई है।"
                },
                "Tamil": {
                    "audio": "voiceover_tamil_v2_edede122.mp3", "audio_len": 19.32,
                    "video": "video_tamil_v2_12efcce8.mp4",
                    "text": "உங்கள் தேநீரில் கேரளா ஏலக்காயின் நறுமணம் இல்லையா? எங்களது ஏலக்காய் இடுக்கியில் அறுவடை செய்யப்படுகிறது."
                },
                "Telugu": {
                    "audio": "voiceover_telugu_v2_a8476c99.mp3", "audio_len": 18.86,
                    "video": "video_telugu_v2_6a2efde3.mp4",
                    "text": "మీ టీలో కేరళ యాలకుల సువాసన లోపించిందా? మా ఆర్గానిక్ యాలకులు కొండల నుండి సేకరించబడ్డాయి."
                },
                "Malayalam": {
                    "audio": "voiceover_malayalam_v2_56a549d6.mp3", "audio_len": 14.50,
                    "video": "video_malayalam_v2_b9304c03.mp4",
                    "text": "നിങ്ങളുടെ ചായയിൽ യഥാർത്ഥ കേരള ഏലക്കായുടെ മണം കുറവാണോ? ഇടുക്കിയിലെ തോട്ടങ്ങളിൽ നിന്ന് നേരിട്ട് ശേഖരിച്ച ഏലക്കായ."
                }
            }
            
            for lang, assets in lang_files.items():
                trans = supabase_svc.create_translation(
                    script_id=script["id"],
                    language=lang,
                    youtube=assets["text"],
                    reel=assets["text"],
                    whatsapp=assets["text"],
                    google=assets["text"]
                )
                voice = supabase_svc.create_voiceover(
                    translation_id=trans["id"],
                    audio_url=f"/static/media/{assets['audio']}",
                    duration=assets["audio_len"]
                )
                supabase_svc.create_video(
                    voiceover_id=voice["id"],
                    video_url=f"/static/media/{assets['video']}",
                    status="ready",
                    approval_status="pending",
                    version=1
                )
            
            logger.info(f"Seeded mock database on startup with product: {prod['name']}")

@app.on_event("shutdown")
async def stop_youtube_monitor():
    youtube_monitor_svc.stop()


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "An unexpected error occurred on the server.", "details": str(exc)}
    )

@app.get("/")
async def root_health_check():
    """Health check endpoint confirming API status and active database/agent configurations."""
    from backend.database.connection import db_conn
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "database_mode": "Mock (In-Memory)" if db_conn.is_mock else "Supabase Real-Time Connected",
        "ollama_host": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
