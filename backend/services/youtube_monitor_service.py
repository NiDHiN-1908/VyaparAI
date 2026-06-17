# backend/services/youtube_monitor_service.py
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List
from googleapiclient.discovery import build

from backend.services.supabase_service import supabase_svc
from backend.crews.youtube_monitor_crew import youtube_monitor_crew

logger = logging.getLogger("vyaparai.services.youtube_monitor_service")

# List of demo comments for sandbox simulation mode
MOCK_INCOMING_COMMENTS = [
    {"username": "arun_raj", "text": "What is the price of coconut oil? Do you deliver to Bangalore?", "timestamp": "2026-06-12T11:00:00Z"},
    {"username": "hema_bhat", "text": "How can I order? Please share contact number.", "timestamp": "2026-06-12T11:05:00Z"},
    {"username": "rahul_k", "text": "Is this product chemical free?", "timestamp": "2026-06-12T11:10:00Z"},
    {"username": "crypto_guy", "text": "Click here to win a free iphone! www.spambot.com", "timestamp": "2026-06-12T11:15:00Z"},
    {"username": "meera_nair", "text": "Super quality, highly recommended! ❤️", "timestamp": "2026-06-12T11:20:00Z"},
    {"username": "vicky_sharma", "text": "Do you offer cash on delivery?", "timestamp": "2026-06-12T11:25:00Z"},
]

