# backend/tests/test_backend.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.supabase_service import supabase_svc
from backend.agents.comment_monitor_agent import classify_comment_heuristics
from backend.agents.quality_agent import audit_campaign_quality
from backend.services.youtube_publishing_service import youtube_publish_svc

client = TestClient(app)

# Test 1: API root check
def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

# Test 2: In-Memory/Supabase Database insertions
def test_database_operations():
    biz = supabase_svc.create_business(name="Test Shop", location="Bangalore")
    assert biz["id"] is not None
    
    # Register product with images list
    prod = supabase_svc.create_product(
        business_id=biz["id"], 
        name="Silk Saree", 
        description="Fine fabric", 
        price=4500.0,
        images=["/media/img1.jpg", "/media/img2.jpg"]
    )
    assert prod["id"] is not None
    assert len(prod["images"]) == 2

# Test 3: QualityAgent rating scoring
def test_quality_audits():
    # Complete script
    script_pass = {
        "title": "Authentic Cardamom Campaign",
        "hook": "Are you looking for the best cardamom?",
        "script_text": "Introducing our premium cardamom sourced from organic farms."
    }
    res_pass = audit_campaign_quality(script_pass, ["cardamom"])
    assert res_pass["status"] == "APPROVED"
    assert res_pass["score"] >= 80

    # Incomplete script failing score < 80
    script_fail = {
        "title": "Elaichi",
        "hook": "",
        "script_text": "buy elaichi"
    }
    res_fail = audit_campaign_quality(script_fail, ["cardamom"])
    assert res_fail["status"] == "REGENERATE"
    assert res_fail["score"] < 80

# Test 4: YouTubePublishingService Sandbox publishing
def test_youtube_publishing():
    pub_res = youtube_publish_svc.publish_video(
        video_path="mock_video.mp4",
        title="Spices Campaign",
        description="Best organic spices",
        hashtags=["Spices", "Munnar"]
    )
    assert pub_res["status"] == "success"
    assert pub_res["youtube_id"] is not None
    assert "youtube.com" in pub_res["youtube_url"]
