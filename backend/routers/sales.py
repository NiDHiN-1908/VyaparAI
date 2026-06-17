# backend/routers/sales.py
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from backend.models.schemas import ChatRequest, PaymentRequest
from backend.services.supabase_service import supabase_svc
from backend.services.rag_service import rag_svc
from backend.langgraph.sales_workflow import run_sales_chat

logger = logging.getLogger("vyaparai.routers.sales")
router = APIRouter(prefix="", tags=["LangGraph AI Sales Agent"])

@router.post("/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    logger.info(f"Uploading knowledge file: {file.filename}")
    try:
        content = await file.read()
        text = content.decode("utf-8")
        chunks_added = rag_svc.ingest_text(text, source=file.filename)
        return {"status": "success", "chunks_added": chunks_added}
    except Exception as e:
        logger.error(f"Error uploading knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat_sales_agent(payload: ChatRequest):
    logger.info(f"Chat request from lead ID: {payload.lead_id} for product: {payload.product_id}")
    try:
        # Check if lead exists
        leads = supabase_svc.get_leads()
        lead_exists = any(l["id"] == payload.lead_id for l in leads)
        if not lead_exists:
            raise HTTPException(status_code=404, detail="Lead not found")

        # Execute conversation workflow in LangGraph
        chat_res = run_sales_chat(
            lead_id=payload.lead_id,
            product_id=payload.product_id,
            user_message=payload.message
        )

        return {
            "status": "success",
            "reply": chat_res["response"],
            "state": chat_res["next_state"],
            "history": chat_res["history"]
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Sales chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment")
async def process_payment(payload: PaymentRequest):
    logger.info(f"Payment received for order {payload.order_id} - status: {payload.status}")
    try:
        # Find order
        orders = supabase_svc.get_orders()
        order_rec = next((o for o in orders if o["id"] == payload.order_id), None)
        if not order_rec:
            raise HTTPException(status_code=404, detail="Order not found")

        status_val = "paid" if payload.status.lower() == "paid" else "failed"
        txn_id = payload.transaction_id or f"TXN_GATEWAY_{payload.order_id[:8].upper()}"

        # Update order status in Supabase
        updated_order = supabase_svc.update_order_status(
            order_id=payload.order_id,
            status=status_val,
            transaction_id=txn_id
        )

        # Increment conversion metrics on success
        if status_val == "paid":
            lead = supabase_svc.get_leads()
            lead_data = next((l for l in lead if l["id"] == order_rec["lead_id"]), {})
            business_id = lead_data.get("business_id")
            if business_id:
                try:
                    supabase_svc.increment_analytics(business_id, "total_conversions", 1)
                except Exception as e:
                    logger.error(f"Failed to increment conversion analytics: {e}")

        return {"status": "success", "data": updated_order}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing payment webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
