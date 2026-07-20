# backend/langgraph/sales_workflow.py
import logging
import json
from typing import TypedDict, List, Dict, Any, Optional
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
    # Memory fields
    previous_state: str
    customer_preferences: Dict[str, Any]
    products_discussed: List[str]
    questions_answered: List[str]
    address_info: str
    payment_status: str
    conversation_summary: str


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
    
    # Update Memory
    if "products_discussed" not in state or not state["products_discussed"]:
        state["products_discussed"] = []
    if prod_name not in state["products_discussed"]:
        state["products_discussed"].append(prod_name)
    
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

    # Update Memory
    if "products_discussed" not in state or not state["products_discussed"]:
        state["products_discussed"] = []
    if prod_name not in state["products_discussed"]:
        state["products_discussed"].append(prod_name)

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
    all_products = supabase_svc.get_products()
    product = supabase_svc.get_product(state["product_id"])
    
    # Check if user message inquires about another product in our store catalog
    msg_lower = state["user_message"].lower()
    matched_product = None
    for p in all_products:
        pname = p.get("name", "").lower()
        if not pname:
            continue
        tokens = [t for t in pname.split() if len(t) > 3]
        if pname in msg_lower or any(t in msg_lower for t in tokens):
            matched_product = p
            break

    if matched_product:
        product = matched_product
        state["product_id"] = matched_product["id"]

    prod_name = product.get("name", "Product") if product else "Product"
    prod_price = product.get("price", 999.00) if product else 999.00
    prod_desc = product.get("description", "") if product else ""

    # Update Memory
    if "products_discussed" not in state or not state["products_discussed"]:
        state["products_discussed"] = []
    if prod_name not in state["products_discussed"]:
        state["products_discussed"].append(prod_name)

    # Format full store catalog context so LLM knows every available product
    catalog_summary = []
    for p in all_products:
        catalog_summary.append(f"• {p.get('name')}: Rs. {p.get('price', 0)} - {p.get('description', '')}")
    catalog_text = "\n".join(catalog_summary)

    try:
        # Retrieve context from RAG Service
        rag_context = rag_svc.retrieve(state["user_message"])
        
        llm = get_ollama_llm()
        history = format_history(state["chat_history"])
        
        prompt = (
            f"You are a helpful and knowledgeable sales assistant representing our business.\n"
            f"OUR FULL STORE PRODUCT CATALOG:\n{catalog_text}\n\n"
            f"Currently requested item: {prod_name}.\n"
            f"Item Price: Rs. {prod_price:.2f}.\n"
            f"Item Description: {prod_desc}.\n"
            f"Previous Chat History:\n{history}\n"
        )
        
        if rag_context:
            prompt += f"\nCOMPANY KNOWLEDGE BASE:\n{rag_context}\n\n"
            
        prompt += (
            f"Customer Message: \"{state['user_message']}\"\n\n"
            "INSTRUCTIONS:\n"
            "1. Formulate a warm, polite, and helpful response answering their specific query or objection.\n"
            "2. If the customer asks about any other product in our catalog, use the catalog above to provide accurate price, details, and care guidelines.\n"
            "3. If the customer asks about plant care (sunlight, watering, toxicity), use your pre-trained horticultural knowledge for that specific plant species.\n"
            "4. DO NOT ask for their shipping address unless they explicitly show intent to buy (e.g. asking to order, saying yes to buy).\n"
            "5. If they are just asking questions, answer clearly and ask if they would like to place an order for that product."
        )
        response = llm.invoke(prompt).content
    except Exception as e:
        logger.warning(f"Ollama prediction failed in qa_loop: {e}. Using rule-based fallback.")
        msg = state["user_message"].lower()
        if "discount" in msg or "price" in msg or "cost" in msg or "how much" in msg:
            response = f"The price of {prod_name} is Rs. {prod_price:.2f}. We offer free delivery all across India! Would you like to buy it now?"
        elif matched_product or any(p.get("name", "").lower() in msg for p in all_products):
            target_p = matched_product or product
            p_n = target_p.get("name", "Product")
            p_pr = target_p.get("price", 999.00)
            p_ds = target_p.get("description", "")
            response = f"Yes! We have {p_n} available for Rs. {p_pr:.2f}. {p_ds} Would you like to place an order for {p_n}?"
        elif "quality" in msg or "warranty" in msg or "guarantee" in msg:
            response = f"We guarantee 100% genuine quality for {prod_name}. If you face any issues, we have a 7-day replacement policy. Are you ready to order?"
        elif "ingredients" in msg or "what is" in msg or "details" in msg or "organic" in msg:
            response = f"Our {prod_name} is of premium quality ({prod_desc}). Would you like to order it now?"
        elif "where" in msg or "address" in msg or "location" in msg or "shop" in msg:
            response = f"We ship our products directly to your doorstep all over India. Where are you located so we can calculate shipping?"
        elif "buy" in msg or "order" in msg or "purchase" in msg or "want" in msg:
            response = f"Great! Please provide your full shipping address (including house number, street name, city, and pincode) so I can create your order for {prod_name}."
        else:
            response = f"Thank you for asking! We have {prod_name} (Rs. {prod_price:.2f}) and other items in our catalog available. Could you please specify your question, or would you like to proceed with an order?"

    state["agent_response"] = response
    return state

