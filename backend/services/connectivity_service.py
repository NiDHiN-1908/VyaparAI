# backend/services/connectivity_service.py
import os
import time
import logging
import traceback
import httpx
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
from backend.config import settings

logger = logging.getLogger("vyaparai.services.connectivity")

class ConnectivityService:
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=5.0)

    async def request_with_retry(
        self, 
        method: str, 
        url: str, 
        retries: int = 3, 
        backoff_factor: float = 1.5,
        **kwargs
    ) -> httpx.Response:
        """
        Executes an HTTP request with detailed error logging (Requirement 8)
        and retry logic with exponential backoff (Requirement 9).
        """
        last_exception = None
        current_delay = 1.0
        
        for attempt in range(1, retries + 1):
            try:
                start_time = time.time()
                logger.info(f"[HTTP REQUEST] Attempt {attempt}/{retries} - {method} {url}")
                
                response = await self.http_client.request(method, url, **kwargs)
                
                # Success
                duration = time.time() - start_time
                logger.info(f"[HTTP SUCCESS] {method} {url} - Status: {response.status_code} ({duration:.2f}s)")
                return response
                
            except httpx.TimeoutException as te:
                duration = time.time() - start_time
                last_exception = te
                stack_trace = traceback.format_exc()
                logger.error(
                    f"[TIMEOUT ERROR] Request failed:\n"
                    f"  URL: {url}\n"
                    f"  Method: {method}\n"
                    f"  Status: TIMEOUT\n"
                    f"  Timeout Duration: {duration:.2f}s (configured limit: {kwargs.get('timeout', 5.0)}s)\n"
                    f"  Stack Trace:\n{stack_trace}"
                )
            except Exception as e:
                duration = time.time() - start_time
                last_exception = e
                stack_trace = traceback.format_exc()
                logger.error(
                    f"[CONNECTION ERROR] Request failed:\n"
                    f"  URL: {url}\n"
                    f"  Method: {method}\n"
                    f"  Status: ERROR\n"
                    f"  Duration: {duration:.2f}s\n"
                    f"  Error: {str(e)}\n"
                    f"  Stack Trace:\n{stack_trace}"
                )

            if attempt < retries:
                logger.warning(f"Temporary network issue. Retrying in {current_delay:.2f}s...")
                await time.sleep(current_delay)
                current_delay *= backoff_factor
                
        raise last_exception

    async def get_active_ngrok_url(self) -> Optional[str]:
        """
        Checks if the local ngrok client is running and retrieves the active public URL.
        (Requirement 4 & 5)
        """
        # Always reload environment variables on check to load fresh PUBLIC_URL changes
        load_dotenv(override=True)
        ngrok_api_url = "http://127.0.0.1:4040/api/tunnels"
        try:
            # We use a short timeout to check if ngrok dashboard is active
            res = await self.http_client.get(ngrok_api_url, timeout=1.0)
            if res.status_code == 200:
                data = res.json()
                tunnels = data.get("tunnels", [])
                for tunnel in tunnels:
                    public_url = tunnel.get("public_url")
                    proto = tunnel.get("proto")
                    # Prefer HTTPS tunnel pointing to port 8000
                    if public_url and (proto == "https" or public_url.startswith("https:")):
                        return public_url
                # Fallback to any tunnel
                if tunnels:
                    return tunnels[0].get("public_url")
        except Exception:
            # Local ngrok API not responding / not running
            pass
            
        # Fallback: Check if our managed tunnel_mgr is active and has a public URL
        from backend.services.tunnel_manager import tunnel_mgr
        if tunnel_mgr.status == "Running" and tunnel_mgr.public_url:
            return tunnel_mgr.public_url
            
        return None

    async def analyze_ngrok_status(self) -> Dict[str, Any]:
        """
        Detailed connectivity analysis of the active public tunnel.
        """
        load_dotenv(override=True)
        active_url = await self.get_active_ngrok_url()
        configured_url = settings.PUBLIC_URL or os.getenv("PUBLIC_URL")
        
        status = "offline"
        message = "Public tunnel (ngrok or localhost.run) is not active. Please start your tunnel."
        
        if active_url:
            status = "online"
            if configured_url == active_url:
                message = f"Public tunnel is active and fully synchronized: {active_url}"
            else:
                status = "out_of_sync"
                message = (
                    f"Active tunnel detected at {active_url}, but the application config is using "
                    f"an outdated URL: {configured_url}. Synchronization required."
                )
        elif configured_url:
            # Local tunnel isn't running, check if the configured public URL is reachable externally
            # (In case it's a remote ngrok instance or a custom production domain)
            try:
                # Ping the public URL health check
                test_url = f"{configured_url.rstrip('/')}/"
                res = await self.http_client.get(test_url, timeout=2.0)
                status = "online"
                message = f"Configured public URL is reachable: {configured_url}"
            except Exception:
                status = "unreachable"
                message = f"Configured public URL is completely unreachable: {configured_url}. Ensure your tunnel/domain is online."
                
        return {
            "status": status,
            "configured_url": configured_url,
            "active_url": active_url,
            "message": message
        }

    async def check_evolution_api(self) -> Dict[str, Any]:
        """
        Checks connectivity to the WhatsApp Evolution API gateway.
        """
        evo_url = os.getenv("EVOLUTION_API_URL") or "http://localhost:8080"
        evo_key = os.getenv("EVOLUTION_API_KEY")
        
        if not evo_url:
            return {"status": "disabled", "message": "Evolution API configuration url is not set."}
            
        try:
            headers = {"apikey": evo_key or ""}
            # Fetch simple instance list to check auth & connectivity
            res = await self.http_client.get(f"{evo_url.rstrip('/')}/instance/fetchInstances", headers=headers, timeout=2.0)
            if res.status_code == 200:
                return {
                    "status": "online",
                    "url": evo_url,
                    "message": f"Evolution API is active and responded successfully (Status {res.status_code})."
                }
            return {
                "status": "error",
                "url": evo_url,
                "message": f"Evolution API returned error code {res.status_code}: {res.text}"
            }
        except Exception as e:
            return {
                "status": "offline",
                "url": evo_url,
                "message": f"Could not connect to Evolution API at {evo_url}. Check if the Docker container is running. Error: {str(e)}"
            }

    async def check_supabase(self) -> Dict[str, Any]:
        """
        Checks connectivity to the Supabase Database.
        """
        from backend.database.connection import db_conn
        if db_conn.is_mock:
            return {
                "status": "mock",
                "message": "Running in Mock/In-Memory database mode. Local database requests are always online."
            }
            
        url = settings.SUPABASE_URL
        try:
            # Simple metadata query to confirm connection
            res = await self.http_client.get(f"{url}/rest/v1/", headers={"apikey": settings.SUPABASE_KEY}, timeout=2.0)
            if res.status_code in [200, 404, 401]: # Rest API root responses
                return {
                    "status": "online",
                    "url": url,
                    "message": "Supabase database Rest API is connected and responding."
                }
            return {
                "status": "offline",
                "url": url,
                "message": f"Supabase database returned error code {res.status_code}"
            }
        except Exception as e:
            return {
                "status": "offline",
                "url": url,
                "message": f"Failed to connect to Supabase: {str(e)}"
            }

    async def perform_full_connectivity_analysis(self) -> Dict[str, Any]:
        """
        Executes health checks across all critical system services.
        (Requirement 11)
        """
        ngrok_report = await self.analyze_ngrok_status()
        evolution_report = await self.check_evolution_api()
        supabase_report = await self.check_supabase()
        
        # Verify self-reachability
        self_status = "online"
        self_message = "FastAPI server is running locally on port 8000."
        try:
            await self.http_client.get("http://127.0.0.1:8000/docs", timeout=1.0)
        except Exception:
            self_status = "offline"
            self_message = "FastAPI server is not responding to local requests."

        # Overall status resolution
        is_healthy = (
            ngrok_report["status"] in ["online", "out_of_sync"] and 
            evolution_report["status"] in ["online", "disabled"] and 
            supabase_report["status"] in ["online", "mock"] and
            self_status == "online"
        )
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "self": {"status": self_status, "message": self_message},
            "ngrok": ngrok_report,
            "evolution_api": evolution_report,
            "supabase": supabase_report
        }

connectivity_svc = ConnectivityService()
