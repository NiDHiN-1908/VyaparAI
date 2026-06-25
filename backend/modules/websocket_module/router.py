# backend/modules/websocket_module/router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .websocket_service import websocket_manager
import logging

logger = logging.getLogger("vyaparai.websocket.router")
router = APIRouter(prefix="/ws", tags=["Websocket Manager"])

@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    tenant_id: str = Query("00000000-0000-0000-0000-000000000000")
):
    await websocket_manager.connect(websocket, tenant_id)
    try:
        while True:
            # Keep connection open and listen for any inbound ping/messages from the client
            data = await websocket.receive_text()
            # Simple heartbeat ping-pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, tenant_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket, tenant_id)
