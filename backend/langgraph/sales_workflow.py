# backend/langgraph/sales_workflow.py
import logging
import json
from typing import TypedDict, List, Dict, Any
# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph, END
from backend.agents.content_agent import get_ollama_llm
from backend.services.supabase_service import supabase_svc
from backend.services.rag_service import rag_svc

logger = logging.getLogger("vyaparai.langgraph.sales_workflow")

# Define state structure
class SalesState(TypedDict):
    lead_id: str
    product_id: str
    current_state: str  # WELCOME, PRODUCT_INFO, QA_LOOP, ADDRESS_COLLECTION, PAYMENT, ORDER_CONFIRMED, ESCALATE
    chat_history: List[Dict[str, str]]
    user_message: str
    agent_response: str
    customer_info: Dict[str, Any]
    order_id: str

# Helper to format chat history for LLM prompt
def format_history(history: List[Dict[str, str]]) -> str:
    formatted = []
    for msg in history:
        role = "Customer" if msg["role"] == "user" else "Assistant"
        formatted.append(f"{role}: {msg['content']}")
    return "\n".join(formatted)

# --- Node Implementations ---

def welcome_node(state: SalesState) -> SalesState:
    logger.info("Running welcome_node")
    lead = supabase_svc.get_leads()  # Fetch lead data for context if available
    lead_data = next((l for l in lead if l["id"] == state["lead_id"]), {})
    username = lead_data.get("username", "Customer")
    
    product = supabase_svc.get_product(state["product_id"])
    prod_name = product.get("name", "our product") if product else "our product"
    
    response = (
        f"Namaste {username}! 🙏 Welcome to VyaparAI Sales. "
        f"We noticed you were interested in our {prod_name}. "
        f"It is one of our best-selling items. Can I tell you more about its features and pricing?"
    )
    
    state["agent_response"] = response
    state["current_state"] = "PRODUCT_INFO"  # Advance state
    return state

def product_info_node(state: SalesState) -> SalesState:
    logger.info("Running product_info_node")
    product = supabase_svc.get_product(state["product_id"])
    prod_name = product.get("name", "Product") if product else "Product"
    prod_desc = product.get("description", "High quality product") if product else "High quality"
    prod_price = product.get("price", 999.00) if product else 999.00

    response = (
        f"The {prod_name} is designed for top-tier performance. "
        f"Description: {prod_desc}.\n"
        f"Price: Rs. {prod_price:.2f}. "
        f"Would you like to place an order, or do you have any questions about it?"
    )
    
    state["agent_response"] = response
    state["current_state"] = "QA_LOOP"
    return state

def qa_loop_node(state: SalesState) -> SalesState:
    logger.info("Running qa_loop_node")
    product = supabase_svc.get_product(state["product_id"])
    prod_name = product.get("name", "Product") if product else "Product"
    prod_price = product.get("price", 999.00) if product else 999.00

    try:
        # Retrieve context from RAG Service
        rag_context = rag_svc.retrieve(state["user_message"])
        
        llm = get_ollama_llm()
        history = format_history(state["chat_history"])
        
        prompt = (
            f"You are a sales assistant helping a customer with {prod_name}.\n"
            f"Product Price: Rs. {prod_price}.\n"
            f"Previous Chat History:\n{history}\n"
        )
        
        if rag_context:
            prompt += f"\nCOMPANY KNOWLEDGE BASE (Use this to answer the customer's query accurately):\n{rag_context}\n\n"
            
        prompt += (
            f"Customer Message: \"{state['user_message']}\"\n\n"
            "INSTRUCTIONS:\n"
            "1. Formulate a warm, polite, and helpful response answering their specific query or objection.\n"
            "2. If a COMPANY KNOWLEDGE BASE is provided above, use it to answer the customer. Do not make up or hallucinate details that are not in the knowledge base.\n"
            "3. If you do not know the answer, politely state that you're not sure, but offer to have a representative get in touch. Do not make up facts.\n"
            "4. DO NOT ask for their shipping address unless they explicitly show intent to buy (e.g. asking to order, saying yes to buy, etc.).\n"
            "5. If they are just asking questions, answer the question clearly, and ask if they have any other questions or if they would like to place an order."
        )
        response = llm.invoke(prompt).content
    except Exception as e:
        logger.warning(f"Ollama prediction failed in qa_loop: {e}. Using rule-based fallback.")
        # Fallback responses
        msg = state["user_message"].lower()
        if "discount" in msg or "price" in msg or "cost" in msg or "how much" in msg:
            response = f"The price of {prod_name} is Rs. {prod_price:.2f}. We offer free delivery all across India! Would you like to buy it now?"
        elif "quality" in msg or "warranty" in msg or "guarantee" in msg:
            response = f"We guarantee 100% genuine quality for {prod_name}. If you face any issues, we have a 7-day replacement policy. Are you ready to order?"
        elif "ingredients" in msg or "what is" in msg or "details" in msg or "organic" in msg:
            response = f"Our {prod_name} is made from 100% premium ingredients under strict quality standards. Would you like me to share more details, or are you ready to order?"
        elif "where" in msg or "address" in msg or "location" in msg or "shop" in msg:
            response = f"We ship our products directly to your doorstep all over India. Where are you located so we can calculate shipping?"
        elif "buy" in msg or "order" in msg or "purchase" in msg or "want" in msg:
            response = f"Great! Please provide your full shipping address (including house number, street name, city, and pincode) so I can create your order."
        else:
            response = f"Thank you for asking! Our {prod_name} is of the highest quality. Could you please specify your question, or would you like to proceed with the order?"

    state["agent_response"] = response
    # We stay in QA_LOOP until user shows intent to buy/submit address
    return state

