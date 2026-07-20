# backend/routers/youtube_auth.py
import os
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from backend.services.supabase_service import supabase_svc
from backend.config import settings

logger = logging.getLogger("vyaparai.routers.youtube_auth")
router = APIRouter(prefix="/auth/youtube", tags=["YouTube Channel Authentication"])

FRONTEND_REDIRECT_URL = "http://localhost:3000/youtube-connect"

@router.get("/login")
async def youtube_login(request: Request):
    """
    Initiates Google OAuth2 web authorization flow.
    If no client_secrets.json is present, it returns an error or redirects to simulated callback.
    """
    client_secrets_path = "client_secrets.json"
    
    if not os.path.exists(client_secrets_path):
        logger.warning("client_secrets.json not found. Redirecting to simulated callback.")
        # Fallback redirect to mock success callback
        return RedirectResponse(url=f"{FRONTEND_REDIRECT_URL}?status=success&mock=true")
        
    try:
        from google_auth_oauthlib.flow import Flow
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        scopes = [
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl"
        ]
        
        flow = Flow.from_client_secrets_file(
            client_secrets_path,
            scopes=scopes,
            redirect_uri="http://localhost:8000/auth/youtube/callback"
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Retrieve automatic code verifier
        code_verifier = getattr(flow, "code_verifier", None)
        if code_verifier:
            # Package state and code_verifier together
            combined_state = f"{state}___{code_verifier}"
            parsed = urlparse(authorization_url)
            query = parse_qs(parsed.query)
            query['state'] = [combined_state]
            parsed = parsed._replace(query=urlencode(query, doseq=True))
            authorization_url = urlunparse(parsed)
            logger.info(f"Packed PKCE code_verifier into OAuth state parameter: {state}")
        
        return RedirectResponse(url=authorization_url)
    except Exception as e:
        logger.error(f"Google OAuth flow initiation failed: {e}")
        return RedirectResponse(url=f"{FRONTEND_REDIRECT_URL}?status=error&error={str(e)}")

@router.get("/callback")
async def youtube_callback(code: str = None, state: str = None, error: str = None):
    """Handles Google OAuth authorization callback redirect"""
    if error:
        logger.error(f"OAuth callback returned error: {error}")
        return RedirectResponse(url=f"{FRONTEND_REDIRECT_URL}?status=error&error={error}")
        
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing.")

    client_secrets_path = "client_secrets.json"
    try:
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build
        
        scopes = [
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl"
        ]
        
        flow = Flow.from_client_secrets_file(
            client_secrets_path,
            scopes=scopes,
            redirect_uri="http://localhost:8000/auth/youtube/callback" # Must match Google Developer Console redirect
        )
        
        # Extract code_verifier if packed in state
        code_verifier = None
        if state and "___" in state:
            parts = state.split("___")
            code_verifier = parts[1]
            logger.info("Extracted PKCE code_verifier from incoming callback state")
            
        flow.fetch_token(code=code, code_verifier=code_verifier)
        credentials = flow.credentials
        
        # Call YouTube API to retrieve connected channel statistics
        youtube = build("youtube", "v3", credentials=credentials)
        request = youtube.channels().list(
            part="snippet,statistics",
            mine=True
        )
        response = request.execute()
        
        if not response.get("items"):
            raise ValueError("No YouTube channels found for the authenticated Google account.")
            
        channel_info = response["items"][0]
        channel_id = channel_info["id"]
        channel_name = channel_info["snippet"]["title"]
        thumbnail = channel_info["snippet"]["thumbnails"]["default"]["url"]
        sub_count = int(channel_info["statistics"].get("subscriberCount", 0))
        
        # Save credentials in Supabase
        supabase_svc.create_youtube_channel(
            channel_id=channel_id,
            channel_name=channel_name,
            thumbnail=thumbnail,
            subscriber_count=sub_count,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=credentials.scopes
        )
        
        # Initialize default analytics for the channel
        supabase_svc.create_youtube_analytics(channel_id=channel_id)
        
        # Trigger background task to sync videos and comments immediately
        import asyncio
        from backend.modules.video_monitoring_module import video_monitoring_svc as youtube_monitor_svc
        asyncio.create_task(youtube_monitor_svc.poll_comments_for_all_channels())
        
        logger.info(f"Successfully linked YouTube channel: {channel_name} ({channel_id})")
        return RedirectResponse(url=f"{FRONTEND_REDIRECT_URL}?status=success")
        
    except Exception as e:
        logger.error(f"Error handling Google OAuth callback: {e}")
        return RedirectResponse(url=f"{FRONTEND_REDIRECT_URL}?status=error&error={str(e)}")

@router.post("/mock-connect")
async def mock_youtube_connect():
    """Endpoint to trigger sandbox channel connection with 1-click on UI"""
    logger.info("Connecting mock YouTube channel for sandbox testing")
    try:
        mock_id = "UC_MOCK_VYAPAR_AI"
        mock_name = "VyaparAI Green Haven Nursery"
        mock_thumb = "https://images.unsplash.com/photo-1542838132-92c53300491e?w=100&auto=format&fit=crop&q=60"
        
        channel = supabase_svc.create_youtube_channel(
            channel_id=mock_id,
            channel_name=mock_name,
            thumbnail=mock_thumb,
            subscriber_count=2480,
            access_token="mock_access_token",
            refresh_token="mock_refresh_token"
        )
        
        # Seed mock videos
        supabase_svc.create_youtube_video(
            channel_id=mock_id,
            video_id="PuCb1JHpBkM",
            title="Nursery Greenery Launch Campaign",
            publish_date=datetime.now().isoformat(),
            status="monitored"
        )
        
        # Create default analytics rows
        supabase_svc.create_youtube_analytics(channel_id=mock_id)
        
        return {"status": "success", "data": channel}
    except Exception as e:
        logger.error(f"Failed to create mock channel connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_youtube_status():
    """Check connection status and return details"""
    error_msg = None
    try:
        from backend.modules.video_monitoring_module import video_monitoring_svc as youtube_monitor_svc
        error_msg = getattr(youtube_monitor_svc, "last_sync_error", None)
        logger.info(f"[/status] youtube_monitor_svc.last_sync_error is: {error_msg} (id: {id(youtube_monitor_svc)})")
        
        channels = supabase_svc.get_youtube_channels()
        if channels:
            # Prioritize returning a real channel if one exists alongside the mock channel
            active_chan = next((c for c in channels if c.get("access_token") != "mock_access_token"), channels[0])
            return {"connected": True, "channel": active_chan, "temp_error": error_msg}
    except Exception as e:
        import traceback
        error_msg = f"{e}\n{traceback.format_exc()}"
        logger.error(f"Status check failed: {error_msg}")
        
    return {"connected": False, "channel": None, "temp_error": error_msg}



@router.post("/disconnect")
async def youtube_disconnect():
    """Disconnect active channel and reset settings"""
    channels = supabase_svc.get_youtube_channels()
    if not channels:
        return {"status": "success", "message": "No channel was connected."}
        
    for channel in channels:
        supabase_svc.delete_youtube_channel(channel["channel_id"])
        
    logger.info("Disconnected YouTube channel successfully.")
    return {"status": "success", "message": "Channel disconnected successfully."}
