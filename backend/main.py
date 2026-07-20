# backend/main.py
import time
start_all_time = time.time()

# 1. Environment Loading
start_env = time.time()
import os
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
os.chdir(project_root)

import socket
socket.setdefaulttimeout(10.0)

import pydantic
pydantic.BaseModel.model_config["protected_namespaces"] = ()

from dotenv import load_dotenv
load_dotenv()

from backend.config import settings
env_loading_duration = time.time() - start_env

# 2. Dependency Initialization
start_deps = time.time()
import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.routers import business, marketing, lead, sales, analytics, youtube_auth, whatsapp, health
from backend.modules.video_monitoring_module import video_monitoring_router, video_monitoring_svc

# Clean Architecture WhatsApp Module imports
from backend.modules.websocket_module import websocket_router
from backend.modules.whatsapp_module import whatsapp_router
from backend.modules.conversation_module import conversation_router
from backend.modules.messaging_module import messaging_router
from backend.modules.payment_module import payment_router
deps_initialization_duration = time.time() - start_deps

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("vyaparai.main")

# Register metrics in StartupManager
from backend.services.startup_manager import startup_mgr
startup_mgr.set_metric("environment_loading", env_loading_duration, True)
startup_mgr.set_metric("dependency_initialization", deps_initialization_duration, True)

