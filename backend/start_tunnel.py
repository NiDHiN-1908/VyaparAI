import os
import re
import sys
import time
import subprocess

# Ensure standard Windows system directories are in the PATH (Requirement 7 & 11)
if os.name == 'nt':
    sys_paths = [
        r"C:\Windows\System32",
        r"C:\Windows",
        r"C:\Windows\System32\Wbem",
        r"C:\Windows\System32\WindowsPowerShell\v1.0"
    ]
    current_path = os.environ.get("PATH", "")
    for p in sys_paths:
        if p.lower() not in current_path.lower():
            current_path = p + os.pathsep + current_path
    os.environ["PATH"] = current_path

def update_env_file(url):
    # Locate the .env file in the project root (parent directory of backend)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.abspath(os.path.join(current_dir, "../.env"))
    
    if not os.path.exists(env_path):
        # Fallback to current directory
        env_path = os.path.join(current_dir, ".env")
        
    if not os.path.exists(env_path):
        print(f"Error: Could not locate .env file (looked in root and backend/)")
        return False
        
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Check if PUBLIC_URL config line exists
        pattern = r"^(PUBLIC_URL\s*=\s*)(.*)$"
        if re.search(pattern, content, re.MULTILINE):
            new_content = re.sub(pattern, f"PUBLIC_URL={url}", content, flags=re.MULTILINE)
        else:
            new_content = content.rstrip() + f"\nPUBLIC_URL={url}\n"
            
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        print(f"Success: Updated .env with PUBLIC_URL={url}")
        return True
    except Exception as e:
        print(f"Error writing to .env file: {e}")
        return False

def run_pre_tunnel_checks(port=8000):
    import socket
    import urllib.request
    
    print("\n[Pre-tunnel Checks] Auditing local backend connectivity...")
    
    # 1. Check if port is listening
    backend_listening = False
    for attempt in range(1, 11):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                backend_listening = True
                print(f"  [OK] Local port {port} is active and listening.")
                break
        print(f"  [*] Port {port} is offline. Waiting for backend to boot (Attempt {attempt}/10)...")
        time.sleep(1.0)
        
    if not backend_listening:
        print(f"  [ERROR] Port {port} is still offline. The backend server must be running before forwarding!")
        print("  Please check uvicorn logs for errors or run start_all.bat.")
        return False
        
    # 2. Check if webhook and health routes are accessible
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/health",
            headers={"User-Agent": "VyaparAI-Tunnel-Precheck"}
        )
        with urllib.request.urlopen(req, timeout=2.0) as res:
            if res.status == 200:
                print("  [OK] Health-check route /health is accessible.")
            else:
                print(f"  [WARNING] /health returned unexpected status code {res.status}.")
    except Exception as e:
        print(f"  [WARNING] Failed to query /health route: {e}")
        
    try:
        req_post = urllib.request.Request(
            f"http://127.0.0.1:{port}/webhooks/whatsapp",
            data=b'{"event":"ping"}',
            headers={"Content-Type": "application/json", "User-Agent": "VyaparAI-Tunnel-Precheck"}
        )
        with urllib.request.urlopen(req_post, timeout=2.0) as res:
            if res.status == 200:
                print("  [OK] Webhook route /webhooks/whatsapp is accessible.")
            else:
                print(f"  [WARNING] /webhooks/whatsapp returned status code {res.status}.")
    except Exception as e:
        print(f"  [WARNING] Webhook route /webhooks/whatsapp check failed: {e}")
        
    return True

