# backend/routers/youtube_monitor.py (Forwarding wrapper for backward compatibility)
from backend.modules.video_monitoring_module.router import (
    router,
    CommentInjectRequest,
    ReplyApproveRequest,
    AutoReplyToggleRequest,
    VideoAutoReplyToggleRequest,
    VideoStatusToggleRequest
)