# Register Database Connection wrapper time
from backend.database.connection import db_conn_duration
startup_mgr.set_metric("database_connection", db_conn_duration, True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Explicitly initialize and register correct MIME types to prevent Windows Registry issues where .mp4 is served as application/octet-stream
import mimetypes
mimetypes.init()
mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("audio/mp4", ".m4a")

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount media static directory to serve generated MP3s and MP4s wrapped in CORSMiddleware to prevent browser CORS issues
static_app = StaticFiles(directory=settings.STATIC_DIR)
cors_static_app = CORSMiddleware(
    app=static_app,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", cors_static_app, name="static")

@app.middleware("http")
async def log_request_lifecycle(request: Request, call_next):
    host = request.headers.get("host", "")
    is_tunnel = any(dom in host for dom in ["lhr.life", "lhr.rocks", "lhr.run", "ngrok-free.dev", "ngrok-free.app", "trycloudflare.com"])
    prefix = "[PUBLIC TUNNEL REQUEST]" if is_tunnel else "[LOCAL REQUEST]"
    start_time = time.time()
    logger.info(f"{prefix} Received: {request.method} {request.url.path} from client {request.client.host if request.client else 'unknown'} (Host: {host}, X-Forwarded-For: {request.headers.get('x-forwarded-for', 'none')})")
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(f"{prefix} Completed: {request.method} {request.url.path} - Status: {response.status_code} (Duration: {duration:.4f}s)")
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"{prefix} Failed: {request.method} {request.url.path} - Error: {e} (Duration: {duration:.4f}s)", exc_info=True)
        raise e


# Register modular routers
app.include_router(business.router)
app.include_router(marketing.router)
app.include_router(lead.router)
app.include_router(sales.router)
app.include_router(analytics.router)
app.include_router(youtube_auth.router)
app.include_router(video_monitoring_router)
app.include_router(whatsapp.router)
app.include_router(health.router)

# Mount Clean Architecture WhatsApp Modules
app.include_router(websocket_router)
app.include_router(whatsapp_router)
app.include_router(conversation_router)
app.include_router(messaging_router)
app.include_router(payment_router)

# Background Polling Service Startup
@app.on_event("startup")
async def start_youtube_monitor():
    startup_mgr.start_metric("api_server_startup")
    startup_mgr.start_metric("background_workers")
    
    video_monitoring_svc.start()
    
    startup_mgr.stop_metric("background_workers", True)
    startup_mgr.stop_metric("api_server_startup", True)
    
    # Start checkingSupabase/Ollama/WhatsApp/Tunnel concurrently in the background
    startup_mgr.start_background_initialization()
    
    # Start the tunnel self-healing monitoring loop in the background
    from backend.services.tunnel_manager import tunnel_mgr
    tunnel_mgr.start_monitoring_loop()
    
@app.on_event("shutdown")
async def shutdown_services():
    from backend.services.tunnel_manager import tunnel_mgr
    tunnel_mgr.shutdown()
    
    # Seed default mock data if running in mock mode and DB is empty
    from backend.services.supabase_service import supabase_svc
    if supabase_svc.is_mock:
        businesses = supabase_svc.get_businesses()
        if not businesses:
            biz = supabase_svc.create_business(
                name="Green Haven Nursery",
                location="Kottayam, Kerala",
                contact="+91 9744506034",
                industry="Nursery & Gardening"
            )
            # Create a default Fiddle Leaf Fig product
            prod = supabase_svc.create_product(
                business_id=biz["id"],
                name="Fiddle Leaf Fig",
                description="Stunning air-purifying indoor plant with large, glossy fiddle-shaped leaves. Perfect for home decor.",
                price=499.00,
                images=["/static/media/prod_eb2705d428d74da489cdff6685567b1a.png"]
            )
            
            # Seed script
            script = supabase_svc.create_script(
                product_id=prod["id"],
                title="Nursery Greenery Launch Campaign",
                hook="Are your house plants constantly dying? \ud83c\udf3f",
                script_text="Are you looking for low-maintenance house plants? Introducing our premium Fiddle Leaf Fig. Sourced directly from Green Haven Nursery in Kottayam. It is grown in nutrient-rich soil and shipped with a plant care guide. Order yours today!",
                scene_breakdown=[
                    {"scene": 1, "instruction": "Show stunning fiddle leaf fig plants", "voiceover": "Are you looking for low-maintenance house plants?"}
                ],
                caption_timeline=[
                    {"start": 0.0, "end": 5.0, "text": "Are you looking for low-maintenance house plants?"}
                ],
                thumbnail_text="Beautiful Fiddle Leaf Fig!",
                seo_description="Buy premium quality indoor plants online with care guides and free delivery.",
                hashtags=["FiddleLeafFig", "NurseryPlants", "GreenHaven"],
                version=1
            )
            
            # Seed thumbnail
            supabase_svc.create_thumbnail(
                script_id=script["id"],
                layout="Product centered with bold yellow text overlay",
                text="Beautiful Fiddle Leaf Fig!",
                prompt="Fiddle leaf fig plant in a modern white ceramic pot, sunlit minimal room background"
            )
            
            # Seed translation, voiceover, and video for multiple languages
            lang_files = {
                "English": {
                    "audio": "voiceover_english_v2_cf375002.mp3", "audio_len": 11.59,
                    "video": "video_english_v2_3ce14206.mp4",
                    "text": "Are you looking for low-maintenance house plants? Sourced directly from our organic nursery. It is high quality, healthy, and shipped with care. Order yours today!"
                },
                "Hindi": {
                    "audio": "voiceover_hindi_v2_0e98b3b2.mp3", "audio_len": 20.23,
                    "video": "video_hindi_v2_63b2d922.mp4",
                    "text": "क्या आपके घर के पौधे बार-बार सूख जाते हैं? हमारी प्रीमियम फिडेल लीफ फिग सीधे नर्सरी से मंगवाएं।"
                },
                "Tamil": {
                    "audio": "voiceover_tamil_v2_edede122.mp3", "audio_len": 19.32,
                    "video": "video_tamil_v2_12efcce8.mp4",
                    "text": "உங்கள் வீட்டு செடிகள் அடிக்கடி காய்ந்து விடுகிறதா? எங்கள் பசுமையான ஃபிடில் லீஃப் பிக் செடியை ஆர்டர் செய்யுங்கள்."
                },
                "Telugu": {
                    "audio": "voiceover_telugu_v2_a8476c99.mp3", "audio_len": 18.86,
                    "video": "video_telugu_v2_6a2efde3.mp4",
                    "text": "మీ ఇంట్లోని మొక్కలు తరచుగా చనిపోతున్నాయా? మా ప్రీమియం ఫిడిల్ లీఫ్ ఫిగ్ మొక్కను ఆర్డర్ చేయండి."
                },
                "Malayalam": {
                    "audio": "voiceover_malayalam_v2_56a549d6.mp3", "audio_len": 14.50,
                    "video": "video_malayalam_v2_b9304c03.mp4",
                    "text": "നിങ്ങളുടെ വീട്ടിലെ ചെടികൾ പെട്ടെന്ന് ഉണങ്ങിപ്പോകാറുണ്ടോ? ഞങ്ങളുടെ ഫിഡിൽ ലീഫ് ഫിഗ് ചെടി ഇപ്പോൾ തന്നെ ഓർഡർ ചെയ്യൂ."
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
    from backend.modules.whatsapp_module.instance_service import whatsapp_instance_svc
    
    provider = whatsapp_instance_svc.provider
    is_sandbox = getattr(provider, "is_sandbox", None)
    api_url = getattr(provider, "api_url", None)
    api_key = getattr(provider, "api_key", None)
    
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "database_mode": "Mock (In-Memory)" if db_conn.is_mock else "Supabase Real-Time Connected",
        "ollama_host": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "whatsapp": {
            "provider_name": whatsapp_instance_svc.provider_name,
            "is_sandbox": is_sandbox,
            "api_url": api_url,
            "api_key_set": bool(api_key),
            "api_key_masked": (api_key[:4] + "..." if api_key else None)
        }
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)

# Restored clean main.py reloader after merchant name dynamic lookup
# Trigger auto-reload for PUBLIC_URL env update - ngrok prioritized

