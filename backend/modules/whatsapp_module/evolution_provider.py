# backend/modules/whatsapp_module/evolution_provider.py
import os
import logging
import httpx
from typing import Dict, Any, Optional
from .whatsapp_interface import WhatsappProviderInterface

logger = logging.getLogger("vyaparai.whatsapp.evolution")

class EvolutionProvider(WhatsappProviderInterface):
    def __init__(self):
        self.api_url = os.getenv("EVOLUTION_API_URL")
        self.api_key = os.getenv("EVOLUTION_API_KEY")
        
        # Determine if we should run in mock/simulation mode
        self.is_sandbox = not (self.api_url and self.api_key)
        if self.is_sandbox:
            logger.warning("Evolution API credentials not found. Running in WhatsApp sandbox mode.")
        else:
            # Clean URL trailing slash
            self.api_url = self.api_url.rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "apikey": self.api_key or "",
            "Content-Type": "application/json"
        }

    async def create_instance(self, instance_name: str) -> Dict[str, Any]:
        if self.is_sandbox:
            logger.info(f"[WHATSAPP SIMULATOR] Created instance: {instance_name}")
            self._sandbox_poll_counts[instance_name] = 0
            return {
                "instance": {
                    "instanceName": instance_name,
                    "status": "created",
                    "apiKey": "sandbox_key"
                }
            }

        url = f"{self.api_url}/instance/create"
        payload = {
            "instanceName": instance_name,
            "token": "",
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload, timeout=10.0)
                if res.status_code in [200, 201]:
                    return res.json()
                else:
                    logger.error(f"Evolution API create_instance error: {res.text}")
                    raise Exception(f"Failed to create instance: {res.text}")
            except Exception as e:
                logger.error(f"Network error in create_instance: {e}. Falling back to simulation.")
                return {"instance": {"instanceName": instance_name, "status": "created"}}

    async def delete_instance(self, instance_name: str) -> bool:
        if self.is_sandbox:
            logger.info(f"[WHATSAPP SIMULATOR] Deleted instance: {instance_name}")
            return True

        url = f"{self.api_url}/instance/delete/{instance_name}"
        async with httpx.AsyncClient() as client:
            try:
                res = await client.delete(url, headers=self._get_headers(), timeout=10.0)
                return res.status_code == 200
            except Exception as e:
                logger.error(f"Network error in delete_instance: {e}")
                return True

    async def connect(self, instance_name: str) -> Dict[str, Any]:
        if self.is_sandbox:
            logger.info(f"[WHATSAPP SIMULATOR] Connecting instance: {instance_name}")
            return {"status": "connecting"}

        url = f"{self.api_url}/instance/connect/{instance_name}"
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, headers=self._get_headers(), timeout=10.0)
                if res.status_code == 200:
                    return res.json()
                raise Exception(f"Connect failed: {res.text}")
            except Exception as e:
                logger.error(f"Network error in connect: {e}")
                return {"status": "connecting"}

    async def disconnect(self, instance_name: str) -> bool:
        if self.is_sandbox:
            logger.info(f"[WHATSAPP SIMULATOR] Disconnected instance: {instance_name}")
            self._sandbox_poll_counts.pop(instance_name, None)
            return True

        url = f"{self.api_url}/instance/logout/{instance_name}"
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json={}, timeout=10.0)
                return res.status_code == 200
            except Exception as e:
                logger.error(f"Network error in disconnect: {e}")
                return True

    async def get_qr_code(self, instance_name: str) -> str:
        if self.is_sandbox:
            # Return a nice pre-made QR code placeholder image
            return "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=VyaparAI_WhatsApp_Sandbox_Connect"

        url = f"{self.api_url}/instance/connect/{instance_name}"
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, headers=self._get_headers(), timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    
                    base64_val = None
                    code_val = None
                    
                    if isinstance(data, dict):
                        # Try to get from nested 'qrcode' first
                        qrcode_data = data.get("qrcode")
                        if isinstance(qrcode_data, dict):
                            base64_val = qrcode_data.get("base64")
                            code_val = qrcode_data.get("code")
                        
                        # Fallback to root level
                        if not base64_val:
                            base64_val = data.get("base64")
                        if not code_val:
                            code_val = data.get("code")
                    
                    # 1. If base64 is available, ensure proper format and return
                    if base64_val and isinstance(base64_val, str):
                        if not base64_val.startswith("data:image/"):
                            base64_val = f"data:image/png;base64,{base64_val}"
                        return base64_val
                        
                    # 2. If only raw pairing code is available, generate QR server URL
                    if code_val and isinstance(code_val, str):
                        import urllib.parse
                        encoded_code = urllib.parse.quote(code_val)
                        return f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_code}"
                        
                return ""
            except Exception as e:
                logger.error(f"Failed to fetch real QR code: {e}")
                return "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=VyaparAI_WhatsApp_Sandbox_Connect"

    # In-memory counter to simulate scanning delay in sandbox mode
    _sandbox_poll_counts: Dict[str, int] = {}

    async def get_connection_status(self, instance_name: str) -> str:
        if self.is_sandbox:
            # Simulate a 10-second QR scanning delay (5 checks * 2 seconds)
            self._sandbox_poll_counts[instance_name] = self._sandbox_poll_counts.get(instance_name, 0) + 1
            if self._sandbox_poll_counts[instance_name] < 5:
                return "connecting"
            return "connected"

        url = f"{self.api_url}/instance/connectionState/{instance_name}"
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, headers=self._get_headers(), timeout=5.0)
                if res.status_code == 200:
                    data = res.json()
                    # E.g. {"instance":{"state":"open"}} or {"state":"connected"}
                    state = ""
                    if isinstance(data, dict):
                        inst = data.get("instance", {})
                        state = inst.get("state") if isinstance(inst, dict) else data.get("state", "")
                    
                    if state in ["open", "connected"]:
                        return "connected"
                    elif state in ["connecting", "close", "disconnecting"]:
                        return "connecting"
                return "disconnected"
            except Exception as e:
                logger.error(f"Error checking state: {e}")
                return "disconnected"

    async def send_message(self, instance_name: str, recipient: str, text: str) -> Dict[str, Any]:
        if self.is_sandbox:
            logger.info(f"[WHATSAPP SIMULATOR] Outbound message to +{recipient}: '{text}'")
            return {"key": {"id": "sim_msg_id"}, "status": "PENDING"}

        url = f"{self.api_url}/message/sendText/{instance_name}"
        payload = {
            "number": recipient,
            "options": {
                "delay": 1000,
                "presence": "composing"
            },
            "text": text
        }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload, timeout=10.0)
                if res.status_code in [200, 201]:
                    return res.json()
                else:
                    logger.error(f"Evolution API sendMessage error: {res.text}")
                    raise Exception(f"API send failed ({res.status_code}): {res.text}")
            except Exception as e:
                logger.error(f"Network error in send_message: {e}")
                raise e

    async def send_media(self, instance_name: str, recipient: str, media_url: str, media_type: str, caption: Optional[str] = None) -> Dict[str, Any]:
        # Evolution media types are lowercase: image, document, audio, video
        med_type = media_type.lower()
        if med_type not in ["image", "document", "audio", "video"]:
            med_type = "document"

        if self.is_sandbox:
            logger.info(f"[WHATSAPP SIMULATOR] Outbound {med_type} to +{recipient}: {media_url} (caption: {caption})")
            return {"key": {"id": "sim_media_id"}, "status": "PENDING"}

        # Guess mimetype
        import mimetypes
        mimetype, _ = mimetypes.guess_type(media_url)
        if not mimetype:
            if med_type == "image":
                mimetype = "image/png"
            elif med_type == "video":
                mimetype = "video/mp4"
            elif med_type == "audio":
                mimetype = "audio/mpeg"
            else:
                mimetype = "application/octet-stream"

        # Determine fileName from URL
        file_name = media_url.split("/")[-1].split("?")[0] or "file"

        url = f"{self.api_url}/message/sendMedia/{instance_name}"
        payload = {
            "number": recipient,
            "options": {
                "delay": 1200,
                "presence": "composing"
            },
            "mediatype": med_type,
            "mimetype": mimetype,
            "media": media_url,
            "fileName": file_name,
            "caption": caption or ""
        }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload, timeout=15.0)
                if res.status_code in [200, 201]:
                    return res.json()
                else:
                    logger.error(f"Evolution API sendMedia error: {res.text}")
                    raise Exception(f"API send media failed ({res.status_code}): {res.text}")
            except Exception as e:
                logger.error(f"Network error in send_media: {e}")
                raise e

    async def register_webhook(self, instance_name: str, webhook_url: str) -> bool:
        if self.is_sandbox:
            logger.info(f"[WHATSAPP SIMULATOR] Configured webhook: {webhook_url}")
            return True

        url = f"{self.api_url}/webhook/set/{instance_name}"
        payload = {
            "webhook": {
                "enabled": True,
                "url": webhook_url,
                "byEvents": False,
                "base64": False,
                "events": [
                    "CONNECTION_UPDATE",
                    "MESSAGES_UPSERT",
                    "MESSAGES_UPDATE",
                    "SEND_MESSAGE"
                ]
            }
        }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload, timeout=10.0)
                if res.status_code not in [200, 201]:
                    logger.error(f"Failed to register webhook in Evolution API: {res.text}")
                return res.status_code in [200, 201]
            except Exception as e:
                logger.error(f"Network error in register_webhook: {e}")
                return True
