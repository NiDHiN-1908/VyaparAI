# backend/services/youtube_auth_helper.py
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from backend.services.supabase_service import supabase_svc

logger = logging.getLogger("vyaparai.services.youtube_auth_helper")

def get_credentials(channel: dict) -> Credentials:
    """
    Constructs a Credentials object from the channel dictionary stored in the DB.
    """
    return Credentials(
        token=channel["access_token"],
        refresh_token=channel.get("refresh_token"),
        token_uri=channel.get("token_uri") or "https://oauth2.googleapis.com/token",
        client_id=channel.get("client_id"),
        client_secret=channel.get("client_secret"),
        scopes=channel.get("scopes") or ["https://www.googleapis.com/auth/youtube.force-ssl"]
    )

def refresh_credentials(channel: dict, creds: Credentials) -> Credentials:
    """
    Refreshes the credentials, updates the database, and returns the refreshed credentials.
    """
    logger.info(f"Refreshing access token for channel {channel.get('channel_name', channel['channel_id'])}...")
    if not creds.refresh_token:
        raise ValueError("No refresh token available to refresh credentials.")
        
    try:
        creds.refresh(Request())
        # Update the channel in database
        supabase_svc.create_youtube_channel(
            channel_id=channel["channel_id"],
            channel_name=channel["channel_name"],
            thumbnail=channel.get("thumbnail"),
            subscriber_count=channel.get("subscriber_count", 0),
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            token_uri=channel.get("token_uri"),
            client_id=channel.get("client_id"),
            client_secret=channel.get("client_secret"),
            scopes=channel.get("scopes")
        )
        logger.info("Credentials successfully refreshed and updated in database.")
        return creds
    except Exception as e:
        logger.error(f"Failed to refresh credentials: {e}", exc_info=True)
        raise e

def execute_youtube_call(channel: dict, call_func):
    """
    Executes a YouTube API call. If a 401 Unauthorized or auth-related exception is caught,
    it refreshes the credentials and retries the call once.
    
    call_func: A callable that accepts the built 'youtube' service client and returns a request.
    Example: execute_youtube_call(channel, lambda yt: yt.comments().insert(...))
    """
    creds = get_credentials(channel)
    try:
        youtube = build("youtube", "v3", credentials=creds)
        request = call_func(youtube)
        return request.execute()
    except Exception as e:
        import googleapiclient.errors
        # Check if it's an authorization/expired token error (typically 401)
        is_auth_error = False
        if isinstance(e, googleapiclient.errors.HttpError) and e.resp.status == 401:
            is_auth_error = True
        elif "invalid_grant" in str(e) or "expired" in str(e).lower() or "unauthorized" in str(e).lower() or "token has been expired" in str(e).lower():
            is_auth_error = True
            
        if is_auth_error and creds.refresh_token:
            logger.info("Detected authorization error. Attempting to refresh token and retry...")
            try:
                creds = refresh_credentials(channel, creds)
                # Re-build client
                youtube = build("youtube", "v3", credentials=creds)
                request = call_func(youtube)
                return request.execute()
            except Exception as retry_err:
                logger.error(f"Failed YouTube API call after refreshing credentials: {retry_err}")
                raise retry_err
        else:
            raise e
