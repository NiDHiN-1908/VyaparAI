# backend/routers/health.py
from fastapi import APIRouter
from backend.services.startup_manager import startup_mgr
from backend.modules.video_monitoring_module import video_monitoring_svc as youtube_monitor_svc
from backend.services.supabase_service import supabase_svc, MOCK_DB
import traceback
import sys
import logging

router = APIRouter(tags=["Health"])

@router.get("/health")
async def get_health():
    """
    Returns the comprehensive health and readiness status of the backend and all downstream services.
    """
    return startup_mgr.get_health_report()


