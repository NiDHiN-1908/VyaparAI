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
        if existing:
            instance_id = existing["id"]
            
            # In sandbox mode, if already connected in DB, pre-fill sandbox counter to prevent reset
            if existing.get("status") == "connected" and getattr(self.provider, "is_sandbox", False):
                if hasattr(self.provider, "_sandbox_poll_counts") and instance_name not in self.provider._sandbox_poll_counts:
                    self.provider._sandbox_poll_counts[instance_name] = 5
                    
            # Check connection status on provider to see if it's already active
            try:
                provider_status = await self.provider.get_connection_status(instance_name)
            except Exception as e:
                logger.warning(f"Failed to check connection status on provider for {instance_name}: {e}")
                provider_status = existing.get("status", "disconnected")

            if provider_status in ["connected", "connecting"]:
                if existing.get("status") != provider_status:
                    supabase_svc.update_whatsapp_instance_status(instance_id, provider_status)
                return {
                    "id": instance_id,
                    "instance_name": instance_name,
                    "status": provider_status,
                    "provider": self.provider_name
                }
            
            # Update to connecting since it's not connected on provider
            supabase_svc.update_whatsapp_instance_status(instance_id, "connecting")
        else:
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
        webhook_url = f"{app_url}/webhooks/whatsapp"
        logger.info(f"Registering webhook: {webhook_url}")
        try:
            await self.provider.register_webhook(instance_name, webhook_url)
        except Exception as e:
            logger.error(f"Failed to register webhook: {e}")

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