class YouTubeMonitorService:
    def __init__(self):
        self.is_running = False
        self.task = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self.monitor_loop())
            logger.info("YouTube Comment Monitoring Service started successfully.")

    def stop(self):
        if self.is_running:
            self.is_running = False
            if self.task:
                self.task.cancel()
            logger.info("YouTube Comment Monitoring Service stopped.")

    async def monitor_loop(self):
        while self.is_running:
            try:
                logger.info("Running scheduled YouTube comment monitoring cycle...")
                await self.poll_comments_for_all_channels()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor cycle: {e}", exc_info=True)
            
            # Sleep for 5 minutes (300 seconds)
            await asyncio.sleep(300)

    async def poll_comments_for_all_channels(self):
        channels = supabase_svc.get_youtube_channels()
        if not channels:
            logger.info("No connected YouTube channels found. Skipping comment monitor cycle.")
            return

        for channel in channels:
            channel_id = channel["channel_id"]
            # Sync channel videos first to ensure we monitor all uploads
            await self.sync_channel_videos(channel)
            # Fetch videos
            videos = [v for v in supabase_svc.get_youtube_videos() if v["channel_id"] == channel_id]
            
            # If we have other videos, delete the default Rick Roll video from being monitored
            other_videos = [v for v in videos if v["video_id"] != "dQw4w9WgXcQ"]
            if other_videos:
                for v in videos:
                    if v["video_id"] == "dQw4w9WgXcQ":
                        supabase_svc.delete_youtube_video("dQw4w9WgXcQ")
                videos = other_videos
            elif not videos:
                # Seed mock video if none exist
                mock_video = supabase_svc.create_youtube_video(
                    channel_id=channel_id,
                    video_id="dQw4w9WgXcQ",
                    title="100% Organic Cold Pressed Coconut Oil - VyaparAI Promo",
                    publish_date=datetime.now().isoformat(),
                    status="monitored"
                )
                videos = [mock_video]

            # Determine if we're in sandbox/simulation mode
            is_mock_channel = channel.get("access_token") == "mock_access_token"
            
            for video in videos:
                video_id = video["video_id"]
                logger.info(f"Scanning comment threads for video: {video_id} ({video['title']})")
                
                if is_mock_channel:
                    await self._poll_mock_comments(channel_id, video_id)
                else:
                    await self._poll_real_youtube_comments(channel, video_id)

    async def _poll_mock_comments(self, channel_id: str, video_id: str):
        """Seed simulated comments for testing the dashboard offline"""
        # Pick a comment that hasn't been added yet
        existing_comments = [c for c in supabase_svc.get_youtube_comments() if c["video_id"] == video_id]
        existing_texts = {c["text"] for c in existing_comments}
        
        # Determine product name for this video
        product_name = "product"
        try:
            videos = supabase_svc._select_all("videos")
            vid = next((v for v in videos if v.get("youtube_id") == video_id), None)
            if vid:
                voiceovers = supabase_svc._select_all("voiceovers")
                voice = next((v for v in voiceovers if v["id"] == vid["voiceover_id"]), None)
                if voice:
                    translations = supabase_svc._select_all("translations")
                    trans = next((t for t in translations if t["id"] == voice["translation_id"]), None)
                    if trans:
                        scripts = supabase_svc._select_all("scripts")
                        script = next((s for s in scripts if s["id"] == trans["script_id"]), None)
                        if script:
                            products = supabase_svc.get_products()
                            product = next((p for p in products if p["id"] == script["product_id"]), None)
                            if product:
                                product_name = product["name"]
        except Exception as e:
            logger.warning(f"Error determining product name for mock comments: {e}")

        # Add next available mock comment
        for demo in MOCK_INCOMING_COMMENTS:
            demo_text = demo["text"].replace("coconut oil", product_name).replace("Coconut Oil", product_name)
            if demo_text not in existing_texts:
                comment_id = f"MOCK_CMT_{uuid.uuid4().hex[:8].upper()}"
                logger.info(f"[SANDBOX MONITOR] Detected new comment: @{demo['username']}: \"{demo_text}\"")
                
                # Execute the multi-agent orchestration loop asynchronously
                asyncio.create_task(
                    youtube_monitor_crew.process_single_comment(
                        channel_id=channel_id,
                        video_id=video_id,
                        comment_id=comment_id,
                        username=demo["username"],
                        comment_text=demo_text,
                        timestamp=demo["timestamp"]
                    )
                )
                break # Limit to one comment injection per poll cycle to simulate flow

    async def _poll_real_youtube_comments(self, channel: Dict[str, Any], video_id: str):
        """Fetch comments using real Google APIs with token refresh capability"""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            
            creds = Credentials(
                token=channel["access_token"],
                refresh_token=channel.get("refresh_token"),
                token_uri=channel.get("token_uri") or "https://oauth2.googleapis.com/token",
                client_id=channel.get("client_id"),
                client_secret=channel.get("client_secret")
            )
            
            # Check refresh if expired
            if creds.expired and creds.refresh_token:
                logger.info(f"Access token for channel {channel['channel_name']} expired. Refreshing token...")
                creds.refresh(Request())
                # Update in DB
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

            youtube = build("youtube", "v3", credentials=creds)
            
            # Call commentThreads.list API
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=50,
                textFormat="plainText"
            )
            response = request.execute()
            
            items = response.get("items", [])
            for item in items:
                top_comment = item["snippet"]["topLevelComment"]
                comment_id = top_comment["id"]
                snippet = top_comment["snippet"]
                author = snippet.get("authorDisplayName", "Anonymous")
                # Remove leading @ if present
                if author.startswith("@"):
                    author = author[1:]
                text = snippet.get("textDisplay", "")
                timestamp = snippet.get("publishedAt", datetime.now().isoformat())
                
                # Check if duplicate comment exists in DB
                existing = supabase_svc.get_youtube_comment(comment_id)
                if not existing:
                    logger.info(f"[API MONITOR] Ingesting new comment {comment_id} from @{author}")
                    asyncio.create_task(
                        youtube_monitor_crew.process_single_comment(
                            channel_id=channel["channel_id"],
                            video_id=video_id,
                            comment_id=comment_id,
                            username=author,
                            comment_text=text,
                            timestamp=timestamp
                        )
                    )
                    
        except Exception as e:
            # Detect if the video was deleted or made private (404 Not Found)
            import googleapiclient.errors
            if isinstance(e, googleapiclient.errors.HttpError) and e.resp.status in [404, 403]:
                logger.warning(f"Video {video_id} is no longer accessible (Deleted or Private). Removing from monitor list.")
                supabase_svc.delete_youtube_video(video_id)
    async def sync_channel_videos(self, channel: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch recent uploaded videos from YouTube API and index them in the database"""
        channel_id = channel["channel_id"]
        logger.info(f"Syncing videos for channel {channel_id} ({channel.get('channel_name')})...")
        
        if channel.get("access_token") == "mock_access_token":
            # In mock mode, keep current monitored videos
            return supabase_svc.get_youtube_videos()

        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            
            creds = Credentials(
                token=channel["access_token"],
                refresh_token=channel.get("refresh_token"),
                token_uri=channel.get("token_uri") or "https://oauth2.googleapis.com/token",
                client_id=channel.get("client_id"),
                client_secret=channel.get("client_secret")
            )
            
            # Check refresh if expired
            if creds.expired and creds.refresh_token:
                logger.info(f"Access token for channel {channel.get('channel_name')} expired. Refreshing token...")
                creds.refresh(Request())
                # Update in DB
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

            youtube = build("youtube", "v3", credentials=creds)
            
            # 1. Retrieve the uploads playlist ID
            channel_response = youtube.channels().list(
                part="contentDetails",
                mine=True
            ).execute()
            
            if not channel_response.get("items"):
                logger.warning(f"No channel details found for active credentials.")
                return supabase_svc.get_youtube_videos()
                
            uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # 2. Retrieve playlist items from the uploads playlist
            playlist_response = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50
            ).execute()
            
            items = playlist_response.get("items", [])
            synced_videos = []
            for item in items:
                video_id = item["snippet"]["resourceId"]["videoId"]
                title = item["snippet"]["title"]
                publish_date = item["snippet"].get("publishedAt")
                
                # Check if video already exists in DB, create if not
                video_rec = supabase_svc.get_youtube_video(video_id)
                if not video_rec:
                    logger.info(f"Discovered new upload on YouTube channel: {title} ({video_id})")
                    video_rec = supabase_svc.create_youtube_video(
                        channel_id=channel_id,
                        video_id=video_id,
                        title=title,
                        publish_date=publish_date,
                        status="monitored"
                    )
                synced_videos.append(video_rec)
                
            return synced_videos
        except Exception as e:
            logger.error(f"Failed to sync channel videos from YouTube: {e}", exc_info=True)
            return supabase_svc.get_youtube_videos()

    async def inject_comment_manually(self, channel_id: str, video_id: str, username: str, text: str) -> Dict[str, Any]:
        """Manually force comment ingestion for testing the flow immediately"""
        comment_id = f"MANUAL_CMT_{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now().isoformat()
        
        # Process asynchronously but return details
        res = await youtube_monitor_crew.process_single_comment(
            channel_id=channel_id,
            video_id=video_id,
            comment_id=comment_id,
            username=username,
            comment_text=text,
            timestamp=timestamp
        )
        return res

youtube_monitor_svc = YouTubeMonitorService()
