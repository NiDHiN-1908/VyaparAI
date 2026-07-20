- [x] Backend YouTube Link Generator Endpoint
    - [x] Implement `GET /youtube/comments/{comment_id}/whatsapp-link` in `backend/routers/youtube_monitor.py`
    - [x] Resolve active connected WhatsApp instance phone number dynamically
    - [x] Build wa.me URL containing attribution suffix `(Ref: YT_<comment_id>)`
- [x] AI Autopilot Suggested Reply Update
    - [x] Update `youtube_monitor_crew.py` to automatically append the WhatsApp link to the suggestion for `HIGH_INTENT` comments
- [x] Incoming Webhook Attribution Processing
    - [x] Update `handle_evolution_webhook` in `webhook_handler.py` to parse `Ref: YT_(\w+)` from inbound message text
    - [x] Extract comment ID, fetch comment/lead info, and update conversation's `lead_id` and metadata
- [x] Frontend Comment Inbox UI Enhancements
    - [x] Display WhatsApp status in `comment-inbox/page.tsx`
    - [x] Add "Insert WhatsApp Link" button to inject generated wa.me CTA into the reply textarea
- [x] Frontend Live Chat Dashboard Context Banner
    - [x] Read conversation metadata source in `live-chat/page.tsx`
    - [x] Render context banner detailing video title and source comment text
- [x] Verification & Testing
    - [x] Inject comment and verify auto-appended CTA
    - [x] Test webhook attribution mapping using mock message payload

# Refactoring Video Generation to Support Asynchronous Workflows

- [x] Database Schema: Create `004_video_jobs.sql` migration script and register in `MOCK_DB`
- [x] Supabase Service: Implement accessor methods for `video_jobs` table in `supabase_service.py`
- [x] Backend router: Modify `generate-content` and status check routes, and add `/video-jobs/active` in `marketing.py`
- [x] Upload Page: Update `upload/page.tsx` to handle background job status, timeouts and transition to non-blocking UI
- [x] Preview Page: Update `preview/page.tsx` to support job tracking and dynamic video loading on completion
- [x] Approval Page: Update `approval/page.tsx` with same tracking behaviours
