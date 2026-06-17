# backend/tests/conftest.py
import pytest
from backend.services.youtube_monitor_service import youtube_monitor_svc

@pytest.fixture(autouse=True)
def cleanup_services():
    yield
    try:
        youtube_monitor_svc.stop()
    except Exception:
        pass
