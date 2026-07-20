# backend/services/tunnel_manager.py
import time
import os
import sys
import re
import subprocess
import threading
import socket
import httpx
import logging
import traceback
import shutil
import queue
import collections
from typing import Dict, Any, Optional
from backend.config import settings
from backend.services.supabase_service import supabase_svc

logger = logging.getLogger("vyaparai.tunnel_manager")

ERROR_FRIENDLY_MESSAGES = {
    "ssh_executable_not_found": "SSH executable not found. Please install OpenSSH Client on Windows (run: Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0 in elevated PowerShell).",
    "ssh_authentication_failed": "SSH authentication failed. The public key authentication with nokey@localhost.run was rejected.",
    "localhost_run_connection_refused": "Localhost.run connection refused. The remote service might be experiencing high latency or rate-limiting.",
    "ssh_process_crashed": "SSH process exited unexpectedly. Connection closed by remote tunnel provider.",
    "tunnel_provider_unreachable": "Tunnel provider unreachable. Check internet connectivity and outgoing port 22 access.",
    "port_forwarding_failed": "Port forwarding failed. Remote server was unable to bind tunnel port.",
    "backend_unreachable": "Backend unreachable. Local FastAPI health endpoint is not responding.",
    "network_timeout": "Network timeout occurred while validating public tunnel connection.",
    "firewall_blocked": "Firewall blocked SSH connection. Ensure port 22 outgoing traffic is allowed.",
    "tunnel_url_missing": "Tunnel URL could not be parsed from localhost.run output within 90 seconds.",
    "webhook_endpoint_unavailable": "Webhook endpoint unavailable. The backend /webhooks/whatsapp route returned an error code."
}

def enqueue_output(out, q):
    """Worker function to read stdout lines in a non-blocking daemon thread."""
    try:
        for line in iter(out.readline, ''):
            q.put(line)
        out.close()
    except Exception:
        pass

