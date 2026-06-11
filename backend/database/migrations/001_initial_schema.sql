-- 001_initial_schema.sql
-- Expanded database schema for VyaparAI with campaign versioning

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Businesses table
CREATE TABLE IF NOT EXISTS businesses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    contact VARCHAR(50),
    industry VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(12, 2) NOT NULL,
    images TEXT[] DEFAULT '{}', -- Store multiple image paths/URLs
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Keywords table (Expanded)
CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    primary_keywords TEXT[] DEFAULT '{}',
    secondary_keywords TEXT[] DEFAULT '{}',
    long_tail_keywords TEXT[] DEFAULT '{}',
    intent_keywords TEXT[] DEFAULT '{}',
    regional_keywords TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Scripts table (Expanded with versioning and structural details)
CREATE TABLE IF NOT EXISTS scripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    title VARCHAR(255),
    hook TEXT,
    script_text TEXT,
    scene_breakdown JSONB DEFAULT '[]'::jsonb,
    caption_timeline JSONB DEFAULT '[]'::jsonb,
    thumbnail_text TEXT,
    seo_description TEXT,
    hashtags TEXT[] DEFAULT '{}',
    version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'draft', -- draft, approved, rejected
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Thumbnails table (New)
CREATE TABLE IF NOT EXISTS thumbnails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    layout TEXT,
    text TEXT,
    prompt TEXT,
    image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Translations table
CREATE TABLE IF NOT EXISTS translations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    language VARCHAR(50) NOT NULL, -- Malayalam, Tamil, Hindi, Telugu
    youtube_script TEXT,
    reel_script TEXT,
    whatsapp_post TEXT,
    google_business_post TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_script_language UNIQUE(script_id, language)
);

-- Voiceovers table
CREATE TABLE IF NOT EXISTS voiceovers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    translation_id UUID NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
    audio_url TEXT NOT NULL,
    duration NUMERIC(6, 2), -- in seconds
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Videos table (Updated with versioning and publishing info)
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    voiceover_id UUID NOT NULL REFERENCES voiceovers(id) ON DELETE CASCADE,
    video_url TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'draft', -- processing, ready, failed
    approval_status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected, revision_requested
    youtube_id VARCHAR(100), -- YouTube Video ID
    youtube_url VARCHAR(255), -- YouTube Video Link
    version INTEGER DEFAULT 1,
    engagement_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Comments table
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    username VARCHAR(100) NOT NULL,
    comment_text TEXT NOT NULL,
    intent_class VARCHAR(50) DEFAULT 'SPAM', -- HIGH_INTENT, MEDIUM_INTENT, SPAM
    response_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Leads table
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE SET NULL,
    username VARCHAR(100) NOT NULL,
    language VARCHAR(50),
    intent VARCHAR(50) DEFAULT 'MEDIUM_INTENT',
    status VARCHAR(50) DEFAULT 'new', -- new, contacting, qualified, customer, lost
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    state VARCHAR(50) NOT NULL DEFAULT 'WELCOME',
    history JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    amount NUMERIC(12, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, paid, shipped, completed, cancelled
    address TEXT,
    payment_method VARCHAR(50),
    transaction_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Analytics table
CREATE TABLE IF NOT EXISTS analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_leads INTEGER DEFAULT 0,
    total_conversions INTEGER DEFAULT 0,
    videos_generated INTEGER DEFAULT 0,
    engagement_rate NUMERIC(5, 2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_business_date UNIQUE(business_id, date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_products_business ON products(business_id);
CREATE INDEX IF NOT EXISTS idx_keywords_product ON keywords(product_id);
CREATE INDEX IF NOT EXISTS idx_scripts_product ON scripts(product_id);
CREATE INDEX IF NOT EXISTS idx_thumbnails_script ON thumbnails(script_id);
CREATE INDEX IF NOT EXISTS idx_translations_script ON translations(script_id);
CREATE INDEX IF NOT EXISTS idx_voiceovers_translation ON voiceovers(translation_id);
CREATE INDEX IF NOT EXISTS idx_videos_voiceover ON videos(voiceover_id);
CREATE INDEX IF NOT EXISTS idx_comments_video ON comments(video_id);
CREATE INDEX IF NOT EXISTS idx_leads_business ON leads(business_id);
CREATE INDEX IF NOT EXISTS idx_conversations_lead ON conversations(lead_id);
CREATE INDEX IF NOT EXISTS idx_orders_lead ON orders(lead_id);
CREATE INDEX IF NOT EXISTS idx_analytics_business ON analytics(business_id);
