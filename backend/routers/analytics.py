# backend/routers/analytics.py
import logging
from fastapi import APIRouter, HTTPException, Query
from backend.services.supabase_service import supabase_svc

logger = logging.getLogger("vyaparai.routers.analytics")
router = APIRouter(prefix="", tags=["Analytics Engine"])

@router.get("/analytics")
async def get_business_analytics(business_id: str = Query(..., example="business_uuid_here")):
    logger.info(f"Retrieving analytics overview for business ID: {business_id}")
    try:
        # Check if business exists
        business = supabase_svc.get_business(business_id)
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")

        # Get analytics rows from database
        rows = supabase_svc.get_analytics(business_id)

        # Aggregate total values for widgets
        total_leads = sum(r.get("total_leads", 0) for r in rows)
        total_conversions = sum(r.get("total_conversions", 0) for r in rows)
        videos_generated = sum(r.get("videos_generated", 0) for r in rows)
        
        # Calculate average engagement rate
        avg_engagement = 0.0
        if rows:
            avg_engagement = sum(float(r.get("engagement_rate", 0.0)) for r in rows) / len(rows)

        # Build conversion funnel rates
        conversion_rate = 0.0
        if total_leads > 0:
            conversion_rate = (total_conversions / total_leads) * 100

        return {
            "status": "success",
            "business_id": business_id,
            "summary": {
                "total_leads": total_leads,
                "total_conversions": total_conversions,
                "videos_generated": videos_generated,
                "avg_engagement_rate": round(avg_engagement, 2),
                "conversion_rate": round(conversion_rate, 2)
            },
            "history": rows
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching analytics data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
