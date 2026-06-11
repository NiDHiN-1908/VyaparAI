# backend/routers/business.py
import logging
from fastapi import APIRouter, HTTPException, Depends
from backend.models.schemas import BusinessCreate, ProductCreate
from backend.services.supabase_service import supabase_svc

logger = logging.getLogger("vyaparai.routers.business")
router = APIRouter(prefix="", tags=["Business & Products"])

@router.post("/business")
async def create_business(payload: BusinessCreate):
    logger.info(f"Creating business profile: {payload.name}")
    try:
        res = supabase_svc.create_business(
            name=payload.name,
            location=payload.location,
            contact=payload.contact,
            industry=payload.industry
        )
        return {"status": "success", "data": res}
    except Exception as e:
        logger.error(f"Error creating business: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/product")
async def create_product(payload: ProductCreate):
    logger.info(f"Adding product: {payload.name} for business: {payload.business_id}")
    try:
        # Verify business exists
        business = supabase_svc.get_business(payload.business_id)
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
            
        res = supabase_svc.create_product(
            business_id=payload.business_id,
            name=payload.name,
            description=payload.description,
            price=payload.price,
            image_url=payload.image_url
        )
        return {"status": "success", "data": res}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error adding product: {e}")
        raise HTTPException(status_code=500, detail=str(e))
