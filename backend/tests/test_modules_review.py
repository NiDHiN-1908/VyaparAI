# backend/tests/test_modules_review.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.supabase_service import supabase_svc
from backend.crews.youtube_monitor_crew import get_auto_reply_config, set_auto_reply_config

client = TestClient(app)

def test_target_catalog_product():
    # nursery campaign video matches seeded fig plant product
    res = client.get("/youtube/videos/PuCb1JHpBkM/products")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["data"]) > 0
    assert any("fiddle" in p["name"].lower() or "fig" in p["name"].lower() for p in data["data"])

    # unrelated video id should return empty or default fallbacks
    res_empty = client.get("/youtube/videos/unrelated_vid/products")
    assert res_empty.status_code == 200
    assert len(res_empty.json()["data"]) == 0


def test_auto_reply_config_io():
    # Verify settings reader and writer preserves confidence_threshold
    orig_config = get_auto_reply_config()
    try:
        test_cfg = {"auto_reply": True, "confidence_threshold": 0.88}
        set_auto_reply_config(test_cfg)
        
        cfg = get_auto_reply_config()
        assert cfg["auto_reply"] is True
        assert cfg["confidence_threshold"] == 0.88
    finally:
        set_auto_reply_config(orig_config)


def test_campaign_analytics_endpoint():
    res = client.get("/analytics/campaigns")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "campaign_status" in data
    assert "products_promoted" in data
    assert "videos_published" in data
    assert "total_comments" in data
    assert "qualified_leads" in data
    assert "revenue" in data
    assert "avg_response_time" in data
    assert "top_campaigns" in data
    assert "funnel" in data


def test_youtube_analytics_dashboard_fields():
    res = client.get("/youtube/analytics")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    fields = data["data"]
    assert "views" in fields
    assert "likes" in fields
    assert "watch_time" in fields
    assert "subscribers" in fields
    assert "engagement_rate" in fields
    assert "shares" in fields
    assert "traffic_trends" in fields
    assert "audience_growth" in fields


def test_lead_dashboard_crm_endpoint():
    res = client.get("/youtube/leads/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    
    assert "summary" in data
    summary = data["summary"]
    assert "total_leads" in summary
    assert "contact_rate" in summary
    assert "hot_leads" in summary
    assert "warm_leads" in summary
    assert "cold_leads" in summary
    assert "revenue_attributed" in summary
    
    assert "funnel" in data
    assert "trends" in data
    assert "leads" in data
    assert "activity" in data


@pytest.mark.anyio
async def test_youtube_comment_failure_transition(monkeypatch):
    # 1. Connect mock channel
    client.post("/auth/youtube/mock-connect")
    
    # 2. Get video ID
    videos_res = client.get("/youtube/videos")
    assert videos_res.status_code == 200
    video_id = videos_res.json()["data"][0]["video_id"]
    
    # 3. Enable video & global auto_reply
    client.post(f"/youtube/videos/{video_id}/auto-reply", json={"auto_reply": True})
    client.post("/youtube/settings/auto-reply", json={"auto_reply": True, "confidence_threshold": 0.5})
    
    # 4. Mock publish_reply_to_youtube to raise exception
    from backend.crews.youtube_monitor_crew import youtube_monitor_crew
    async def mock_failed_publish(comment_id, reply_text):
        raise Exception("YouTube API quota exceeded mock failure")
    monkeypatch.setattr(youtube_monitor_crew, "publish_reply_to_youtube", mock_failed_publish)
    
    # 5. Inject a comment
    inject_res = client.post("/youtube/comments/inject", json={
        "video_id": video_id,
        "username": "failure_tester",
        "comment_text": "I want to buy Fiddle Leaf Fig plant now!"
    })
    assert inject_res.status_code == 200
    
    # 6. Retrieve the comment and assert status is failed
    comments_res = client.get("/youtube/comments")
    comments = comments_res.json()["data"]
    failed_cmt = next((c for c in comments if c["username"] == "failure_tester"), None)
    assert failed_cmt is not None
    assert failed_cmt["status"] == "failed"
    assert failed_cmt["reply"] is not None
    assert failed_cmt["reply"]["status"] == "failed"
    assert "quota exceeded" in failed_cmt["reply"]["failure_reason"]
    
    # 7. Retry posting manually
    monkeypatch.undo() # Restore original publisher function
    retry_res = client.post(f"/youtube/comments/{failed_cmt['comment_id']}/approve", json={
        "reply_text": "Hey @failure_tester, click the WhatsApp link to buy."
    })
    assert retry_res.status_code == 200
    
    # 8. Verify comment status updated to replied
    comments_res2 = client.get("/youtube/comments")
    comments2 = comments_res2.json()["data"]
    replied_cmt = next((c for c in comments2 if c["username"] == "failure_tester"), None)
    assert replied_cmt["status"] == "replied"
    
    # Clean up
    client.post("/youtube/settings/auto-reply", json={"auto_reply": False})
