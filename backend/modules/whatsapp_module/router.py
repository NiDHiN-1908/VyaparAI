# backend/modules/whatsapp_module/router.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from .instance_service import whatsapp_instance_svc

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Instance Onboarding"])

class ConnectInstanceRequest(BaseModel):
    tenant_id: str = "00000000-0000-0000-0000-000000000000"
    instance_name: str

@router.get("/instances")
async def get_instances(tenant_id: str = "00000000-0000-0000-0000-000000000000"):
    """
    Returns list of registered WhatsApp instances for a tenant.
    """
    try:
        from backend.services.supabase_service import supabase_svc
        instances = supabase_svc.get_whatsapp_instances(tenant_id)
        return {"status": "success", "data": instances}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect")
async def connect_whatsapp(payload: ConnectInstanceRequest):
    """
    Creates/initializes a WhatsApp instance for onboarding.
    """
    try:
        res = await whatsapp_instance_svc.connect_instance(payload.tenant_id, payload.instance_name)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{instance_id}/qrcode")
async def get_qrcode(instance_id: str):
    """
    Returns the QR code string/url to scan.
    """
    try:
        qr_data = await whatsapp_instance_svc.get_qr_code(instance_id)
        return {"status": "success", "qrcode": qr_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{instance_id}/status")
async def get_status(instance_id: str):
    """
    Checks connection status: connected, disconnected, connecting.
    """
    try:
        status_val = await whatsapp_instance_svc.get_connection_status(instance_id)
        return {"status": "success", "connection_status": status_val}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{instance_id}/disconnect")
async def disconnect_whatsapp(instance_id: str, delete: bool = Query(False)):
    """
    Disconnects/logs out of the WhatsApp instance session.
    """
    try:
        res = await whatsapp_instance_svc.disconnect_instance(instance_id, delete_completely=delete)
        return {"status": "success", "disconnected": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