def extract_distance(msg: str) -> Optional[float]:
    import re
    # Match patterns like "5 km", "4.5km", "12 kilometers", "3.2kms"
    matches = re.findall(r'\b(\d+(?:\.\d+)?)\s*(?:km|kms|kilometer|kilometers|kilometre|kilometres|km\b)\b', msg.lower())
    if matches:
        try:
            return float(matches[0])
        except ValueError:
            pass
    return None

def get_estimated_distance(address: str) -> float:
    import hashlib
    # Hash address to get a stable, pseudo-random distance between 2.0 and 15.0 km
    hash_val = int(hashlib.md5(address.encode('utf-8')).hexdigest(), 16)
    distance = 2.0 + (hash_val % 131) / 10.0  # Generates a float between 2.0 and 15.1
    return round(distance, 1)

def extract_quantity(chat_history: List[Dict[str, str]], current_message: str) -> int:
    import re
    # Combine history and current message to search for quantity
    all_texts = [current_message]
    for m in reversed(chat_history):
        if m.get("role") in ["user", "assistant"]:
            all_texts.append(m.get("content", ""))
            
    for text in all_texts:
        text_lc = text.lower()
        # Look for "quantity: 3" or "qty: 3"
        matches = re.findall(r'\b(?:quantity|qty)[:\s]*(\d+)\b', text_lc)
        if matches:
            return int(matches[0])
        # Look for "3 plants", "3 roses", "3 units", "3 of them"
        matches = re.findall(r'\b(\d+)\s*(?:plant|rose|jasmine|flower|unit|item|copy|pack|piece|qty|qty|of\s+them|of\s+those|them|those)s?\b', text_lc)
        if matches:
            return int(matches[0])
            
    return 1 # Default quantity

def count_past_orders(lead_id: str) -> int:
    try:
        leads = supabase_svc.get_leads()
        current_lead = next((l for l in leads if l["id"] == lead_id), None)
        if not current_lead:
            return 0
        username = current_lead.get("username")
        if not username:
            return 0
        
        # Get all lead IDs for this username
        user_lead_ids = {l["id"] for l in leads if l.get("username") == username}
        
        # Count orders for these leads that are paid/completed/shipped
        orders = supabase_svc.get_orders()
        past_orders_count = sum(
            1 for o in orders 
            if o.get("lead_id") in user_lead_ids and o.get("status") in ["paid", "completed", "shipped", "delivered"]
        )
        return past_orders_count
    except Exception as e:
        logger.error(f"Error counting past orders: {e}")
        return 0

