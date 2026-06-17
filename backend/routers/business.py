# backend/routers/business.py
import logging
import os
import shutil
import uuid
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from backend.models.schemas import BusinessCreate, ProductCreate
from backend.services.supabase_service import supabase_svc
from backend.config import settings

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
            images=payload.images
        )
        return {"status": "success", "data": res}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error adding product: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    logger.info(f"Uploading product image: {file.filename}")
    try:
        # Generate unique filename
        ext = os.path.splitext(file.filename)[1]
        filename = f"prod_{uuid.uuid4().hex}{ext}"
        file_path = settings.MEDIA_DIR / filename
        
        # Save file locally
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"Image saved locally to {file_path}")
        return {"status": "success", "url": f"/static/media/{filename}"}
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/product")
async def get_products():
    try:
        products = supabase_svc.get_products()
        return products
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/product/{product_id}")
async def get_product(product_id: str):
    try:
        product = supabase_svc.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/business")
async def get_businesses():
    try:
        businesses = supabase_svc.get_businesses()
        return {"status": "success", "data": businesses}
    except Exception as e:
        logger.error(f"Error fetching businesses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


