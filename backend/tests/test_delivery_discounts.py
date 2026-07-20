import pytest
from unittest.mock import patch, MagicMock
from backend.langgraph.sales_workflow import (
    extract_distance,
    get_estimated_distance,
    extract_quantity,
    count_past_orders,
    address_collection_node,
    SalesState
)

# Test distance parsing
def test_extract_distance():
    assert extract_distance("Deliver to MG Road, 7 km") == 7.0
    assert extract_distance("Bannerghatta Road, distance 3.5km") == 3.5
    assert extract_distance("distance: 12 kms") == 12.0
    assert extract_distance("10 kilometers away") == 10.0
    assert extract_distance("Main Street, Delhi") is None

# Test deterministic distance estimation
def test_get_estimated_distance():
    addr1 = "123 Main St, Bangalore"
    addr2 = "456 Side St, Delhi"
    d1 = get_estimated_distance(addr1)
    d2 = get_estimated_distance(addr2)
    # Check that it's a float within expected range
    assert 2.0 <= d1 <= 15.1
    assert 2.0 <= d2 <= 15.1
    # Check that it's deterministic
    assert get_estimated_distance(addr1) == d1

# Test quantity extraction
def test_extract_quantity():
    # Current message containing quantity
    assert extract_quantity([], "I want 3 plants") == 3
    assert extract_quantity([], "give me 5 roses please") == 5
    assert extract_quantity([], "qty: 4") == 4
    # Quantity in conversation history
    history = [
        {"role": "user", "content": "I would like to order 2 jasmines"},
        {"role": "assistant", "content": "Sure, what is your address?"}
    ]
    assert extract_quantity(history, "My address is MG Road") == 2
    # Default fallback
    assert extract_quantity([], "No numbers here") == 1

# Test checkout fee and discount logic inside address_collection_node
@patch("backend.langgraph.sales_workflow.supabase_svc")
def test_address_collection_calculation(mock_supabase):
    # Setup mocks
    mock_supabase.get_product.return_value = {"id": "prod1", "name": "Rose Plant", "price": 1000.0}
    mock_supabase.get_leads.return_value = [{"id": "lead1", "username": "customer1"}]
    mock_supabase.get_orders.return_value = []
    
    # We will test address collection node for a regular customer buying 1 product at 7 km (Free Zone)
    state = SalesState(
        lead_id="lead1",
        product_id="prod1",
        current_state="ADDRESS_COLLECTION",
        chat_history=[{"role": "user", "content": "want to buy"}],
        user_message="Deliver to MG Road, distance: 7 km",
        agent_response="",
        customer_info={"address": ""},
        order_id="",
        previous_state="QA_LOOP",
        customer_preferences={},
        products_discussed=[],
        questions_answered=[],
        address_info="",
        payment_status="pending",
        conversation_summary=""
    )
    
    # Run node
    result = address_collection_node(state)
    
    # Assertions
    info = result["customer_info"]
    assert info["quantity"] == 1
    assert info["subtotal"] == 1000.0
    assert info["distance"] == 7.0
    assert info["shipping_cost"] == 0.0 # Free
    assert info["huge_purchase_discount"] == 0.0
    assert info["permanent_discount"] == 0.0
    assert info["total_cost"] == 1000.0
    assert result["current_state"] == "PAYMENT"
    assert "Free Delivery" in result["agent_response"]

@patch("backend.langgraph.sales_workflow.supabase_svc")
def test_address_collection_surcharges_and_discounts(mock_supabase):
    # Setup mock product (Rs. 1000.0)
    mock_supabase.get_product.return_value = {"id": "prod1", "name": "Rose Plant", "price": 1000.0}
    # Setup mock lead (customer1)
    mock_supabase.get_leads.return_value = [{"id": "lead1", "username": "customer1"}]
    # Setup mock orders: customer1 has 6 past completed orders, making them a permanent customer
    mock_supabase.get_orders.return_value = [
        {"lead_id": "lead1", "status": "paid"},
        {"lead_id": "lead1", "status": "paid"},
        {"lead_id": "lead1", "status": "completed"},
        {"lead_id": "lead1", "status": "completed"},
        {"lead_id": "lead1", "status": "paid"},
        {"lead_id": "lead1", "status": "paid"},
    ]
    
    # Customer orders 2 plants (Rs. 2000 subtotal -> huge purchase discount) and is a permanent customer at 12 km (outside free zone)
    state = SalesState(
        lead_id="lead1",
        product_id="prod1",
        current_state="ADDRESS_COLLECTION",
        chat_history=[
            {"role": "user", "content": "I want to buy 2 plants"},
            {"role": "assistant", "content": "Please provide address"}
        ],
        user_message="Deliver to Outer Ring Road, 12 km",
        agent_response="",
        customer_info={"address": ""},
        order_id="",
        previous_state="QA_LOOP",
        customer_preferences={},
        products_discussed=[],
        questions_answered=[],
        address_info="",
        payment_status="pending",
        conversation_summary=""
    )
    
    result = address_collection_node(state)
    info = result["customer_info"]
    
    assert info["quantity"] == 2
    assert info["subtotal"] == 2000.0
    assert info["distance"] == 12.0
    # Over 10km surcharge: 12 km * Rs. 15 = Rs. 180 shipping
    assert info["shipping_cost"] == 180.0
    # Huge purchase discount (10%): 10% of Rs. 2000 = Rs. 200
    assert info["huge_purchase_discount"] == 200.0
    # Permanent customer discount (15%): 15% of Rs. 2000 = Rs. 300
    assert info["permanent_discount"] == 300.0
    # Total cost = 2000 - 200 - 300 + 180 = 1680.0
    assert info["total_cost"] == 1680.0
    assert result["current_state"] == "PAYMENT"