def address_collection_node(state: SalesState) -> SalesState:
    logger.info("Running address_collection_node")
    # Attempt to extract address from user message
    msg = state["user_message"]
    
    if len(msg) > 12 and any(char.isdigit() for char in msg):  # Simple heuristic for street/pincode
        state["customer_info"]["address"] = msg
        state["agent_response"] = (
            f"Thank you! I have recorded your delivery address: \"{msg}\". "
            "To complete the purchase, please make a payment using UPI. "
            "Shall I generate your payment link?"
        )
        state["current_state"] = "PAYMENT"
    else:
        state["agent_response"] = "Please provide your full shipping address (including house number, street name, city, and pincode) so we can calculate delivery."
        state["current_state"] = "ADDRESS_COLLECTION"
        
    return state

def payment_node(state: SalesState) -> SalesState:
    logger.info("Running payment_node")
    product = supabase_svc.get_product(state["product_id"])
    price = product.get("price", 999.00) if product else 999.00
    
    # Create a draft order record in Supabase
    order = supabase_svc.create_order(
        lead_id=state["lead_id"],
        product_id=state["product_id"],
        amount=price,
        address=state["customer_info"].get("address", "Standard Delivery"),
        status="pending"
    )
    
    state["order_id"] = order["id"]
    
    import os
    public_url = os.getenv("PUBLIC_URL") or os.getenv("APP_BASE_URL") or "http://localhost:8000"
    if "host.docker.internal" in public_url:
        public_url = public_url.replace("host.docker.internal", "localhost")
    if not public_url.endswith("/"):
        public_url += "/"
    pay_url = f"{public_url}payment/simulate?order_id={order['id']}&amount={price:.2f}"
    
    state["agent_response"] = (
        f"Awesome! I have generated a payment request for Rs. {price:.2f}.\n\n"
        f"👉 [PAY NOW WITH UPI]({pay_url})\n\n"
        "Please let me know once you have completed the payment so I can confirm your order."
    )
    state["current_state"] = "ORDER_CONFIRMED"
    return state

def order_confirmed_node(state: SalesState) -> SalesState:
    logger.info("Running order_confirmed_node")
    # Transition to paid status
    if state["order_id"]:
        supabase_svc.update_order_status(state["order_id"], "paid", "TXN_MOCK_" + state["order_id"][:8].upper())
        
        # Increment conversion analytics
        lead = supabase_svc.get_leads()
        lead_data = next((l for l in lead if l["id"] == state["lead_id"]), {})
        business_id = lead_data.get("business_id")
        if business_id:
            try:
                supabase_svc.increment_analytics(business_id, "total_conversions", 1)
            except Exception as e:
                logger.error(f"Failed to increment conversion analytics: {e}")
    
    state["agent_response"] = (
        "🎉 Payment Received! Thank you for your purchase. "
        "Your order is confirmed and will be shipped within 24 hours. "
        "A tracking link will be sent to your number. Have a wonderful day!"
    )
    state["current_state"] = "COMPLETE"
    return state

def escalate_node(state: SalesState) -> SalesState:
    logger.info("Running escalate_node")
    state["agent_response"] = (
        "I understand you have custom requirements. I am escalating this conversation "
        "to the business owner. They will reach out to you directly on WhatsApp shortly. Thank you!"
    )
    state["current_state"] = "ESCALATE"
    return state

