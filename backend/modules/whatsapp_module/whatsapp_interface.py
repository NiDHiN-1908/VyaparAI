# backend/modules/whatsapp_module/whatsapp_interface.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class WhatsappProviderInterface(ABC):
    @abstractmethod
    async def create_instance(self, instance_name: str) -> Dict[str, Any]:
        """Creates a WhatsApp connection instance."""
        pass

    @abstractmethod
    async def delete_instance(self, instance_name: str) -> bool:
        """Deletes a WhatsApp connection instance and cleans up sessions."""
        pass

    @abstractmethod
    async def connect(self, instance_name: str) -> Dict[str, Any]:
        """Connects/initiates session login process."""
        pass

    @abstractmethod
    async def disconnect(self, instance_name: str) -> bool:
        """Logs out and disconnects WhatsApp session."""
        pass

    @abstractmethod
    async def get_qr_code(self, instance_name: str) -> str:
        """Returns the connection QR code in base64 format or image URL."""
        pass

    @abstractmethod
    async def get_connection_status(self, instance_name: str) -> str:
        """Returns status: 'connected', 'disconnected', 'connecting'."""
        pass

    @abstractmethod
    async def send_message(self, instance_name: str, recipient: str, text: str) -> Dict[str, Any]:
        """Sends a text message to recipient's phone number."""
        pass

    @abstractmethod
    async def send_media(self, instance_name: str, recipient: str, media_url: str, media_type: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Sends media: image, audio, video, document."""
        pass

    @abstractmethod
    async def register_webhook(self, instance_name: str, webhook_url: str) -> bool:
        """Configures Evolution/Meta webhook to route incoming messages to our backend."""
        pass
