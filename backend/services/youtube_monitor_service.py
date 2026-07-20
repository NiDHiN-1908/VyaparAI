# backend/services/youtube_monitor_service.py (Forwarding wrapper for backward compatibility)
from backend.modules.video_monitoring_module.video_monitoring_service import youtube_monitor_svc, VideoMonitoringService
# Also export under the original name to ensure all legacy imports work without issues
YouTubeMonitorService = VideoMonitoringService