# --- Routing Logic ---

def route_next(state: SalesState) -> str:
    """Router function to analyze message and direct to appropriate state node."""
    msg = state["user_message"].lower()
    curr = state["current_state"]
    
    # Global escape to human
    if any(w in msg for w in ["human", "agent", "owner", "call me", "talk to support", "complaint"]):
        return "escalate"

    if curr == "WELCOME":
        return "welcome"
    elif curr == "PRODUCT_INFO":
        if any(w in msg for w in ["yes", "show me", "price", "info", "details", "tell me"]):
            return "product_info"
        return "qa_loop"
    elif curr == "QA_LOOP":
        if any(w in msg for w in ["buy", "order", "purchase", "want to buy", "get it"]):
            return "address_collection"
        return "qa_loop"
    elif curr == "ADDRESS_COLLECTION":
        return "address_collection"
    elif curr == "PAYMENT":
        return "payment"
    elif curr == "ORDER_CONFIRMED":
        if any(w in msg for w in ["paid", "done", "completed", "sent", "success"]):
            return "order_confirmed"
        return "payment"
    
    return END

# --- Build LangGraph State Machine ---

workflow = StateGraph(SalesState)

# Add nodes
workflow.add_node("welcome", welcome_node)
workflow.add_node("product_info", product_info_node)
workflow.add_node("qa_loop", qa_loop_node)
workflow.add_node("address_collection", address_collection_node)
workflow.add_node("payment", payment_node)
workflow.add_node("order_confirmed", order_confirmed_node)
workflow.add_node("escalate", escalate_node)

# Set conditional entrypoint and routing
workflow.set_conditional_entry_point(
    route_next,
    {
        "welcome": "welcome",
        "product_info": "product_info",
        "qa_loop": "qa_loop",
        "address_collection": "address_collection",
        "payment": "payment",
        "order_confirmed": "order_confirmed",
        "escalate": "escalate"
    }
)

# Set edges
workflow.add_edge("welcome", END)
workflow.add_edge("product_info", END)
workflow.add_edge("qa_loop", END)
workflow.add_edge("address_collection", END)
workflow.add_edge("payment", END)
workflow.add_edge("order_confirmed", END)
workflow.add_edge("escalate", END)

# Compile
compiled_sales_flow = workflow.compile()

# --- Public Interface Wrapper ---

def run_sales_chat(lead_id: str, product_id: str, user_message: str) -> Dict[str, Any]:
    """
    Executes a chat message step against the sales graph,
    updating and persisting state in Supabase.
    """
    # 1. Fetch or create conversation record
    conv = supabase_svc.get_conversation_by_lead(lead_id)
    if not conv:
        conv = supabase_svc.create_conversation(lead_id=lead_id, state="WELCOME", history=[])
        
    current_state_val = conv.get("state", "WELCOME")
    history = conv.get("history", [])

    # 2. Append user message to history
    if user_message:
        history.append({"role": "user", "content": user_message})

    # Find address inside custom info
    customer_info = {"address": ""}
    for msg in history:
        if msg["role"] == "assistant" and "recorded your delivery address" in msg["content"]:
            # Address already recorded
            pass

    # Extract order_id if present
    order_id = ""
    orders = supabase_svc.get_orders()
    for o in orders:
        if o["lead_id"] == lead_id and o["product_id"] == product_id:
            order_id = o["id"]

    # 3. Create graph input state
    inputs = SalesState(
        lead_id=lead_id,
        product_id=product_id,
        current_state=current_state_val,
        chat_history=history,
        user_message=user_message or "",
        agent_response="",
        customer_info=customer_info,
        order_id=order_id
    )

    # 4. Execute graph step
    result_state = compiled_sales_flow.invoke(inputs)

    # 5. Append agent response to history and save state
    history.append({"role": "assistant", "content": result_state["agent_response"]})
    
    supabase_svc.update_conversation(
        conversation_id=conv["id"],
        state=result_state["current_state"],
        history=history
    )

    # If state transitioned to Escalate, we update lead status
    if result_state["current_state"] == "ESCALATE":
        supabase_svc.update_lead_status(lead_id, "lost") # escalate flag
    elif result_state["current_state"] == "COMPLETE":
        supabase_svc.update_lead_status(lead_id, "customer")

    return {
        "response": result_state["agent_response"],
        "next_state": result_state["current_state"],
        "history": history
    }