def validate_address_completeness(msg: str, chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """Strictly validates if a user provided complete delivery details (Name, House/Street, District/City, and 6-digit Pincode)."""
    import re
    msg_clean = msg.strip()
    
    # Combine current message with previous user messages to check for details provided across multiple lines/chats
    full_text = msg_clean
    for h in reversed(chat_history[-4:]):
        if h.get("role") == "user":
            full_text += " " + h.get("content", "").strip()
            
    # 1. Pincode Check: Must contain a valid 6-digit Indian PIN code (e.g. 686001, 682016, 110001, 680001)
    pincode_match = re.search(r'\b[1-9][0-9]{5}\b', full_text)
    has_pincode = pincode_match is not None
    pincode_val = pincode_match.group(0) if pincode_match else None
    
    # 2. House / Street / Door No. / Landmark Check
    street_kw = ['house', 'flat', 'door', 'street', 'road', 'lane', 'near', 'opp', 'opposite', 'building', 'colony', 'nagar', 'villa', 'apartment', 'po', 'p.o', 'post', 'junction', 'cross', 'bhavan', 'mandiram', 'nivas', 'no', 'number', 'no.', '#']
    has_street = any(kw in full_text.lower() for kw in street_kw) or (any(char.isdigit() for char in full_text) and len(full_text) > 15)
    
    # 3. District / City / Town Check
    words = [w for w in re.split(r'[\s,.\-\n]+', full_text) if len(w) > 2]
    has_city = len(words) >= 3
    
    missing_fields = []
    if not has_pincode:
        missing_fields.append("📮 **6-Digit Pincode** (e.g. 686001)")
    if not has_street:
        missing_fields.append("🏠 **House Name / Door No. & Street / Landmark**")
    if not has_city:
        missing_fields.append("📍 **District / City / Town**")
        
    is_complete = has_pincode and has_street and has_city
    return {
        "is_complete": is_complete,
        "missing_fields": missing_fields,
        "pincode": pincode_val,
        "address": msg_clean
    }

def address_collection_node(state: SalesState) -> SalesState:
    logger.info("Running address_collection_node")
    msg = state["user_message"]
    
    address_val = validate_address_completeness(msg, state.get("chat_history", []))
    
    if not address_val["is_complete"]:
        missing_str = "\n".join([f"• {f}" for f in address_val["missing_fields"]])
        state["agent_response"] = (
            "Thank you! 🙏 To make sure your parcel is delivered safely to your doorstep without delay, "
            "we require your **complete delivery details**:\n\n"
            f"⚠️ **Missing Details Needed:**\n{missing_str}\n\n"
            "Please reply with your complete details in this format:\n"
            "👤 **Full Name:**\n"
            "🏠 **House Name / Door No. & Street / Landmark:**\n"
            "📍 **District / City:**\n"
            "📮 **6-Digit Pincode:**"
        )
        state["current_state"] = "ADDRESS_COLLECTION"
        return state

    import os
    import json
    
    # Load delivery config
    config_file = "nursery_delivery_config.json"
    config = {
        "enabled": True,
        "free_min_distance": 5.0,
        "free_max_distance": 10.0,
        "charge_under_5km_per_km": 10.0,
        "charge_over_10km_per_km": 15.0,
        "huge_purchase_min_amount": 1500.0,
        "huge_purchase_discount_pct": 10.0,
        "permanent_customer_min_orders": 5,
        "permanent_customer_discount_pct": 15.0
    }
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
        except Exception:
            pass
            
    # Proceed with order calculations
    state["customer_info"]["address"] = msg
    state["address_info"] = msg  # Update Memory
    
    # Calculate shipping charge dynamically
    product = supabase_svc.get_product(state["product_id"])
    price = product.get("price", 999.00) if product else 999.00
    
    # Determine distance
    distance = extract_distance(msg)
    is_estimated = False
    if distance is None:
        distance = get_estimated_distance(msg)
        is_estimated = True
        
    shipping_cost = 0.0
    shipping_msg = "Free Delivery"
    
    if config.get("enabled", True):
        min_dist = config.get("free_min_distance", 5.0)
        max_dist = config.get("free_max_distance", 10.0)
        if min_dist <= distance <= max_dist:
            shipping_cost = 0.0
            shipping_msg = f"Free Delivery (within {min_dist}-{max_dist} km)"
        elif distance < min_dist:
            rate = config.get("charge_under_5km_per_km", 10.0)
            shipping_cost = round(distance * rate, 2)
            shipping_msg = f"Rs. {int(shipping_cost)} shipping ({distance} km is under {min_dist} km limit)"
        else:
            rate = config.get("charge_over_10km_per_km", 15.0)
            shipping_cost = round(distance * rate, 2)
            shipping_msg = f"Rs. {int(shipping_cost)} shipping ({distance} km is over {max_dist} km limit)"
    else:
        shipping_cost = 0.0
        shipping_msg = "Free Delivery (Rules disabled)"
        
    # Determine quantity
    quantity = extract_quantity(state["chat_history"], msg)
    subtotal = price * quantity
    
    # Discounts calculation
    huge_purchase_discount = 0.0
    huge_purchase_msg = ""
    min_amount = config.get("huge_purchase_min_amount", 1500.0)
    if subtotal >= min_amount or quantity >= 3:
        huge_pct = config.get("huge_purchase_discount_pct", 10.0)
        huge_purchase_discount = round(subtotal * (huge_pct / 100.0), 2)
        huge_purchase_msg = f"Huge Purchase Discount ({int(huge_pct)}%): -Rs. {int(huge_purchase_discount)}"

    permanent_discount = 0.0
    permanent_msg = ""
    past_orders = count_past_orders(state["lead_id"])
    min_orders = config.get("permanent_customer_min_orders", 5)
    if past_orders > min_orders:
        perm_pct = config.get("permanent_customer_discount_pct", 15.0)
        permanent_discount = round(subtotal * (perm_pct / 100.0), 2)
        permanent_msg = f"Permanent Customer Loyalty Discount ({int(perm_pct)}%): -Rs. {int(permanent_discount)}"
        
    total_discount = huge_purchase_discount + permanent_discount
    total_cost = max(0.0, subtotal - total_discount + shipping_cost)
    
    # Save details to customer_info so payment_node can access it
    state["customer_info"].update({
        "address": msg,
        "quantity": quantity,
        "subtotal": subtotal,
        "distance": distance,
        "is_estimated_distance": is_estimated,
        "shipping_cost": shipping_cost,
        "huge_purchase_discount": huge_purchase_discount,
        "permanent_discount": permanent_discount,
        "total_discount": total_discount,
        "total_cost": total_cost,
        "past_orders_count": past_orders
    })
    
    # Build breakdown lines
    breakdown_lines = [
        f"Quantity: {quantity}x",
        f"Subtotal: Rs. {int(subtotal)}"
    ]
    if huge_purchase_discount > 0:
        breakdown_lines.append(f"• {huge_purchase_msg}")
    if permanent_discount > 0:
        breakdown_lines.append(f"• {permanent_msg} (Loyal customer with {past_orders} past orders!)")
    
    dist_suffix = " *(estimated)*" if is_estimated else ""
    breakdown_lines.append(f"• Distance: {distance} km{dist_suffix}")
    breakdown_lines.append(f"• Delivery Charge: {shipping_msg}")
    breakdown_lines.append(f"• **Order Total: Rs. {int(total_cost)}**")
    
    breakdown_text = "\n".join(breakdown_lines)
    
    state["agent_response"] = (
        f"Thank you! I have verified your complete shipping address:\n\"{msg}\"\n\n"
        f"Here is your order summary:\n"
        f"{breakdown_text}\n\n"
        "Shall I generate your UPI payment link to complete the order?"
    )
    state["current_state"] = "PAYMENT"
    return state
        
    return state

def payment_node(state: SalesState) -> SalesState:
    logger.info("Running payment_node")
    product = supabase_svc.get_product(state["product_id"])
    price = product.get("price", 999.00) if product else 999.00
    
    # Retrieve computed total cost from customer_info, default to price
    total_cost = state["customer_info"].get("total_cost", price)
    
    # Create a draft order record in Supabase
    order = supabase_svc.create_order(
        lead_id=state["lead_id"],
        product_id=state["product_id"],
        amount=total_cost,
        address=state["customer_info"].get("address") or state.get("address_info") or "Standard Delivery",
        status="pending"
    )
    
    state["order_id"] = order["id"]
    state["payment_status"] = "pending"  # Update Memory
    
    import os
    public_url = os.getenv("PUBLIC_URL") or os.getenv("APP_BASE_URL") or "http://localhost:8000"
    if "host.docker.internal" in public_url:
        public_url = public_url.replace("host.docker.internal", "localhost")
    if not public_url.endswith("/"):
        public_url += "/"
    pay_url = f"{public_url}payment/simulate?order_id={order['id']}&amount={total_cost:.2f}"
    
    state["agent_response"] = (
        f"Awesome! I have generated a payment request for Rs. {total_cost:.2f}.\n\n"
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
        state["payment_status"] = "paid"  # Update Memory
        
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

def interruption_node(state: SalesState) -> SalesState:
    logger.info(f"Running interruption_node for stage: {state['current_state']}")
    
    product = supabase_svc.get_product(state["product_id"])
    prod_name = product.get("name", "Product") if product else "Product"
    prod_price = product.get("price", 999.00) if product else 999.00
    prod_desc = product.get("description", "") if product else ""
    
    # Retrieve general knowledge layers from RAG service
    rag_context = rag_svc.retrieve(state["user_message"])
    
    # Check if there are active orders
    order_info = ""
    if state["lead_id"]:
        try:
            orders = supabase_svc.get_orders()
            active_order = next((o for o in orders if o["lead_id"] == state["lead_id"] and o["product_id"] == state["product_id"]), None)
            if active_order:
                order_info = f"Active Order Status: {active_order['status']}, Order ID: {active_order['id']}, Amount: Rs. {active_order['amount']:.2f}, Shipping Address: {active_order.get('address') or 'not set'}."
        except Exception as oe:
            logger.error(f"Failed to fetch active order: {oe}")
            
    history = format_history(state["chat_history"])
    current_stage = state["current_state"]
    
    resume_instruction = ""
    if current_stage == "WELCOME":
        resume_instruction = "After answering the question, ask them if they want to hear more details or features of the plant."
    elif current_stage == "PRODUCT_INFO":
        resume_instruction = "After answering the question, ask them if they would like to place an order or if they have other questions."
    elif current_stage == "QA_LOOP":
        resume_instruction = "After answering the question, ask them if they are ready to proceed with ordering."
    elif current_stage == "ADDRESS_COLLECTION":
        resume_instruction = "After answering the question, ask them politely to provide their full shipping address so you can create their order."
    elif current_stage == "PAYMENT" or current_stage == "ORDER_CONFIRMED":
        resume_instruction = "After answering the question, ask them if they can proceed with completing the payment using the link provided."
    elif current_stage == "COMPLETE":
        resume_instruction = "No need to prompt for purchase as the order is already confirmed. Wish them a great day!"
        
    prompt = (
        "You are an intelligent sales assistant for Green Haven Nursery.\n"
        "The customer has interrupted the checkout flow to ask a question.\n"
        "Your task is to:\n"
        "1. Answer their question/objection accurately and politely using the retrieved context below.\n"
        "2. Seamlessly prompt them to return to the current checkout stage using the instructions below.\n\n"
        "RETIREVED KNOWLEDGE LAYERS:\n"
        f"--- PRODUCT DETAILS ---\n"
        f"Name: {prod_name}\n"
        f"Description: {prod_desc}\n"
        f"Price: Rs. {prod_price:.2f}\n\n"
    )
    
    if order_info:
        prompt += f"--- CUSTOMER ORDER STATUS ---\n{order_info}\n\n"
        
    if rag_context:
        prompt += f"--- COMPANY & POLICIES KNOWLEDGE BASE ---\n{rag_context}\n\n"
        
    prompt += (
        f"--- CONVERSATION HISTORY ---\n{history}\n\n"
        f"Current Sales Workflow Stage: {current_stage}\n"
        f"Customer Message: \"{state['user_message']}\"\n\n"
        f"RESUME INSTRUCTIONS:\n{resume_instruction}\n\n"
        "GUIDELINES:\n"
        "- Do not make up facts. Only use the provided knowledge layers to answer.\n"
        "- Respond in a natural, friendly, and helpful tone.\n"
        "- Ensure the transition back to the sales stage is smooth and not robotic.\n"
        "- Do not say things like 'Based on the context provided' or 'According to the knowledge base'."
    )
    
    try:
        llm = get_ollama_llm()
        response = llm.invoke(prompt).content
    except Exception as e:
        logger.error(f"Failed to generate response in interruption_node: {e}")
        response = "I'm happy to help with that! Let me get you that information. Could we also finish setting up your delivery details?"
        
    state["agent_response"] = response
    
    # Store questions answered / preferences update in memory
    if "questions_answered" not in state or not state["questions_answered"]:
        state["questions_answered"] = []
    state["questions_answered"].append(state["user_message"])
    
    # Keep track of previous stage in memory
    state["previous_state"] = state["current_state"]
    
    # Stay in the same current state!
    # This prevents stage-locking and preserves current checkout stage progress
    return state


# --- Routing Logic ---

def classify_intent_via_llm(user_message: str, current_state: str, history_str: str) -> str:
    try:
        llm = get_ollama_llm()
        prompt = (
            "You are a sales routing assistant for Green Haven Nursery.\n"
            "Analyze the customer's new message and determine their intent.\n\n"
            f"Current Workflow Stage: {current_state}\n"
            f"Chat History Context:\n{history_str}\n"
            f"Customer's New Message: \"{user_message}\"\n\n"
            "CLASSIFICATION OPTIONS:\n"
            "1. 'escalate': The customer wants to talk to a human agent, owner, support team, has a complaint, or is frustrated.\n"
            "2. 'interruption_question': The customer is asking a question or raising an objection (e.g. asking about dimensions, watering, care, nursery location, hours, return policy, delivery coverage, pricing, bulk/wholesale, website, etc.) rather than providing the information requested by the current stage.\n"
            "3. 'workflow_progress': The customer is answering the sales assistant's prompt, providing requested info (like their address, or saying they completed the payment), or saying yes/no to proceed with the purchase.\n\n"
            "Output exactly one word from the options above: 'escalate', 'interruption_question', or 'workflow_progress'. Do not include any other text, explanation, or punctuation."
        )
        response = llm.invoke(prompt).content.strip().lower()
        
        # Clean up response
        for option in ["escalate", "interruption_question", "workflow_progress"]:
            if option in response:
                return option
        return "workflow_progress" # default fallback
    except Exception as e:
        logger.warning(f"Ollama intent classification failed: {e}. Falling back to rule-based.")
        return "fallback"

def classify_intent_rule_based(user_message: str, current_state: str) -> str:
    msg = user_message.lower()
    
    # Escalation
    if any(w in msg for w in ["human", "agent", "owner", "call me", "talk to support", "complaint", "speak to someone"]):
        return "escalate"
        
    # Interruption question check
    is_question = "?" in msg or any(w in msg for w in [
        "what", "how", "why", "where", "when", "who", "do you", "is it", "does it", "can i", 
        "price", "cost", "location", "hours", "nursery", "delivery", "ship", "refund", "return", 
        "wholesale", "support", "contact", "phone", "email", "address", "fertilizer", "soil"
    ])
    
    if current_state == "ADDRESS_COLLECTION":
        has_address_indicators = len(msg) > 12 and any(char.isdigit() for char in msg)
        if not has_address_indicators:
            return "interruption_question"
            
    elif current_state == "ORDER_CONFIRMED":
        has_payment_confirmation = any(w in msg for w in ["paid", "done", "completed", "sent", "success", "payed"])
        if not has_payment_confirmation:
            return "interruption_question"
            
    if is_question:
        return "interruption_question"
        
    return "workflow_progress"

def route_next(state: SalesState) -> str:
    """Router function to analyze message and direct to appropriate state node."""
    msg = state["user_message"].lower()
    curr = state["current_state"]
    
    history_str = format_history(state["chat_history"])
    intent = classify_intent_via_llm(state["user_message"], curr, history_str)
    if intent == "fallback":
        intent = classify_intent_rule_based(state["user_message"], curr)
        
    logger.info(f"Classified customer message intent: {intent} (current state: {curr})")
    
    if intent == "escalate":
        return "escalate"
        
    if intent == "interruption_question":
        return "interruption"
        
    # Standard workflow progression
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
        if any(w in msg for w in ["paid", "done", "completed", "sent", "success", "payed"]):
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
workflow.add_node("interruption", interruption_node)

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
        "escalate": "escalate",
        "interruption": "interruption"
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
workflow.add_edge("interruption", END)

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

    # Load memory from state_metadata first
    state_metadata = conv.get("state_metadata") or {}
    if isinstance(state_metadata, str):
        try:
            state_metadata = json.loads(state_metadata)
        except Exception:
            state_metadata = {}
            
    memory = {
        "previous_state": "WELCOME",
        "customer_preferences": {},
        "products_discussed": [],
        "questions_answered": [],
        "address_info": "",
        "payment_status": "pending",
        "conversation_summary": ""
    }
    
    if state_metadata:
        memory.update(state_metadata)
    else:
        # Fallback to system_memory in messages if state_metadata is empty
        for msg in history:
            if msg.get("role") == "system_memory":
                try:
                    loaded_mem = json.loads(msg["content"])
                    memory.update(loaded_mem)
                except Exception as e:
                    logger.error(f"Failed to load system memory: {e}")

    # Build clean history
    clean_history = [msg for msg in history if msg.get("role") != "system_memory"]

    # Check if there is an existing completed order
    has_completed_order = False
    try:
        orders = supabase_svc.get_orders()
        for o in orders:
            if o["lead_id"] == lead_id and o["status"] in ["paid", "completed", "delivered"]:
                has_completed_order = True
                break
    except Exception as oe:
        logger.error(f"Failed to fetch orders for resume detection: {oe}")

    # Process user message if provided
    if user_message:
        clean_history.append({"role": "user", "content": user_message})

    # Resume handling
    if has_completed_order:
        if current_state_val == "WELCOME":
            # Transition to resume prompt and ask customer
            response = "I see that you have already completed an order with us. 🎉 Would you like to place a new order today, or do you have questions about your previous order?"
            clean_history.append({"role": "assistant", "content": response})
            supabase_svc.update_conversation_v2(
                conversation_id=conv["id"],
                updates={
                    "state": "RESUME_PROMPT",
                    "history": clean_history,
                    "state_metadata": memory
                }
            )
            return {
                "response": response,
                "next_state": "RESUME_PROMPT",
                "history": clean_history
            }
            
        elif current_state_val == "RESUME_PROMPT" and user_message:
            msg_lower = user_message.lower()
            is_new = any(w in msg_lower for w in ["new", "another", "fresh", "buy", "order", "place a new", "place new"])
            is_prev = any(w in msg_lower for w in ["previous", "old", "tracking", "status", "delivered", "paid", "last", "already"])
            
            if is_new:
                # Reset memory and order references
                logger.info("Customer requested new order. Resetting session.")
                current_state_val = "WELCOME"
                memory = {
                    "previous_state": "WELCOME",
                    "customer_preferences": {},
                    "products_discussed": [],
                    "questions_answered": [],
                    "address_info": "",
                    "payment_status": "pending",
                    "conversation_summary": ""
                }
                try:
                    if supabase_svc.is_mock:
                        from backend.services.supabase_service import MOCK_DB, save_mock_db
                        MOCK_DB["orders"] = [o for o in MOCK_DB.get("orders", []) if o.get("lead_id") != lead_id]
                        save_mock_db()
                    else:
                        supabase_svc.client.table("orders").delete().eq("lead_id", lead_id).execute()
                except Exception as ex:
                    logger.error(f"Failed to clear old orders for new session: {ex}")
            else:
                logger.info("Customer requested previous order or asked question. Routing to QA_LOOP.")
                current_state_val = "QA_LOOP"

    # Find address inside custom info / memory
    customer_info = {"address": memory.get("address_info", "")}

    # Extract order_id if present
    order_id = ""
    if current_state_val != "WELCOME":
        try:
            orders = supabase_svc.get_orders()
            for o in orders:
                if o["lead_id"] == lead_id and o["product_id"] == product_id:
                    order_id = o["id"]
        except Exception as oe:
            logger.error(f"Failed to get orders: {oe}")

    # 3. Create graph input state
    inputs = SalesState(
        lead_id=lead_id,
        product_id=product_id,
        current_state=current_state_val,
        chat_history=clean_history,
        user_message=user_message or "",
        agent_response="",
        customer_info=customer_info,
        order_id=order_id,
        previous_state=memory.get("previous_state", "WELCOME"),
        customer_preferences=memory.get("customer_preferences", {}),
        products_discussed=memory.get("products_discussed", []),
        questions_answered=memory.get("questions_answered", []),
        address_info=memory.get("address_info", ""),
        payment_status=memory.get("payment_status", "pending"),
        conversation_summary=memory.get("conversation_summary", "")
    )

    # 4. Execute graph step
    result_state = compiled_sales_flow.invoke(inputs)

    # Save updated memory back
    updated_memory = {
        "previous_state": result_state.get("previous_state", "WELCOME"),
        "customer_preferences": result_state.get("customer_preferences", {}),
        "products_discussed": result_state.get("products_discussed", []),
        "questions_answered": result_state.get("questions_answered", []),
        "address_info": result_state.get("address_info", ""),
        "payment_status": result_state.get("payment_status", "pending"),
        "conversation_summary": result_state.get("conversation_summary", "")
    }

    # 5. Append agent response to history and save state
    clean_history.append({"role": "assistant", "content": result_state["agent_response"]})

    # Save cleanly with state_metadata
    supabase_svc.update_conversation_v2(
        conversation_id=conv["id"],
        updates={
            "state": result_state["current_state"],
            "history": clean_history,
            "state_metadata": updated_memory
        }
    )

    # If state transitioned to Escalate, we update lead status
    if result_state["current_state"] == "ESCALATE":
        supabase_svc.update_lead_status(lead_id, "lost")
    elif result_state["current_state"] == "COMPLETE":
        supabase_svc.update_lead_status(lead_id, "customer")

    return {
        "response": result_state["agent_response"],
        "next_state": result_state["current_state"],
        "history": clean_history
    }

