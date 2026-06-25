# diagnose_whatsapp.py
import os
import asyncio
import httpx
from dotenv import load_dotenv

# Load .env file
load_dotenv()

async def main():
    api_url = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
    api_key = os.getenv("EVOLUTION_API_KEY", "vyaparai_key_secret")
    app_url = os.getenv("APP_BASE_URL", "http://host.docker.internal:8000")
    
    print("\n=============================================")
    print("   VYAPARAI WHATSAPP INTEGRATION DIAGNOSTICS")
    print("=============================================")
    print(f"Loaded Configuration:")
    print(f"  - EVOLUTION_API_URL: {api_url}")
    print(f"  - EVOLUTION_API_KEY: {api_key}")
    print(f"  - APP_BASE_URL: {app_url}")
    print("")
    
    # 1. Check Evolution API Gateway connectivity
    print("1. Checking Evolution API Gateway status...")
    async with httpx.AsyncClient() as client:
        try:
            url = f"{api_url.rstrip('/')}/instance/connectionState/test"
            headers = {"apikey": api_key}
            res = await client.get(url, headers=headers, timeout=5.0)
            print(f"   ✓ Evolution API is online (HTTP {res.status_code})")
        except httpx.ConnectError:
            print("   ✗ ERROR: Could not reach Evolution API.")
            print("     Make sure your Docker container is actively running.")
            return
        except Exception as e:
            print(f"   ✗ ERROR: Failed to communicate: {e}")
            return
            
    # 2. Try creating instance kochi_farm_whatsapp
    print("\n2. Testing Instance Creation ('kochi_farm_whatsapp')...")
    async with httpx.AsyncClient() as client:
        try:
            url = f"{api_url.rstrip('/')}/instance/create"
            headers = {"apikey": api_key, "Content-Type": "application/json"}
            payload = {
                "instanceName": "kochi_farm_whatsapp",
                "token": "",
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS"
            }
            res = await client.post(url, headers=headers, json=payload, timeout=10.0)
            print(f"   - HTTP Response Code: {res.status_code}")
            print(f"   - Response Body: {res.text.strip()}")
        except Exception as e:
            print(f"   ✗ ERROR during creation: {e}")

    # 3. Try registering webhook for kochi_farm_whatsapp
    print("\n3. Testing Webhook Registration...")
    async with httpx.AsyncClient() as client:
        try:
            url = f"{api_url.rstrip('/')}/webhook/set/kochi_farm_whatsapp"
            headers = {"apikey": api_key, "Content-Type": "application/json"}
            payload = {
                "webhook": {
                    "enabled": True,
                    "url": f"{app_url}/webhooks/whatsapp",
                    "byEvents": False,
                    "base64": False,
                    "events": ["CONNECTION_UPDATE", "MESSAGES_UPSERT", "SEND_MESSAGE"]
                }
            }
            res = await client.post(url, headers=headers, json=payload, timeout=10.0)
            print(f"   - HTTP Response Code: {res.status_code}")
            print(f"   - Response Body: {res.text.strip()}")
        except Exception as e:
            print(f"   ✗ ERROR during webhook setup: {e}")

    # 4. Try fetching QR code for kochi_farm_whatsapp
    print("\n4. Testing QR Code Retrieval...")
    async with httpx.AsyncClient() as client:
        try:
            url = f"{api_url.rstrip('/')}/instance/connect/kochi_farm_whatsapp"
            headers = {"apikey": api_key}
            res = await client.get(url, headers=headers, timeout=10.0)
            print(f"   - HTTP Response Code: {res.status_code}")
            if res.status_code == 200:
                data = res.json()
                has_code = "code" in data or "base64" in data
                print(f"   ✓ Successfully fetched QR Code! Data keys: {list(data.keys())} (Has code/base64: {has_code})")
            else:
                print(f"   - Response Body: {res.text.strip()}")
        except Exception as e:
            print(f"   ✗ ERROR during QR fetch: {e}")

    # 5. Check FastAPI Local Server status
    print("\n5. Checking FastAPI Backend Server on port 8000...")
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get("http://localhost:8000/", timeout=5.0)
            print(f"   ✓ FastAPI backend is online!")
            print(f"   - HTTP Response Code: {res.status_code}")
        except httpx.ConnectError:
            print("   ✗ ERROR: Could not reach FastAPI backend at http://localhost:8000.")
        except Exception as e:
            print(f"   ✗ ERROR: Failed to communicate with backend: {e}")
            
    print("\n=============================================\n")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
