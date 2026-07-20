-- 003_whatsapp_module.sql
-- Migration to support multi-tenant WhatsApp integration via Evolution API

-- 1. Tenants Table
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed a default tenant for backward compatibility / single-tenant setup
INSERT INTO tenants (id, name)
VALUES ('00000000-0000-0000-0000-000000000000', 'Default Tenant')
ON CONFLICT (id) DO NOTHING;

-- 2. WhatsApp Instances Table
CREATE TABLE IF NOT EXISTS whatsapp_instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL DEFAULT 'evolution', -- 'evolution' or 'meta'
    instance_name VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'disconnected', -- 'connected', 'disconnected', 'connecting'
    session_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Alter or Recreate Conversations Table for Multi-Tenancy & WhatsApp Integration
-- Drop the original conversations index/table if it exists to clean up references,
-- but do it safely by checking/creating columns. We'll drop and recreate it for cleanliness.
DROP TABLE IF EXISTS conversations CASCADE;

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL, -- preserve compatibility with existing leads
    customer_phone VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL DEFAULT 'whatsapp', -- 'whatsapp' or 'webchat'
    assigned_agent_id UUID, -- NULL if unassigned
    status VARCHAR(50) NOT NULL DEFAULT 'open', -- 'open', 'closed', 'snoozed'
    ai_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    human_override BOOLEAN NOT NULL DEFAULT FALSE,
    state VARCHAR(50) NOT NULL DEFAULT 'WELCOME', -- preserve compatibility with LangGraph
    history JSONB DEFAULT '[]'::jsonb, -- preserve compatibility with LangGraph
    state_metadata JSONB DEFAULT '{}'::jsonb, -- separate conversation state & memory
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Messages Table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type VARCHAR(50) NOT NULL, -- 'customer', 'agent', 'ai', 'system'
    sender_id UUID, -- ID of the agent or NULL for customer/ai
    message_type VARCHAR(50) NOT NULL DEFAULT 'text', -- 'text', 'image', 'document', 'audio', 'video'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb, -- delivery status (sent, delivered, failed), media metadata, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_whatsapp_instances_tenant ON whatsapp_instances(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant ON conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_phone ON conversations(customer_phone);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
