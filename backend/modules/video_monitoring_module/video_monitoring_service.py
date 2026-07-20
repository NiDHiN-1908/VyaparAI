# backend/modules/video_monitoring_module/video_monitoring_service.py
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List
from googleapiclient.discovery import build

from backend.services.supabase_service import supabase_svc
from backend.crews.youtube_monitor_crew import youtube_monitor_crew

logger = logging.getLogger("vyaparai.modules.video_monitoring_module.service")

# List of demo comments for sandbox simulation mode
MOCK_INCOMING_COMMENTS = [
    {"username": "arun_raj", "text": "What is the price of coconut oil? Do you deliver to Bangalore?", "timestamp": "2026-06-12T11:00:00Z"},
    {"username": "hema_bhat", "text": "How can I order? Please share contact number.", "timestamp": "2026-06-12T11:05:00Z"},
    {"username": "rahul_k", "text": "Is this product chemical free?", "timestamp": "2026-06-12T11:10:00Z"},
    {"username": "crypto_guy", "text": "Click here to win a free iphone! www.spambot.com", "timestamp": "2026-06-12T11:15:00Z"},
    {"username": "meera_nair", "text": "Super quality, highly recommended! ❤️", "timestamp": "2026-06-12T11:20:00Z"},
    {"username": "vicky_sharma", "text": "Do you offer cash on delivery?", "timestamp": "2026-06-12T11:25:00Z"},
]

