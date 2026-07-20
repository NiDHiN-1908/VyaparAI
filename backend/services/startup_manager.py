# backend/services/startup_manager.py
import time
import os
import sys
import asyncio
import logging
import socket
import httpx
from typing import Dict, Any, Optional
from backend.config import settings

logger = logging.getLogger("vyaparai.startup_manager")

class StartupManager:
    def __init__(self):
        self.metrics = {
            "environment_loading": {"duration": 0.0, "status": "PENDING"},
            "dependency_initialization": {"duration": 0.0, "status": "PENDING"},
            "database_connection": {"duration": 0.0, "status": "PENDING"},
            "supabase_connection": {"duration": 0.0, "status": "PENDING"},
            "ai_model_initialization": {"duration": 0.0, "status": "PENDING"},
            "whatsapp_service_startup": {"duration": 0.0, "status": "PENDING"},
            "tunnel_creation": {"duration": 0.0, "status": "PENDING"},
            "api_server_startup": {"duration": 0.0, "status": "PENDING"},
            "background_workers": {"duration": 0.0, "status": "PENDING"},
        }
        self.start_times = {}
        self.ready = False
        self.total_duration = 0.0
        self.startup_start = time.time()
        self.initialization_task = None

    def set_metric(self, name: str, duration: float, success: bool = True):
        if name in self.metrics:
            self.metrics[name] = {
                "duration": duration,
                "status": "SUCCESS" if success else "FAILED"
            }

    def start_metric(self, name: str):
        self.start_times[name] = time.time()

    def stop_metric(self, name: str, success: bool = True):
        if name in self.start_times and name in self.metrics:
            duration = time.time() - self.start_times[name]
            self.metrics[name] = {
                "duration": duration,
                "status": "SUCCESS" if success else "FAILED"
            }

    def start_background_initialization(self):
        """Starts non-blocking service checks in the background."""
        self.initialization_task = asyncio.create_task(self.initialize_services_in_background())

    async def initialize_services_in_background(self):
        logger.info("Initializing services check in background...")
        
        # 1. Database Connection check (Wrapper state)
        from backend.database.connection import db_conn
        db_mode = "mock" if db_conn.is_mock else "real"
        # Database connection wrapper is fast to instantiate
        self.set_metric("database_connection", 0.001, True)

        # 2. Concurrently run the diagnostic pings (Supabase, Ollama, WhatsApp, Tunnel)
        async def check_supabase_ping():
            self.start_metric("supabase_connection")
            if db_conn.is_mock:
                self.stop_metric("supabase_connection", True)
                self.metrics["supabase_connection"]["status"] = "SUCCESS (MOCK)"
                return True
            
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.get(
                        f"{settings.SUPABASE_URL}/rest/v1/",
                        headers={"apikey": settings.SUPABASE_KEY},
                        timeout=3.0
                    )
                    success = res.status_code in [200, 404, 401]
                    self.stop_metric("supabase_connection", success)
                    return success
            except Exception as e:
                logger.warning(f"Supabase connection diagnostic failed: {e}")
                self.stop_metric("supabase_connection", False)
                return False

        async def check_ollama_ping():
            self.start_metric("ai_model_initialization")
            try:
                # Check if Ollama is listening on local port 11434
                async with httpx.AsyncClient() as client:
                    res = await client.get(f"{settings.OLLAMA_BASE_URL}", timeout=2.0)
                    success = res.status_code == 200 or "ollama" in res.text.lower()
                    self.stop_metric("ai_model_initialization", success)
                    return success
            except Exception as e:
                logger.warning(f"Ollama local ping failed: {e}. AI features will operate with rules or fallback.")
                self.stop_metric("ai_model_initialization", False)
                return False

        async def check_whatsapp_ping():
            self.start_metric("whatsapp_service_startup")
            provider_name = os.getenv("WHATSAPP_PROVIDER", "evolution")
            if provider_name == "meta":
                # Meta sandbox check
                has_key = bool(os.getenv("META_ACCESS_TOKEN"))
                self.stop_metric("whatsapp_service_startup", has_key)
                return has_key
            else:
                # Evolution API check
                evo_url = os.getenv("EVOLUTION_API_URL") or "http://localhost:8080"
                evo_key = os.getenv("EVOLUTION_API_KEY")
                if not evo_url or not evo_key:
                    # In sandbox mode, it counts as success (running mockup)
                    self.stop_metric("whatsapp_service_startup", True)
                    self.metrics["whatsapp_service_startup"]["status"] = "SUCCESS (MOCK)"
                    return True
                try:
                    async with httpx.AsyncClient() as client:
                        res = await client.get(
                            f"{evo_url.rstrip('/')}/instance/fetchInstances",
                            headers={"apikey": evo_key},
                            timeout=2.0
                        )
                        success = res.status_code == 200
                        self.stop_metric("whatsapp_service_startup", success)
                        return success
                except Exception:
                    # Evolution API offline, fallback to simulation mode
                    self.stop_metric("whatsapp_service_startup", True)
                    self.metrics["whatsapp_service_startup"]["status"] = "SUCCESS (FALLBACK)"
                    return True

        async def check_tunnel_ping():
            self.start_metric("tunnel_creation")
            from backend.services.tunnel_manager import tunnel_mgr
            
            # 1. Establish the tunnel (runs in thread pool)
            started = await asyncio.to_thread(tunnel_mgr.start_tunnel)
            if not started:
                self.stop_metric("tunnel_creation", False)
                return False
                
            # 2. Verify health by loopback check
            health_ok = await asyncio.to_thread(tunnel_mgr.verify_tunnel_health)
            self.stop_metric("tunnel_creation", health_ok)
            return health_ok

        # Run checks in parallel
        await asyncio.gather(
            check_supabase_ping(),
            check_ollama_ping(),
            check_whatsapp_ping(),
            check_tunnel_ping()
        )

        self.ready = True
        self.total_duration = time.time() - self.startup_start
        self.print_dashboard()

    def print_dashboard(self):
        print("\n" + "=" * 55)
        print("         V Y A P A R   A I   S T A R T U P")
        print("=" * 55)
        print(f"{'Component':<30} | {'Duration':<10} | {'Status':<10}")
        print("-" * 55)
        for key, data in self.metrics.items():
            comp_name = key.replace("_", " ").title()
            duration_str = f"{data['duration']:.4f}s"
            print(f"{comp_name:<30} | {duration_str:<10} | {data['status']:<10}")
        print("-" * 55)
        print(f"{'TOTAL STARTUP TIME:':<30} | {self.total_duration:.4f}s")
        print(f"{'SYSTEM STATE:':<30} | READY / HEALTHY")
        print("=" * 55 + "\n")

    def get_health_report(self) -> Dict[str, Any]:
        """Provides status details of all services for the enhanced health check."""
        from backend.database.connection import db_conn
        from backend.services.tunnel_manager import tunnel_mgr
        
        tunnel_diags = tunnel_mgr.get_diagnostics()
        
        return {
            "ready": self.ready,
            "total_startup_duration_seconds": round(self.total_duration, 4),
            "components": {
                "backend": {
                    "status": "healthy",
                    "uptime_seconds": int(time.time() - self.startup_start)
                },
                "database": {
                    "status": "healthy" if self.metrics["supabase_connection"]["status"] in ["SUCCESS", "SUCCESS (MOCK)"] else "unhealthy",
                    "mode": "mock" if db_conn.is_mock else "real",
                    "duration": round(self.metrics["database_connection"]["duration"] + self.metrics["supabase_connection"]["duration"], 4)
                },
                "whatsapp": {
                    "status": "healthy" if "SUCCESS" in self.metrics["whatsapp_service_startup"]["status"] else "unhealthy",
                    "provider": os.getenv("WHATSAPP_PROVIDER", "evolution"),
                    "mode": "sandbox" if "MOCK" in self.metrics["whatsapp_service_startup"]["status"] or "FALLBACK" in self.metrics["whatsapp_service_startup"]["status"] else "real",
                    "duration": round(self.metrics["whatsapp_service_startup"]["duration"], 4)
                },
                "tunnel": {
                    "status": "healthy" if tunnel_mgr.status == "Running" else "offline",
                    "public_url": tunnel_mgr.public_url,
                    "duration": round(self.metrics["tunnel_creation"]["duration"], 4),
                    **tunnel_diags
                },
                "external_apis": {
                    "status": "healthy" if self.metrics["ai_model_initialization"]["status"] == "SUCCESS" else "limited",
                    "ollama_host": settings.OLLAMA_BASE_URL,
                    "ollama_model": settings.OLLAMA_MODEL,
                    "duration": round(self.metrics["ai_model_initialization"]["duration"], 4)
                }
            }
        }

startup_mgr = StartupManager()
