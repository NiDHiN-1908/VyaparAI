# backend/modules/websocket_module/websocket_service.py
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger("vyaparai.websocket")

class ConnectionManager:
    def __init__(self):
        # Maps tenant_id to a list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = []
        self.active_connections[tenant_id].append(websocket)
        logger.info(f"WebSocket client connected to tenant: {tenant_id}")

    def disconnect(self, websocket: WebSocket, tenant_id: str):
        if tenant_id in self.active_connections:
            if websocket in self.active_connections[tenant_id]:
                self.active_connections[tenant_id].remove(websocket)
                logger.info(f"WebSocket client disconnected from tenant: {tenant_id}")
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]

    async def broadcast_to_tenant(self, tenant_id: str, event_type: str, data: dict):
        payload = {
            "event": event_type,
            "data": data
        }
        connections = self.active_connections.get(tenant_id, [])
        if not connections:
            logger.debug(f"No active WebSocket connections for tenant {tenant_id} to broadcast event {event_type}")
            return
            
        logger.info(f"Broadcasting event {event_type} to {len(connections)} clients in tenant {tenant_id}")
        # Send to all connected sockets for this tenant
        disconnected_sockets = []
        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception as e:
                logger.error(f"Error sending message on WebSocket: {e}")
                disconnected_sockets.append(connection)
                
        # Clean up any dead connections
        for socket in disconnected_sockets:
            self.disconnect(socket, tenant_id)

websocket_manager = ConnectionManager()
