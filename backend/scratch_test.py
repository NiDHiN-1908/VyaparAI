import os
import sys
# Make sure backend package can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.supabase_service import supabase_svc
from backend.modules.conversation_module.conversation_repository import conversation_repo

def run_tests():
    print("==================================================")
    print("   RUNNING AUTOMATED CHECKS FOR WHATSAPP INTEGRATION")
    print("==================================================")
    
    tenant_id = "00000000-0000-0000-0000-000000000000"
    
    # 1. Clean up first
    print("\n1. Cleaning up existing test records...")
    supabase_svc.delete_all_conversations(tenant_id)
    print("[OK] Local database cleared successfully.")
    
    # 2. Seed test instances
    print("\n2. Seeding WhatsApp instances...")
    # First instance (active/connected)
    inst_a = supabase_svc.create_whatsapp_instance(
        tenant_id=tenant_id,
        provider="evolution",
        instance_name="kochi_spice_whatsapp",
        status="connected"
    )
    print(f"[OK] Created connected instance: {inst_a['instance_name']}")
    
    # 3. Create conversations mapped to different instances
    print("\n3. Creating conversations with instance_name association...")
    # Conv A - belongs to kochi_spice_whatsapp
    conv_a = conversation_repo.create(
        tenant_id=tenant_id,
        phone="917306796590",
        channel="whatsapp",
        instance_name="kochi_spice_whatsapp"
    )
    print(f"[OK] Created conversation for kochi_spice_whatsapp: ID {conv_a['id']}")
    
    # Conv B - legacy conversation (no instance_name)
    conv_b = conversation_repo.create(
        tenant_id=tenant_id,
        phone="919876543210",
        channel="whatsapp",
        instance_name=None
    )
    print(f"[OK] Created legacy conversation (no instance_name): ID {conv_b['id']}")

    # 4. Add messages to conv_a
    print("\n4. Seeding messages for conversation A...")
    msg_1 = supabase_svc.create_message(
        conversation_id=conv_a["id"],
        sender_type="agent",
        content="Hello, this is Green Haven Nursery!"
    )
    msg_2 = supabase_svc.create_message(
        conversation_id=conv_a["id"],
        sender_type="customer",
        content="Hi! I want to order a Fiddle Leaf Fig plant."
    )
    print("[OK] Seeded messages.")

    # 5. Check conversations list and filtering
    print("\n5. Checking active instance filtering...")
    # Since kochi_spice_whatsapp is connected, it should return both conversations
    # (conv_b is legacy, so it should dynamically bind to the active instance)
    convs = conversation_repo.get_all(tenant_id)
    print(f"   Active instance name: kochi_spice_whatsapp")
    print(f"   Found conversations: {[c['customer_phone'] for c in convs]}")
    for c in convs:
        print(f"   Conversation +{c['customer_phone']} instance_name: {c.get('instance_name')}")
        assert c.get("instance_name") == "kochi_spice_whatsapp", "Should bind to active instance"
        
    # Now let's change active instance to a new one: kochi_farm_whatsapp
    print("\nSwitching active instance...")
    supabase_svc.update_whatsapp_instance_status(inst_a["id"], "disconnected")
    inst_b = supabase_svc.create_whatsapp_instance(
        tenant_id=tenant_id,
        provider="evolution",
        instance_name="kochi_farm_whatsapp",
        status="connected"
    )
    print(f"[OK] Created new connected instance: {inst_b['instance_name']}")
    
    # Fetching conversations again should return an empty list because the conversations
    # are associated with kochi_spice_whatsapp, not kochi_farm_whatsapp!
    convs_new = conversation_repo.get_all(tenant_id)
    print(f"   Active instance name: kochi_farm_whatsapp")
    print(f"   Found conversations for new instance: {[c['customer_phone'] for c in convs_new]}")
    assert len(convs_new) == 0, "Should hide conversations belonging to other instances"
    print("[OK] Filtering checks passed successfully.")

    # Switch back to spice to test editing and deletion
    supabase_svc.update_whatsapp_instance_status(inst_b["id"], "disconnected")
    supabase_svc.update_whatsapp_instance_status(inst_a["id"], "connected")

    # 6. Test editing a message
    print("\n6. Testing Message Editing...")
    print(f"   Original message 1 content: '{msg_1['content']}'")
    edited_msg = supabase_svc.edit_message(msg_1["id"], "Hello! Welcome to Green Haven nursery!")
    print(f"   Edited message 1 content: '{edited_msg['content']}'")
    print(f"   Message 1 metadata: {edited_msg['metadata']}")
    assert edited_msg["content"] == "Hello! Welcome to Green Haven nursery!", "Content should update"
    assert edited_msg["metadata"].get("edited") is True, "Edited flag should be True"
    assert len(edited_msg["metadata"].get("edit_history", [])) == 1, "Should record history"
    assert edited_msg["metadata"]["edit_history"][0]["content"] == "Hello, this is Green Haven Nursery!", "Should store original content in history"
    print("[OK] Message editing checks passed.")

    # 7. Test deleting individual conversation
    print("\n7. Testing Individual Conversation Deletion...")
    success_del = conversation_repo.delete_by_id(conv_b["id"])
    print(f"   Deleted conversation B: {success_del}")
    remaining_convs = conversation_repo.get_all(tenant_id)
    print(f"   Remaining conversations: {[c['customer_phone'] for c in remaining_convs]}")
    assert len(remaining_convs) == 1, "Only conversation A should remain"
    assert remaining_convs[0]["id"] == conv_a["id"], "Should be conversation A"
    print("[OK] Individual deletion checks passed.")

    # 8. Test clearing all conversations
    print("\n8. Testing Clear All Conversations...")
    success_clear = conversation_repo.delete_all(tenant_id)
    print(f"   Cleared all conversations: {success_clear}")
    final_convs = conversation_repo.get_all(tenant_id)
    print(f"   Final conversations: {final_convs}")
    assert len(final_convs) == 0, "No conversations should remain"
    
    # Check messages count (should be empty due to ON DELETE CASCADE or deletion logic)
    all_msgs = supabase_svc._select_all("messages")
    print(f"   Remaining messages in database: {all_msgs}")
    assert len(all_msgs) == 0, "All messages should be deleted"
    print("[OK] Clear all conversations checks passed.")

    print("\n==================================================")
    print("        ALL AUTOMATED VERIFICATION CHECKS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