class TunnelManager:
    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        self.proxy_thread: Optional[threading.Thread] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Diagnostics metrics (Requirement 5)
        self.status = "Stopped"  # Running / Stopped
        self.start_time: Optional[float] = None
        self.last_success_health_check: Optional[str] = None
        self.public_url: Optional[str] = None
        self.provider = "localhost.run"
        self.restart_count = 0
        self.last_restart_reason: Optional[str] = None
        self.last_crash_reason: Optional[str] = None
        self.error_reason: Optional[str] = None
        self.port = int(os.getenv("PORT", 8000))
        self.ssh_version = "Unknown"
        self.is_reused = False
        self.stdout_buffer = collections.deque(maxlen=50)
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        # Log path
        self.log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "start_tunnel_spawn.log"))

    def log_tunnel_message(self, message: str):
        """Append a log message to the tunnel spawn log file (Requirement 8)."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            logger.error(f"Failed to write to tunnel log: {e}")

    def verify_ssh_installed(self) -> bool:
        """Verify that the SSH client is installed on the host and retrieve version (Requirement 3)."""
        ssh_path = shutil.which("ssh")
        if not ssh_path:
            self.error_reason = "ssh_executable_not_found"
            self.ssh_version = "Not Installed"
            self.log_tunnel_message("[ERROR] SSH executable not found in system PATH.")
            return False
            
        try:
            # ssh -V prints version to stderr
            res = subprocess.run(["ssh", "-V"], capture_output=True, text=True, timeout=3.0)
            self.ssh_version = (res.stderr or res.stdout or "").strip()
            self.log_tunnel_message(f"[Verify] SSH version detected: {self.ssh_version}")
            return True
        except Exception as e:
            self.error_reason = "ssh_executable_not_found"
            self.ssh_version = f"Error: {e}"
            self.log_tunnel_message(f"[ERROR] Failed to query SSH version: {e}")
            return False

    def classify_error_reason(self, exit_code: Optional[int]):
        """Map process exit state and output messages to friendly codes (Requirement 2 & 8)."""
        if exit_code is not None:
            self.error_reason = "ssh_process_crashed"
            # Parse stderr buffer for common signatures
            buffer_str = "\n".join(self.stdout_buffer).lower()
            if "permission denied" in buffer_str:
                self.error_reason = "ssh_authentication_failed"
            elif "connection refused" in buffer_str:
                self.error_reason = "localhost_run_connection_refused"
            elif "reset by peer" in buffer_str:
                self.error_reason = "localhost_run_connection_refused"
            elif "host key verification failed" in buffer_str:
                self.error_reason = "ssh_authentication_failed"
        else:
            self.error_reason = "tunnel_url_missing"

    def cleanup_failed_attempt(self):
        """Safely terminate the active subprocess on a failed attempt (Requirement 5)."""
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

    def validate_public_endpoint(self, url: str) -> bool:
        """Confirm the public URL and its webhooks route respond with HTTP 200 (Requirement 4)."""
        health_url = f"{url.rstrip('/')}/health"
        webhook_url = f"{url.rstrip('/')}/webhooks/whatsapp"
        
        # Try up to 3 times to allow DNS propagation
        for i in range(3):
            self.log_tunnel_message(f"[Validation] Pinging public endpoints (Attempt {i+1}/3)...")
            try:
                with httpx.Client(timeout=10.0) as client:
                    # Ping /health
                    res_health = client.get(health_url)
                    if res_health.status_code != 200:
                        self.error_reason = "Invalid reverse proxy configuration"
                        time.sleep(2.0)
                        continue
                        
                    # Ping /webhooks/whatsapp
                    res_webhook = client.post(webhook_url, json={"event": "ping"}, headers={"Content-Type": "application/json"})
                    if res_webhook.status_code not in [200, 201, 202, 400, 422]:
                        self.error_reason = "Invalid reverse proxy configuration"
                        time.sleep(2.0)
                        continue
                        
                    self.log_tunnel_message("[Validation] Public health checks verified successfully!")
                    return True
            except httpx.ConnectTimeout:
                self.error_reason = "Request never reached backend"
            except httpx.ConnectError:
                self.error_reason = "Request never reached backend"
            except httpx.RemoteProtocolError:
                self.error_reason = "Tunnel closed connection before forwarding"
            except Exception as e:
                ex_str = str(e).lower()
                if "ssl" in ex_str or "handshake" in ex_str:
                    self.error_reason = "TLS handshake failed"
                elif "disconnected" in ex_str or "connection closed" in ex_str or "closed connection" in ex_str:
                    self.error_reason = "Backend closed connection unexpectedly"
                else:
                    self.error_reason = "Request never reached backend"
            time.sleep(2.0)
            
        return False

    def kill_orphaned_tunnels(self):
        """Terminate any stale localhost.run ssh clients (Requirement 8)."""
        self.log_tunnel_message("[Tunnel Cleanup] Auditing and terminating orphaned localhost.run and Ngrok tunnels...")
        try:
            if sys.platform == "win32":
                import os
                my_pid = os.getpid()
                parent_pid = os.getppid()
                # Kill stale ssh processes and any duplicate process listening on our port (excluding current and parent)
                cmd = [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    f"Get-CimInstance Win32_Process -Filter \"Name='ssh.exe'\" -ErrorAction SilentlyContinue | Where-Object {{ $_.CommandLine -like '*localhost.run*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}; Get-CimInstance Win32_Process -Filter \"Name='ngrok.exe'\" -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}; $conn = Get-NetTCPConnection -LocalPort {self.port} -State Listen -ErrorAction SilentlyContinue; if ($conn) {{ foreach ($c in $conn) {{ $p = $c.OwningProcess; if ($p -and $p -ne {my_pid} -and $p -ne {parent_pid}) {{ Stop-Process -Id $p -Force }} }} }}"
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["pkill", "-f", "localhost.run"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["pkill", "-f", "ngrok"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log_tunnel_message("  [OK] Stale SSH, Ngrok, and duplicate server processes cleaned up.")
        except Exception as e:
            self.log_tunnel_message(f"  [Warning] Stale process cleanup encountered error: {e}")


    def start_ipv6_loopback_proxy(self):
        """Spawns a local proxy between IPv6 loopback (::1) and IPv4 loopback (127.0.0.1) for Windows SSH issues."""
        def proxy_worker():
            try:
                # Bind proxy on IPv6 loopback
                proxy_sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                proxy_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                proxy_sock.bind(("::1", self.port))
                proxy_sock.listen(5)
                self.log_tunnel_message(f"[Proxy] Loopback IPv6 proxy listening on [::1]:{self.port}")
                
                while not self.stop_event.is_set():
                    proxy_sock.settimeout(1.0)
                    try:
                        client_sock, _ = proxy_sock.accept()
                    except socket.timeout:
                        continue
                    except Exception:
                        break
                    
                    try:
                        # Direct to IPv4 localhost backend
                        remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        remote_sock.connect(("127.0.0.1", self.port))
                        
                        def pipe(src, dst):
                            try:
                                while not self.stop_event.is_set():
                                    data = src.recv(4096)
                                    if not data:
                                        break
                                    dst.sendall(data)
                            except Exception:
                                pass
                            finally:
                                src.close()
                                dst.close()
                                
                        threading.Thread(target=pipe, args=(client_sock, remote_sock), daemon=True).start()
                        threading.Thread(target=pipe, args=(remote_sock, client_sock), daemon=True).start()
                    except Exception:
                        client_sock.close()
            except Exception as e:
                self.log_tunnel_message(f"[Proxy ERROR] Proxy worker failed: {e}")
                
        self.proxy_thread = threading.Thread(target=proxy_worker, daemon=True)
        self.proxy_thread.start()

    def start_tunnel(self) -> bool:
        """Starts the public tunnel process and captures the public URL (Requirement 2 & 3)."""
        with self.lock:
            self.status = "Starting"
            self.is_reused = False
            
            # Check if there is an active Ngrok tunnel running on the system first
            try:
                with httpx.Client(timeout=2.0) as client:
                    res = client.get("http://127.0.0.1:4040/api/tunnels")
                    if res.status_code == 200:
                        data = res.json()
                        tunnels = data.get("tunnels", [])
                        for t in tunnels:
                            p_url = t.get("public_url")
                            config_addr = t.get("config", {}).get("addr", "")
                            if p_url and (str(self.port) in config_addr or "localhost" in config_addr or "127.0.0.1" in config_addr):
                                self.public_url = p_url
                                self.status = "Running"
                                self.is_reused = True
                                self.provider = "ngrok"
                                self.error_reason = None
                                self.log_tunnel_message(f"[Startup] Detected active Ngrok tunnel from system! Reusing URL: {self.public_url}")
                                self.refresh_webhook_urls(self.public_url)
                                return True
            except Exception:
                pass

            # Check if there is another existing healthy tunnel we can reuse
            existing_url = os.getenv("PUBLIC_URL") or settings.PUBLIC_URL
            if existing_url and not existing_url.startswith("http://localhost") and not existing_url.startswith("http://127.0.0.1"):
                self.log_tunnel_message(f"[Startup] Checking if existing public tunnel {existing_url} is active...")
                try:
                    local_listening = False
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1.0)
                        if s.connect_ex(("127.0.0.1", self.port)) == 0:
                            local_listening = True
                    
                    if local_listening:
                        health_url = f"{existing_url.rstrip('/')}/health"
                        with httpx.Client(timeout=3.0) as client:
                            res = client.get(health_url)
                            if res.status_code == 200:
                                self.public_url = existing_url
                                self.status = "Running"
                                self.is_reused = True
                                self.error_reason = None
                                self.log_tunnel_message(f"[Startup] Existing public tunnel is healthy! Reusing URL: {self.public_url}")
                                self.refresh_webhook_urls(self.public_url)
                                return True
                except Exception as e:
                    self.log_tunnel_message(f"[Startup] Existing tunnel check failed or unreachable: {e}. Proceeding to spawn a new one.")

            # Try starting ngrok tunnel first if ngrok is installed/available
            ngrok_avail = shutil.which("ngrok") or os.path.exists(os.path.expandvars(r"%APPDATA%\npm\ngrok.cmd"))
            if ngrok_avail:
                self.log_tunnel_message("[Startup] Ngrok is available on the system. Launching Ngrok as primary tunnel...")
                if self.start_ngrok_tunnel():
                    return True
                self.log_tunnel_message("[Startup] Ngrok launch failed. Falling back to localhost.run...")

            self.provider = "localhost.run"
            
            # 1. Verification checks
            if not self.verify_ssh_installed():
                self.status = "Stopped"
                return False

            self.kill_orphaned_tunnels()
            
            # Note: We bind to 127.0.0.1 directly to avoid IPv6 localhost resolution conflicts,
            # which renders loopback proxy starting unnecessary.
            ssh_cmd = [
                "ssh", 
                "-v",
                "-R", f"80:127.0.0.1:{self.port}", 
                "-o", "StrictHostKeyChecking=no", 
                "-o", "UserKnownHostsFile=NUL", 
                "-o", "ServerAliveInterval=30",
                "-o", "GSSAPIAuthentication=no",
                "-o", "AddressFamily=inet",
                "nokey@localhost.run"
            ]
            
            self.log_tunnel_message(f"[Startup] Tunnel Command: {' '.join(ssh_cmd)}")
            
            try:
                self.proc = subprocess.Popen(
                    ssh_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                self.log_tunnel_message(f"[Startup] SSH process spawned with PID {self.proc.pid}")
                
                # Start non-blocking reader thread for stdout (Requirement 6 & 7)
                q = queue.Queue()
                t = threading.Thread(target=enqueue_output, args=(self.proc.stdout, q), daemon=True)
                t.start()
                
                # Parse public URL from stdout
                url_found = None
                start_wait = time.time()
                # Wait up to 90 seconds for public URL to be generated
                while time.time() - start_wait < 90:
                    if self.proc.poll() is not None:
                        break
                    
                    try:
                        line = q.get_nowait()
                    except queue.Empty:
                        time.sleep(0.1)
                        continue
                        
                    line_str = line.strip()
                    if line_str:
                        self.log_tunnel_message(f"[Tunnel Stdout] {line_str}")
                        
                    # Check for domain patterns like baf727b8fbe7cf.lhr.life or https://...
                    match = re.search(r"https?://[a-zA-Z0-9\-\.]+\.lhr\.(life|rocks|run)", line)
                    if match:
                        url_found = match.group(0)
                        break
                        
                    match_direct = re.search(r"([a-zA-Z0-9\-]+\.lhr\.(life|rocks|run))", line)
                    if match_direct:
                        url_found = "https://" + match_direct.group(1)
                        break
                    
                if not url_found:
                    poll_code = self.proc.poll()
                    self.log_tunnel_message(f"[ERROR] Could not parse tunnel URL from localhost.run. Exit code: {poll_code}. Initiating Ngrok fallback...")
                    self.cleanup_failed_attempt()
                    return self.start_ngrok_tunnel()
                    
                self.public_url = url_found
                self.start_time = time.time()
                self.status = "Running"
                self.error_reason = None
                self.log_tunnel_message(f"[Success] Tunnel Established! Public URL: {self.public_url}")
                
                # Validate the endpoint before committing to it!
                if not self.validate_public_endpoint(self.public_url):
                    self.log_tunnel_message("[Warning] localhost.run endpoint verification failed. Switching provider to Ngrok...")
                    self.cleanup_failed_attempt()
                    return self.start_ngrok_tunnel()

                # Update .env file
                self.update_env_file(self.public_url)
                
                # Refresh webhook URL in database & active modules
                self.refresh_webhook_urls(self.public_url)
                
                return True
                
            except Exception as e:
                self.log_tunnel_message(f"[ERROR] Exception during tunnel startup: {e}\n{traceback.format_exc()}. Switching to Ngrok...")
                self.cleanup_failed_attempt()
                return self.start_ngrok_tunnel()

    def start_ngrok_tunnel(self) -> bool:
        """Starts the public tunnel process using Ngrok and captures the public URL."""
        self.log_tunnel_message("[Ngrok Startup] Initiating fallback tunnel creation via Ngrok...")
        self.provider = "ngrok"
        self.kill_orphaned_tunnels()
        
        # Resolve ngrok path
        ngrok_path = shutil.which("ngrok")
        if not ngrok_path:
            # Try a sensible Windows default
            appdata_npm_ngrok = os.path.expandvars(r"%APPDATA%\npm\ngrok.cmd")
            if os.path.exists(appdata_npm_ngrok):
                ngrok_path = appdata_npm_ngrok
            else:
                self.error_reason = "Request never reached backend"
                self.log_tunnel_message("[ERROR] Ngrok executable not found in PATH or NPM directory.")
                return False
                
        # Check if we have a custom ngrok domain configured in env
        custom_domain = None
        env_url = os.getenv("PUBLIC_URL") or settings.PUBLIC_URL
        if env_url and "ngrok-free" in env_url:
            # Extract domain e.g. buffalo-scavenger-tantrum.ngrok-free.dev
            match = re.search(r"https?://([a-zA-Z0-9\-\.]+)", env_url)
            if match:
                custom_domain = match.group(1)

        # Command on Windows requires shell=True for .cmd file
        if custom_domain:
            cmd = f'"{ngrok_path}" http --domain={custom_domain} {self.port}'
            self.log_tunnel_message(f"[Ngrok Startup] Using custom domain: {custom_domain}")
        else:
            cmd = f'"{ngrok_path}" http {self.port}'
        self.log_tunnel_message(f"[Ngrok Startup] Command: {cmd}")
        
        try:
            self.proc = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.log_tunnel_message(f"[Ngrok Startup] Ngrok process spawned with PID {self.proc.pid}")
            
            # Wait up to 10 seconds for Ngrok to boot and tunnel URL to become available
            start_wait = time.time()
            url_found = None
            
            while time.time() - start_wait < 10:
                if self.proc.poll() is not None:
                    # process crashed
                    break
                    
                # Query local ngrok API to find URL
                try:
                    with httpx.Client(timeout=2.0) as client:
                        res = client.get("http://127.0.0.1:4040/api/tunnels")
                        if res.status_code == 200:
                            data = res.json()
                            tunnels = data.get("tunnels", [])
                            for t in tunnels:
                                p_url = t.get("public_url")
                                proto = t.get("proto")
                                if p_url and (proto == "https" or p_url.startswith("https:")):
                                    url_found = p_url
                                    break
                            if not url_found and tunnels:
                                url_found = tunnels[0].get("public_url")
                            if url_found:
                                break
                except Exception:
                    pass
                time.sleep(0.5)
                
            if not url_found:
                poll_code = self.proc.poll()
                self.log_tunnel_message(f"[ERROR] Could not parse tunnel URL from local Ngrok API. Exit code: {poll_code}")
                self.error_reason = "Request never reached backend"
                self.cleanup_failed_attempt()
                return False
                
            self.public_url = url_found
            self.start_time = time.time()
            self.status = "Running"
            self.error_reason = None
            self.log_tunnel_message(f"[Success] Ngrok Tunnel Established! Public URL: {self.public_url}")
            
            # Validate ngrok endpoint
            if not self.validate_public_endpoint(self.public_url):
                self.log_tunnel_message("[ERROR] Ngrok public endpoint validation failed.")
                self.cleanup_failed_attempt()
                return False

            # Update .env file
            self.update_env_file(self.public_url)
            
            # Refresh webhook URL in database & active modules
            self.refresh_webhook_urls(self.public_url)
            return True
            
        except Exception as e:
            self.log_tunnel_message(f"[ERROR] Exception during Ngrok startup: {e}\n{traceback.format_exc()}")
            self.error_reason = "Request never reached backend"
            self.cleanup_failed_attempt()
            return False
                


    def update_env_file(self, new_url: str):
        """Update `.env` file with the new PUBLIC_URL and reload environment variables (Requirement 2)."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))
        
        try:
            content = ""
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
            if "PUBLIC_URL" in content:
                # Replace existing URL
                content = re.sub(r"^PUBLIC_URL\s*=.*$", f"PUBLIC_URL={new_url}", content, flags=re.MULTILINE)
            else:
                # Append new URL
                content += f"\nPUBLIC_URL={new_url}\n"
                
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            # Reload dotenv
            from dotenv import load_dotenv
            load_dotenv(env_path, override=True)
            settings.PUBLIC_URL = new_url
            self.log_tunnel_message(f"[Config] Updated .env file and active settings with PUBLIC_URL={new_url}")
        except Exception as e:
            self.log_tunnel_message(f"[ERROR] Failed to update .env: {e}")

    def refresh_webhook_urls(self, new_url: str):
        """Refresh webhook URL for all instances in the database and provider (Requirement 2 & 7)."""
        self.log_tunnel_message("[Webhook Sync] Updating database and active WhatsApp instances...")
        try:
            public_webhook_url = f"{new_url.rstrip('/')}/webhooks/whatsapp"
            
            # Fetch all WhatsApp instances (Requirement 7)
            instances = supabase_svc._select_all("whatsapp_instances")
            updated_count = 0
            
            for inst in instances:
                instance_id = inst.get("id")
                instance_name = inst.get("instance_name")
                
                # 1. Update in Supabase DB
                supabase_svc.update_whatsapp_instance_webhook(instance_id, public_webhook_url)
                updated_count += 1
                
                # 2. Update active WhatsApp provider (Evolution API) webhook if connected
                try:
                    from backend.modules.whatsapp_module.instance_service import whatsapp_instance_svc
                    if whatsapp_instance_svc and inst.get("status") == "connected":
                        provider_webhook = f"{public_webhook_url}?instance={instance_name}"
                        # Fire and forget registration
                        threading.Thread(
                            target=lambda: asyncio_run_coroutine(
                                whatsapp_instance_svc.provider.register_webhook(instance_name, provider_webhook)
                            ),
                            daemon=True
                        ).start()
                except Exception as ex:
                    self.log_tunnel_message(f"  [Warning] Failed to update active webhook for '{instance_name}': {ex}")
                    
            self.log_tunnel_message(f"  [OK] Refreshed {updated_count} WhatsApp instances in database.")
            
            # Broadcast WebSocket event to notify clients (Requirement 7)
            try:
                from backend.modules.websocket_module import websocket_manager
                # Send text info to all connected web sockets for the default tenant
                threading.Thread(
                    target=lambda: asyncio_run_coroutine(
                        websocket_manager.broadcast_to_tenant(
                            tenant_id="00000000-0000-0000-0000-000000000000",
                            event_type="tunnel.updated",
                            data={
                                "public_url": new_url,
                                "webhook_url": public_webhook_url,
                                "message": f"Public tunnel updated to {new_url}. WhatsApp webhooks synchronized."
                            }
                        )
                    ),
                    daemon=True
                ).start()
            except Exception as e:
                logger.error(f"WebSocket tunnel update broadcast failed: {e}")
                
        except Exception as e:
            self.log_tunnel_message(f"[ERROR] Failed during webhook synchronization: {e}")

    def verify_tunnel_health(self) -> bool:
        """Ping health endpoints via the public URL to verify tunnel integrity (Requirement 4)."""
        if not self.public_url:
            self.error_reason = "Request never reached backend"
            return False
            
        try:
            # 1. Check local backend itself is running
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                if s.connect_ex(("127.0.0.1", self.port)) != 0:
                    self.error_reason = "Request never reached backend"
                    self.log_tunnel_message("[Health Check] Local backend server is not listening!")
                    return False

            # 2. Ping health endpoints through the public URL
            health_url = f"{self.public_url.rstrip('/')}/health"
            webhook_url = f"{self.public_url.rstrip('/')}/webhooks/whatsapp"
            
            with httpx.Client(timeout=15.0) as client:
                try:
                    res_health = client.get(health_url)
                    if res_health.status_code != 200:
                        self.error_reason = "Invalid reverse proxy configuration"
                        self.log_tunnel_message(f"[Health Check] Public health check returned status {res_health.status_code}")
                        return False
                except httpx.ConnectTimeout:
                    self.error_reason = "Request never reached backend"
                    self.log_tunnel_message("[Health Check] Public health check connection timed out.")
                    return False
                except httpx.ConnectError:
                    self.error_reason = "Request never reached backend"
                    self.log_tunnel_message("[Health Check] Public health check DNS resolution failure / Unreachable.")
                    return False
                except httpx.RemoteProtocolError:
                    self.error_reason = "Tunnel closed connection before forwarding"
                    self.log_tunnel_message("[Health Check] Public health check Remote Protocol Error / connection reset.")
                    return False
                except Exception as ex:
                    ex_str = str(ex).lower()
                    if "ssl" in ex_str or "handshake" in ex_str:
                        self.error_reason = "TLS handshake failed"
                    elif "disconnected" in ex_str or "connection closed" in ex_str or "closed connection" in ex_str:
                        self.error_reason = "Backend closed connection unexpectedly"
                    else:
                        self.error_reason = "Request never reached backend"
                    self.log_tunnel_message(f"[Health Check] Public health check failed: {ex}")
                    return False
                    
                # Ping WhatsApp webhook
                try:
                    res_webhook = client.post(webhook_url, json={"event": "ping"}, headers={"Content-Type": "application/json"})
                    if res_webhook.status_code not in [200, 201, 202, 400, 422]:
                        self.error_reason = "Invalid reverse proxy configuration"
                        self.log_tunnel_message(f"[Health Check] Public webhook endpoint returned status {res_webhook.status_code}")
                        return False
                except Exception as ex:
                    self.error_reason = "Request never reached backend"
                    self.log_tunnel_message(f"[Health Check] Public webhook ping failed: {ex}")
                    return False
                    
            self.last_success_health_check = time.strftime("%Y-%m-%d %H:%M:%S")
            return True
        except Exception as e:
            self.error_reason = "Request never reached backend"
            self.log_tunnel_message(f"[Health Check] Unexpected exception: {e}")
            return False

    def start_monitoring_loop(self):
        """Start the background thread that monitors SSH process and tests health (Requirement 1 & 4)."""
        def monitor_worker():
            self.log_tunnel_message("[Monitor] Starting 30-second tunnel health monitoring loop...")
            while not self.stop_event.is_set():
                # Sleep in increments so we can exit quickly on shutdown
                for _ in range(30):
                    if self.stop_event.is_set():
                        return
                    time.sleep(1.0)
                    
                # Skip checking if currently starting up to avoid race condition/killing (Requirement 2 & 9)
                if self.status == "Starting":
                    continue
                    
                # Perform check
                if self.is_reused:
                    ssh_alive = self.verify_tunnel_health()
                else:
                    ssh_alive = self.proc is not None and self.proc.poll() is None
                    
                if not ssh_alive:
                    self.log_tunnel_message("[Monitor] SSH Process is not running or public tunnel is offline!")
                    self.heal_tunnel("SSH tunnel process exited unexpectedly or public health check failed")
                elif self.status == "Running" and not self.is_reused:
                    # Only verify health if the tunnel has finished starting and is marked as Running and not verified above
                    health_ok = self.verify_tunnel_health()
                    if not health_ok:
                        self.log_tunnel_message(f"[Monitor] Health check failed: {self.error_reason}")
                        self.heal_tunnel(f"Health check failed: {self.error_reason}")
                        
        self.monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
        self.monitor_thread.start()

    def heal_tunnel(self, reason: str):
        """Automatically restarts the tunnel when a failure is detected (Requirement 2 & 9)."""
        self.log_tunnel_message(f"[Self-Healing] Triggering automatic tunnel recovery. Reason: {reason}")
        self.restart_count += 1
        self.last_restart_reason = reason
        self.status = "Stopped"
        
        # Safe termination of existing process
        with self.lock:
            if self.proc:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=2.0)
                except Exception:
                    try:
                        self.proc.kill()
                    except Exception:
                        pass
                self.proc = None
                
        # Launch a new one
        success = self.start_tunnel()
        if success:
            self.log_tunnel_message("[Self-Healing] Recovery successful!")
        else:
            self.log_tunnel_message("[Self-Healing ERROR] Recovery failed. Will retry on next monitor tick.")

    def shutdown(self):
        """Clean up all processes and threads on application exit."""
        self.log_tunnel_message("[Shutdown] Terminating tunnel and stopping threads...")
        self.stop_event.set()
        
        with self.lock:
            if self.proc:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=2.0)
                except Exception:
                    try:
                        self.proc.kill()
                    except Exception:
                        pass
                self.proc = None
                
        self.kill_orphaned_tunnels()
        self.status = "Stopped"

    def get_diagnostics(self) -> Dict[str, Any]:
        """Provides a detailed diagnostic report for display and debugging (Requirement 5 & 6)."""
        uptime = 0.0
        if self.status == "Running" and self.start_time:
            uptime = time.time() - self.start_time
            
        return {
            "status": self.status,
            "ssh_process_status": "Running" if (self.proc is not None and self.proc.poll() is None) or (self.status == "Running" and self.is_reused) else "Stopped",
            "tunnel_start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time)) if self.start_time else None,
            "tunnel_uptime_seconds": int(uptime),
            "last_success_health_check": self.last_success_health_check,
            "current_public_url": self.public_url,
            "tunnel_provider": self.provider,
            "restart_count": self.restart_count,
            "last_restart_reason": self.last_restart_reason,
            "error_reason": self.error_reason,
            "configured_port": self.port
        }

# Global singleton manager instance
tunnel_mgr = TunnelManager()

def asyncio_run_coroutine(coro):
    """Helper to run async coroutines from sync daemon threads."""
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)
        loop.close()
    except Exception as e:
        logger.error(f"Error running coroutine: {e}")
