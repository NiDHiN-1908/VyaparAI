# backend/tests/test_youtube_integration.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.supabase_service import supabase_svc
from backend.crews.youtube_monitor_crew import fallback_classify_comment, fallback_generate_reply
from backend.modules.video_monitoring_module import video_monitoring_svc as youtube_monitor_svc

client = TestClient(app)

def test_fallback_intent_classification():
    # HIGH INTENT examples
    res1 = fallback_classify_comment("What is the price of this product?")
    assert res1["intent"] == "HIGH_INTENT"
    assert res1["confidence"] > 0.9

    res2 = fallback_classify_comment("how can I buy this oil?")
    assert res2["intent"] == "HIGH_INTENT"

    # MEDIUM INTENT examples
    res3 = fallback_classify_comment("why is cold pressed oil better than refined?")
    assert res3["intent"] == "MEDIUM_INTENT"

    # LOW INTENT examples
    res4 = fallback_classify_comment("wow beautiful presentation")
    assert res4["intent"] == "LOW_INTENT"

    # SPAM examples
    res5 = fallback_classify_comment("Get 1000 free subscribers at www.freeviralgrow.com")
    assert res5["intent"] == "SPAM"


def test_fallback_reply_generation():
    rep1 = fallback_generate_reply("price?", "HIGH_INTENT", "ravi")
    assert "WhatsApp" in rep1
    assert "@ravi" in rep1

    rep2 = fallback_generate_reply("wow", "LOW_INTENT", "ravi")
    assert "appreciate" in rep2 or "support" in rep2


def test_youtube_endpoints_mock_workflow():
    # Ensure global auto-reply is disabled for baseline test state
    client.post("/youtube/settings/auto-reply", json={"auto_reply": False, "confidence_threshold": 0.80})

    # 0. Disconnect any existing channels first to ensure a clean test state
    client.post("/auth/youtube/disconnect")

    # 1. Connect mock channel
    res = client.post("/auth/youtube/mock-connect")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # 2. Check channel connection status
    status_res = client.get("/auth/youtube/status")
    assert status_res.status_code == 200
    assert status_res.json()["connected"] is True
    assert status_res.json()["channel"]["channel_id"] == "UC_MOCK_VYAPAR_AI"

    # 3. Inject high-intent comment
    inject_res = client.post("/youtube/comments/inject", json={
        "video_id": "vid_1",
        "username": "vijay_kumar",
        "comment_text": "Do you offer home delivery in Kochi? Price?"
    })
    assert inject_res.status_code == 200
    assert inject_res.json()["status"] == "success"

    # 4. Check comments inbox contains the comment with correct intent
    comments_res = client.get("/youtube/comments")
    assert comments_res.status_code == 200
    comments_data = comments_res.json()["data"]
    
    vijay_comment = next((c for c in comments_data if c["username"] == "vijay_kumar"), None)
    assert vijay_comment is not None
    assert vijay_comment["intent"] == "HIGH_INTENT"
    assert vijay_comment["status"] == "pending_approval"
    assert vijay_comment["reply"] is not None
    assert "suggested_reply" in vijay_comment["reply"]

    # 5. Check lead dashboard lists vijay_kumar as a lead
    leads_res = client.get("/youtube/leads")
    assert leads_res.status_code == 200
    leads_data = leads_res.json()["data"]
    vijay_lead = next((l for l in leads_data if l["username"] == "vijay_kumar"), None)
    assert vijay_lead is not None
    assert vijay_lead["intent"] == "HIGH_INTENT"

    # 6. Approve suggested reply
    approve_res = client.post(f"/youtube/comments/{vijay_comment['comment_id']}/approve", json={
        "reply_text": "Thanks @vijay_kumar! Yes, delivery is available. Contact us on WhatsApp."
    })
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "success"

    # 7. Check comment status changed to replied
    comments_res2 = client.get("/youtube/comments")
    comments_data2 = comments_res2.json()["data"]
    vijay_comment2 = next((c for c in comments_data2 if c["username"] == "vijay_kumar"), None)
    assert vijay_comment2["status"] == "replied"

    # 8. Check analytics updated
    analytics_res = client.get("/youtube/analytics")
    assert analytics_res.status_code == 200
    analytics_data = analytics_res.json()["data"]
    assert analytics_data["comments_processed"] >= 1
    assert analytics_data["lead_count"] >= 1


def test_youtube_video_auto_reply_toggling():
    # 1. Connect mock channel
    client.post("/auth/youtube/mock-connect")
    
    # 2. Sync / get videos
    videos_res = client.get("/youtube/videos")
    assert videos_res.status_code == 200
    videos = videos_res.json()["data"]
    assert len(videos) > 0
    video_id = videos[0]["video_id"]
    
    # 3. Enable global auto_reply first
    client.post("/youtube/settings/auto-reply", json={"auto_reply": True, "confidence_threshold": 0.80})
    
    # 4. Toggle video auto_reply to False
    toggle_res = client.post(f"/youtube/videos/{video_id}/auto-reply", json={"auto_reply": False})
    assert toggle_res.status_code == 200
    assert toggle_res.json()["status"] == "success"
    
    # Verify DB update
    vid_rec = supabase_svc.get_youtube_video(video_id)
    assert vid_rec["auto_reply"] is False
    
    # 5. Inject comment while video auto_reply is False
    inject_res = client.post("/youtube/comments/inject", json={
        "video_id": video_id,
        "username": "user_manual",
        "comment_text": "Price details?"
    })
    assert inject_res.status_code == 200
    
    # Verify comment is pending_approval
    comments_res = client.get("/youtube/comments")
    comments = comments_res.json()["data"]
    c_manual = next((c for c in comments if c["username"] == "user_manual"), None)
    assert c_manual is not None
    assert c_manual["status"] == "pending_approval"
    
    # 6. Toggle video auto_reply back to True
    toggle_res = client.post(f"/youtube/videos/{video_id}/auto-reply", json={"auto_reply": True})
    assert toggle_res.status_code == 200
    
    # Verify DB update
    vid_rec = supabase_svc.get_youtube_video(video_id)
    assert vid_rec["auto_reply"] is True
    
    # 7. Inject comment while video auto_reply is True
    inject_res = client.post("/youtube/comments/inject", json={
        "video_id": video_id,
        "username": "user_auto",
        "comment_text": "How to order?"
    })
    assert inject_res.status_code == 200
    
    # Verify comment has been auto replied
    comments_res = client.get("/youtube/comments")
    comments = comments_res.json()["data"]
    c_auto = next((c for c in comments if c["username"] == "user_auto"), None)
    assert c_auto is not None
    # since effective auto reply is True, status should be replied
    assert c_auto["status"] == "replied"
    
    # Clean up settings
    client.post("/youtube/settings/auto-reply", json={"auto_reply": False, "confidence_threshold": 0.80})
