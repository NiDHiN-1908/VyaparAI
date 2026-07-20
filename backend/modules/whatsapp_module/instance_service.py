# backend/modules/whatsapp_module/instance_service.py
import os
import logging
from typing import Dict, Any, Optional
from backend.services.supabase_service import supabase_svc
from backend.modules.websocket_module import websocket_manager
from .evolution_provider import EvolutionProvider
from .meta_cloud_provider import MetaCloudProvider

logger = logging.getLogger("vyaparai.whatsapp.service")

class InstanceService:
    def __init__(self):
        # Dynamic Provider Selection (Dependency Injection style based on config)
        self.provider_name = os.getenv("WHATSAPP_PROVIDER", "evolution")
        if self.provider_name == "meta":
            self.provider = MetaCloudProvider()
        else:
            self.provider = EvolutionProvider()

    async def connect_instance(self, tenant_id: str, instance_name: str) -> Dict[str, Any]:
        """
        Creates instance on provider, registers webhook, and stores instance record in DB.
        """
        logger.info(f"Connecting instance '{instance_name}' for tenant {tenant_id} using {self.provider_name}")
        
        # 1. Check if instance already exists in DB
        existing = supabase_svc.get_whatsapp_instance_by_name(instance_name)
        is_sandbox = getattr(self.provider, "is_sandbox", False)
        
        if existing:
            instance_id = existing["id"]
            
            # In sandbox mode, if already connected in DB, pre-fill sandbox counter and return early to prevent reset
            if existing.get("status") == "connected" and is_sandbox:
                if hasattr(self.provider, "_sandbox_poll_counts") and instance_name not in self.provider._sandbox_poll_counts:
                    self.provider._sandbox_poll_counts[instance_name] = 5
                
                return {
                    "id": instance_id,
                    "instance_name": instance_name,
                    "status": "connected",
                    "provider": self.provider_name
                }
            
            # For real provider (e.g. Evolution API), implement clean session reset.
            # Delete any existing session/instance on the provider side before initiating a new linking phase.
            # This completely clears persistent browser context data, cookies, tokens, and IndexedDB cache files.
            if not is_sandbox:
                logger.info(f"Comprehensive session reset: deleting existing provider instance '{instance_name}' to purge cached browser state.")
                try:
                    await self.provider.delete_instance(instance_name)
                except Exception as e:
                    logger.warning(f"Failed to delete existing instance on provider: {e}")
                
                # Clear DB status, phone_number, and session_data of the old account to prevent displaying it in the UI
                try:
                    supabase_svc.update_whatsapp_instance_status(
                        instance_id_or_name=instance_id,
                        status="connecting",
                        phone_number="",
                        session_data={}
                    )
                except Exception as e:
                    logger.warning(f"Failed to reset DB fields for instance in DB: {e}")
            else:
                supabase_svc.update_whatsapp_instance_status(instance_id, "connecting")
        else:
            # If the instance does not exist in the DB, we still want to make sure
            # there isn't an orphan instance with the same name on the real provider.
            if not is_sandbox:
                logger.info(f"Comprehensive session reset: ensuring no orphan instance '{instance_name}' exists on the provider.")
                try:
                    await self.provider.delete_instance(instance_name)
                except Exception as e:
                    logger.warning(f"Failed to delete existing instance on provider: {e}")
            
            # Create instance record in DB
            inst_record = supabase_svc.create_whatsapp_instance(
                tenant_id=tenant_id,
                provider=self.provider_name,
                instance_name=instance_name,
                status="connecting"
            )
            instance_id = inst_record["id"]

        # 2. Call provider API to create session
        try:
            await self.provider.create_instance(instance_name)
        except Exception as e:
            logger.error(f"Provider failed to create instance: {e}")
            # Ignore and continue (rely on simulator fallback)

        # 3. Register incoming webhook to route to our backend
        app_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
        webhook_url = f"{app_url.rstrip('/')}/webhooks/whatsapp"
        
        # Resolve public webhook URL utilizing ngrok endpoint for client/external visibility & validation
        from backend.config import settings
        public_url = settings.PUBLIC_URL or os.getenv("PUBLIC_URL") or os.getenv("APP_BASE_URL") or "http://localhost:8000"
        public_webhook_url = f"{public_url.rstrip('/')}/webhooks/whatsapp"
        
        logger.info(f"Registering webhook with provider: {webhook_url} (Public counterpart: {public_webhook_url})")
        try:
            provider_webhook = f"{webhook_url}?instance={instance_name}"
            await self.provider.register_webhook(instance_name, provider_webhook)
        except Exception as e:
            logger.error(f"Failed to register webhook: {e}")

        # Store the public webhook URL mapped to this WhatsApp account in the database
        try:
            supabase_svc.update_whatsapp_instance_webhook(instance_id, public_webhook_url)
        except Exception as e:
            logger.error(f"Failed to save webhook URL to database: {e}")

        # 4. Try connecting session
        try:
            await self.provider.connect(instance_name)
        except Exception as e:
            logger.error(f"Failed to trigger connect: {e}")

        return {
            "id": instance_id,
            "instance_name": instance_name,
            "status": "connecting",
            "provider": self.provider_name
        }

    async def get_qr_code(self, instance_id: str) -> str:
        """
        Retrieves QR code from WhatsApp provider.
        """
        instance = supabase_svc.get_whatsapp_instance(instance_id)
        if not instance:
            logger.warning(f"get_qr_code called for non-existent instance_id: {instance_id}")
            return "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=VyaparAI_WhatsApp_Sandbox_Connect"
        return await self.provider.get_qr_code(instance["instance_name"])

    async def get_connection_status(self, instance_id: str) -> str:
        """
        Polls connection state from provider, updates DB, and broadcasts event on state change.
        """
        instance = supabase_svc.get_whatsapp_instance(instance_id)
        if not instance:
            return "disconnected"
            
        old_status = instance.get("status", "disconnected")
        
        # In sandbox mode, if already connected in DB, pre-fill sandbox counter to prevent reset
        if old_status == "connected" and getattr(self.provider, "is_sandbox", False):
            if hasattr(self.provider, "_sandbox_poll_counts") and instance["instance_name"] not in self.provider._sandbox_poll_counts:
                self.provider._sandbox_poll_counts[instance["instance_name"]] = 5
                
        new_status = await self.provider.get_connection_status(instance["instance_name"])
        
        if old_status != new_status:
            logger.info(f"WhatsApp instance status changed from {old_status} to {new_status}")
            supabase_svc.update_whatsapp_instance_status(instance_id, new_status)
            
            # Broadcast state changes via WebSocket
            event_name = "whatsapp.connected" if new_status == "connected" else "whatsapp.disconnected"
            await websocket_manager.broadcast_to_tenant(
                tenant_id=instance["tenant_id"],
                event_type=event_name,
                data={
                    "instance_id": instance_id,
                    "instance_name": instance["instance_name"],
                    "status": new_status
                }
            )
            
        return new_status

    async def disconnect_instance(self, instance_id: str, delete_completely: bool = False) -> bool:
        """
        Disconnects/Logs out the instance session.
        """
        instance = supabase_svc.get_whatsapp_instance(instance_id)
        if not instance:
            return False

        logger.info(f"Disconnecting WhatsApp instance: {instance['instance_name']}")
        try:
            await self.provider.disconnect(instance["instance_name"])
        except Exception as e:
            logger.error(f"Provider disconnect error: {e}")

        # Update DB status
        supabase_svc.update_whatsapp_instance_status(instance_id, "disconnected")
        
        # Broadcast disconnect event
        await websocket_manager.broadcast_to_tenant(
            tenant_id=instance["tenant_id"],
            event_type="whatsapp.disconnected",
            data={
                "instance_id": instance_id,
                "instance_name": instance["instance_name"],
                "status": "disconnected"
            }
        )

        if delete_completely:
            try:
                await self.provider.delete_instance(instance["instance_name"])
            except Exception as e:
                logger.error(f"Provider delete_instance error: {e}")
            supabase_svc.delete_whatsapp_instance(instance_id)
            
        return True

# Initialize a global instance service
whatsapp_instance_svc = InstanceService()