def kill_orphaned_tunnel_processes():
    import subprocess
    import json
    print("[Tunnel Cleanup] Auditing and terminating orphaned localhost.run tunnels...")
    try:
        cmd = "powershell -NoProfile -Command \"Get-CimInstance Win32_Process -Filter \\\"name='ssh.exe'\\\" | Select-Object ProcessId, CommandLine | ConvertTo-Json\""
        out = subprocess.check_output(cmd, shell=True, text=True).strip()
        killed_count = 0
        if out:
            data = json.loads(out)
            processes = data if isinstance(data, list) else [data]
            for proc in processes:
                cmdline = proc.get("CommandLine", "")
                pid = proc.get("ProcessId")
                if cmdline and "localhost.run" in cmdline and pid:
                    subprocess.run(f"taskkill /f /pid {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"  [OK] Terminated orphaned tunnel process (PID {pid}).")
                    killed_count += 1
        if killed_count == 0:
            print("  [OK] No orphaned tunnels detected.")
    except Exception as e:
        print(f"  [!] Process cleanup warning: {e}")


def start_ipv6_loopback_proxy(port=8000):
    import socket
    import threading
    def proxy_worker():
        try:
            # Bind to IPv6 loopback
            server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("::1", port))
            server.listen(10)
            while True:
                client_sock, addr = server.accept()
                # Forward to IPv4 loopback
                remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    remote_sock.connect(("127.0.0.1", port))
                    
                    def pipe(src, dst):
                        try:
                            while True:
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
        except Exception:
            pass # Proxy couldn't start or already in use
            
    threading.Thread(target=proxy_worker, daemon=True).start()


