import os
import re
import sys
import time
import subprocess

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

def main():
    print("===================================================")
    print("        VyaparAI Public Tunnel Launcher")
    print("       --- Starting localhost.run tunnel ---")
    print("===================================================")
    
    ssh_cmd = [
        "ssh", 
        "-R", "80:127.0.0.1:8000", 
        "-o", "StrictHostKeyChecking=no", 
        "-o", "UserKnownHostsFile=NUL", 
        "nokey@localhost.run"
    ]
    
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
        print(f"===================================================\n")
        
        # Update .env file
        update_env_file(url_found)
        print("\nKeep this window open to maintain the active public tunnel link.")
        print("To stop the tunnel, press Ctrl+C or close this window.\n")
        
        # Keep the process running
        proc.wait()
        
    except KeyboardInterrupt:
        print("\nShutting down tunnel...")
        if 'proc' in locals():
            proc.terminate()
    except Exception as e:
        print(f"\nError running SSH tunnel: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