class VideoMonitoringService:
    def __init__(self):
        self.is_running = False
        self.task = None
        self.last_sync_error = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self.monitor_loop())
            logger.info("Video Monitoring Service started successfully.")

    def stop(self):
        if self.is_running:
            self.is_running = False
            if self.task:
                self.task.cancel()
            logger.info("Video Monitoring Service stopped.")

    async def monitor_loop(self):
        # Allow server to startup completely before running background tasks
        await asyncio.sleep(5)
        while self.is_running:
            try:
                logger.info("Running scheduled video and comment monitoring cycle...")
                await self.poll_comments_for_all_channels()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in video monitor cycle: {e}", exc_info=True)
            
            # Sleep for 5 minutes (300 seconds)
            await asyncio.sleep(300)

    async def poll_comments_for_all_channels(self):
        self.last_sync_error = None
        channels = supabase_svc.get_youtube_channels()
        if not channels:
            logger.info("No connected YouTube channels found. Skipping comment monitor cycle.")
            return

        for channel in channels:
            channel_id = channel["channel_id"]
            # Sync channel videos first to ensure we monitor all uploads
            await self.sync_channel_videos(channel)

            # Fetch videos with monitored status
            videos = [v for v in supabase_svc.get_youtube_videos() if v["channel_id"] == channel_id and v.get("status") == "monitored"]
            
            # Clean up the old Rick Roll video from database if it exists
            for v in videos:
                if v["video_id"] == "dQw4w9WgXcQ":
                    supabase_svc.delete_youtube_video("dQw4w9WgXcQ")
            videos = [v for v in supabase_svc.get_youtube_videos() if v["channel_id"] == channel_id and v.get("status") == "monitored"]
            
            if not videos:
                # Seed mock video if none exist (using Nursery Campaign instead)
                mock_video = supabase_svc.create_youtube_video(
                    channel_id=channel_id,
                    video_id="PuCb1JHpBkM",
                    title="Nursery Greenery Launch Campaign",
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
        comment_injected = False
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
                comment_injected = True
                break # Limit to one comment injection per poll cycle to simulate flow
            else:
                logger.debug(f"[SANDBOX MONITOR] Comment from @{demo['username']} already exists. Skipping.")
                
        if not comment_injected:
            logger.info("[SANDBOX MONITOR] No new mock comments available to ingest.")

    async def _poll_real_youtube_comments(self, channel: Dict[str, Any], video_id: str):
        """Fetch comments using real Google APIs with token refresh capability"""
        try:
            from backend.services.youtube_auth_helper import execute_youtube_call
            
            logger.info(f"[API MONITOR] Requesting comments list for video {video_id} using YouTube Data API...")
            response = await asyncio.to_thread(
                execute_youtube_call,
                channel,
                lambda yt: yt.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=50,
                    textFormat="plainText"
                )
            )
            
            items = response.get("items", [])
            logger.info(f"[API MONITOR] Retrieved {len(items)} comment threads for video {video_id}.")
            
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
                else:
                    logger.info(f"[API MONITOR] Duplicate detection: comment {comment_id} from @{author} already exists. Skipping Ingestion.")
                    
        except Exception as e:
            self.last_sync_error = f"YouTube API comments lookup failed: {e}"
            logger.error(f"[API MONITOR ERROR] YouTube API comments lookup failed for video {video_id}: {e}", exc_info=True)
            # Detect if the video was deleted or made private (404 Not Found)
            import googleapiclient.errors
            if isinstance(e, googleapiclient.errors.HttpError):
                if e.resp.status in [401, 403]:
                    logger.error("YouTube API authentication failed. Access token might be invalid or expired.")
                    self.last_sync_error = "YouTube API authentication failed. Access token might be invalid or expired. Please connect again."
                elif e.resp.status in [404]:
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
            from backend.services.youtube_auth_helper import execute_youtube_call
            
            # 1. Retrieve the uploads playlist ID
            channel_response = await asyncio.to_thread(
                execute_youtube_call,
                channel,
                lambda yt: yt.channels().list(
                    part="contentDetails",
                    mine=True
                )
            )
            
            if not channel_response.get("items"):
                logger.warning(f"No channel details found for active credentials.")
                return supabase_svc.get_youtube_videos()
                
            uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # 2. Retrieve playlist items from the uploads playlist
            playlist_response = await asyncio.to_thread(
                execute_youtube_call,
                channel,
                lambda yt: yt.playlistItems().list(
                    part="snippet",
                    playlistId=uploads_playlist_id,
                    maxResults=50
                )
            )
            
            items = playlist_response.get("items", [])
            fetched_video_ids = {item["snippet"]["resourceId"]["videoId"] for item in items}
            
            # Clean up old videos in the database for this channel that are no longer in the playlist
            db_videos = supabase_svc.get_youtube_videos()
            for db_video in db_videos:
                if db_video.get("channel_id") == channel_id:
                    v_id = db_video.get("video_id")
                    if v_id and v_id not in fetched_video_ids:
                        logger.info(f"Removing deleted/outdated video {v_id} from database")
                        # Clean up associated comments, replies, and leads
                        if supabase_svc.is_mock:
                            from backend.services.supabase_service import MOCK_DB, save_mock_db
                            v_cmts = {c["comment_id"] for c in MOCK_DB["youtube_comments"] if c.get("video_id") == v_id}
                            MOCK_DB["youtube_comments"] = [c for c in MOCK_DB["youtube_comments"] if c.get("video_id") != v_id]
                            MOCK_DB["youtube_replies"] = [r for r in MOCK_DB["youtube_replies"] if r.get("comment_id") not in v_cmts]
                            MOCK_DB["youtube_leads"] = [l for l in MOCK_DB["youtube_leads"] if l.get("video_id") != v_id]
                            save_mock_db()
                        else:
                            try:
                                # Get comments to find comment_ids
                                res_comments = supabase_svc.client.table("youtube_comments").select("comment_id").eq("video_id", v_id).execute()
                                if res_comments.data:
                                    cmt_ids = [c["comment_id"] for c in res_comments.data]
                                    if cmt_ids:
                                        # Delete replies
                                        supabase_svc.client.table("youtube_replies").delete().in_("comment_id", cmt_ids).execute()
                                # Delete comments
                                supabase_svc.client.table("youtube_comments").delete().eq("video_id", v_id).execute()
                                # Delete leads
                                supabase_svc.client.table("youtube_leads").delete().eq("video_id", v_id).execute()
                            except Exception as db_err:
                                logger.warning(f"Associated details cleanup failed for video {v_id}: {db_err}")
                        
                        # Delete video
                        supabase_svc.delete_youtube_video(v_id)

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
                else:
                    # If it exists, but belongs to a different channel_id (e.g., leftover mock channel), re-link to active channel
                    if video_rec.get("channel_id") != channel_id:
                        logger.info(f"Sync: Video {video_id} belongs to channel {video_rec.get('channel_id')}. Re-linking to active channel {channel_id}.")
                        if supabase_svc.is_mock:
                            video_rec["channel_id"] = channel_id
                            from backend.services.supabase_service import save_mock_db
                            save_mock_db()
                        else:
                            try:
                                supabase_svc.client.table("youtube_videos").update({"channel_id": channel_id}).eq("id", video_rec["id"]).execute()
                                video_rec["channel_id"] = channel_id
                            except Exception as db_err:
                                logger.error(f"Failed to update channel_id for video {video_id}: {db_err}")
                synced_videos.append(video_rec)
                
            return synced_videos
        except Exception as e:
            self.last_sync_error = f"Failed to sync channel videos: {e}"
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

youtube_monitor_svc = VideoMonitoringService()
video_monitoring_svc = youtube_monitor_svc
