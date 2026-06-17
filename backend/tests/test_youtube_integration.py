# backend/tests/test_youtube_integration.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.supabase_service import supabase_svc
from backend.crews.youtube_monitor_crew import fallback_classify_comment, fallback_generate_reply
from backend.services.youtube_monitor_service import youtube_monitor_svc

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