def main():
    # Resolve backend port from env or defaults first to pass to proxy
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.abspath(os.path.join(current_dir, "../.env"))
    if not os.path.exists(env_path):
        env_path = os.path.join(current_dir, ".env")
    port = 8000
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            match_port = re.search(r"^PORT\s*=\s*(\d+)", content, re.MULTILINE)
            if match_port:
                port = int(match_port.group(1))
        except Exception:
            pass

    # Start the IPv6 loopback proxy to resolve Windows OpenSSH localhost binding issues (Requirement 1 & 2)
    start_ipv6_loopback_proxy(port)

    # 1. Check if a permanent/user-configured PUBLIC_URL already exists in .env
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            match = re.search(r"^PUBLIC_URL\s*=\s*(https?://[^\s]+)", content, re.MULTILINE)
            if match:
                url = match.group(1)
                # If the URL is NOT a localhost.run URL (e.g. contains ngrok or custom domain)
                if "lhr.life" not in url and "lhr.rocks" not in url:
                    print("===================================================")
                    print("        VyaparAI Public Tunnel Launcher")
                    print("===================================================")
                    print(f"Permanent PUBLIC_URL is configured: {url}")
                    print("Skipping automatic localhost.run tunnel startup.\n")
                    print("Make sure your custom tunnel is running in the background!")
                    print("===================================================\n")
                    time.sleep(2)
                    sys.exit(0)
        except Exception as e:
            print(f"Warning reading .env for existing PUBLIC_URL: {e}")

    # Terminate any stale localhost.run ssh clients (Requirement 8)
    kill_orphaned_tunnel_processes()

    # Perform pre-tunnel checks (Requirement 6)
    if not run_pre_tunnel_checks(port):
        sys.exit(1)

    ssh_cmd = [
        "ssh", 
        "-R", f"80:localhost:{port}", 
        "-o", "StrictHostKeyChecking=no", 
        "-o", "UserKnownHostsFile=NUL", 
        "localhost.run"
    ]
    
    print("===================================================")
    print("        VyaparAI Public Tunnel Launcher")
    print("===================================================")
    print(f"[LOG] Backend Host Binding : 0.0.0.0")
    print(f"[LOG] Backend Listening Port: {port}")
    print(f"[LOG] Tunnel Forwarding Target: localhost:{port}")
    print(f"[LOG] Tunnel Startup Command  : {' '.join(ssh_cmd)}")
    print("===================================================")
    
    try:
        proc = subprocess.Popen(
            ssh_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            bufsize=1
        )
        
        url_found = None
        # Read SSH output line by line to capture the tunnel domain
        for _ in range(40):
            line = proc.stdout.readline()
            if not line:
                break
            
            # Print output directly so user can see it
            line_str = line.strip()
            if line_str:
                print(f"[Tunnel] {line_str}")
            
            # Check for domain patterns like baf727b8fbe7cf.lhr.life or https://...
            match = re.search(r"https?://[a-zA-Z0-9\-\.]+\.lhr\.(life|rocks|run)", line)
            if match:
                url_found = match.group(0)
                break
                
            # Alternate match (sometimes domain is printed without http protocol prefix)
            match_direct = re.search(r"([a-zA-Z0-9\-]+\.lhr\.(life|rocks|run))", line)
            if match_direct:
                url_found = "https://" + match_direct.group(1)
                break
                
            time.sleep(0.05)
            
        if not url_found:
            print("\nError: Could not parse tunnel URL from localhost.run. Please verify your SSH connection.")
            proc.terminate()
            sys.exit(1)
            
        print(f"\n===================================================")
        print(f"Tunnel Established successfully!")
        print(f"Public URL: {url_found}")
        print(f"[LOG] Public Tunnel URL     : {url_found}")
        print(f"===================================================\n")
        
        # Update .env file
        update_env_file(url_found)
        
        # Automatic validation immediately after tunnel creation (Requirement 4 & 5)
        print("\n[Validation] Running post-startup connectivity checks...")
        time.sleep(2.0) # Allow tunnel a brief moment to stabilize on the provider side
        
        local_ok = False
        public_ok = False
        local_status = None
        public_status = None
        
        # Test local
        try:
            import urllib.request
            local_req = urllib.request.Request(
                f"http://localhost:{port}/health",
                headers={"User-Agent": "VyaparAI-Tunnel-Validator"}
            )
            with urllib.request.urlopen(local_req, timeout=3.0) as res:
                local_status = res.status
                if res.status == 200:
                    local_ok = True
                    print(f"  [OK] Local health check: HTTP {res.status} OK")
                else:
                    print(f"  [ERROR] Local health check returned HTTP {res.status}")
        except Exception as e:
            print(f"  [ERROR] Local health check failed: {e}")
            
        # Test public
        try:
            import urllib.request
            import urllib.error
            public_req = urllib.request.Request(
                f"{url_found}/health",
                headers={"User-Agent": "VyaparAI-Tunnel-Validator"}
            )
            with urllib.request.urlopen(public_req, timeout=5.0) as res:
                public_status = res.status
                if res.status == 200:
                    public_ok = True
                    print(f"  [OK] Public health check: HTTP {res.status} OK")
                else:
                    print(f"  [ERROR] Public health check returned HTTP {res.status}")
        except Exception as e:
            import urllib.error
            if isinstance(e, urllib.error.HTTPError):
                public_status = e.code
                print(f"  [ERROR] Public health check failed with HTTP {e.code}")
            else:
                print(f"  [ERROR] Public health check failed: {e}")
                
        # Compare and print result
        if local_ok and not public_ok:
            print("\n" + "=" * 80)
            print("  Backend is healthy locally, but the tunnel is not forwarding requests correctly.")
            print(f"  Local Status: {local_status or 'Error'}, Public Status: {public_status or 'Unreachable'}")
            print("=" * 80 + "\n")
        elif local_ok and public_ok:
            print("\n" + "=" * 80)
            print("  SUCCESS: Tunnel is online and forwarding traffic successfully!")
            print("=" * 80 + "\n")
        else:
            print("\n" + "=" * 80)
            print("  ERROR: Connectivity diagnostics failed. Check host binding or port conflicts.")
            print("=" * 80 + "\n")
        print("\nKeep this window open to maintain the active public tunnel link.")
        print("To stop the tunnel, press Ctrl+C or close this window.\n")
        
        # Keep the process running and read its stdout continuously to prevent buffer fill-up blocks (Requirement 7)
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str:
                print(f"[Tunnel] {line_str}")
                
                # Check if a new domain was generated during reconnect
                match = re.search(r"https?://[a-zA-Z0-9\-\.]+\.lhr\.(life|rocks|run)", line)
                new_url = None
                if match:
                    new_url = match.group(0)
                else:
                    match_direct = re.search(r"([a-zA-Z0-9\-]+\.lhr\.(life|rocks|run))", line)
                    if match_direct:
                        new_url = "https://" + match_direct.group(1)
                
                if new_url and new_url != url_found:
                    print(f"\n===================================================")
                    print(f"[LOG] Tunnel Reconnected / New Domain Detected!")
                    print(f"  Old URL: {url_found}")
                    print(f"  New URL: {new_url}")
                    print(f"===================================================\n")
                    url_found = new_url
                    update_env_file(url_found)
        
    except KeyboardInterrupt:
        print("\nShutting down tunnel...")
        if 'proc' in locals():
            proc.terminate()
    except Exception as e:
        print(f"\nError running SSH tunnel: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
