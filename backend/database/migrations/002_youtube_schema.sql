-- 002_youtube_schema.sql
-- Database schema for YouTube Comment Monitoring & Intelligent Reply System

-- 1. YouTube Channels Table
CREATE TABLE IF NOT EXISTS youtube_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id VARCHAR(255) UNIQUE NOT NULL,
    channel_name VARCHAR(255) NOT NULL,
    thumbnail TEXT,
    subscriber_count INTEGER DEFAULT 0,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_uri VARCHAR(255),
    client_id VARCHAR(255),
    client_secret VARCHAR(255),
    scopes TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. YouTube Videos Table
CREATE TABLE IF NOT EXISTS youtube_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id VARCHAR(255) REFERENCES youtube_channels(channel_id) ON DELETE CASCADE,
    video_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    publish_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'monitored', -- monitored, ignored
    auto_reply BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. YouTube Comments Table
CREATE TABLE IF NOT EXISTS youtube_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id VARCHAR(100) REFERENCES youtube_videos(video_id) ON DELETE CASCADE,
    comment_id VARCHAR(100) UNIQUE NOT NULL,
    username VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE,
    intent VARCHAR(50) DEFAULT 'SPAM', -- HIGH_INTENT, MEDIUM_INTENT, LOW_INTENT, SPAM
    confidence NUMERIC(4, 3) DEFAULT 1.000,
    status VARCHAR(50) DEFAULT 'pending_approval', -- pending_approval, approved, rejected, replied
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. YouTube Replies Table
CREATE TABLE IF NOT EXISTS youtube_replies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    comment_id VARCHAR(100) REFERENCES youtube_comments(comment_id) ON DELETE CASCADE,
    reply_id VARCHAR(100) UNIQUE, -- populated once published
    suggested_reply TEXT NOT NULL,
    actual_reply TEXT,
    status VARCHAR(50) DEFAULT 'draft', -- draft, pending_approval, pending_publish, published, failed
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. YouTube Leads Table
CREATE TABLE IF NOT EXISTS youtube_leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    comment_id VARCHAR(100) REFERENCES youtube_comments(comment_id) ON DELETE CASCADE,
    video_id VARCHAR(100) REFERENCES youtube_videos(video_id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL,
    intent VARCHAR(50) DEFAULT 'HIGH_INTENT',
    reply TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. YouTube Analytics Table
CREATE TABLE IF NOT EXISTS youtube_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id VARCHAR(255) REFERENCES youtube_channels(channel_id) ON DELETE CASCADE,
    comments_processed INTEGER DEFAULT 0,
    reply_rate NUMERIC(5, 2) DEFAULT 0.00,
    lead_count INTEGER DEFAULT 0,
    conversion_rate NUMERIC(5, 2) DEFAULT 0.00,
    top_videos JSONB DEFAULT '[]'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for YouTube Monitoring performance
CREATE INDEX IF NOT EXISTS idx_yt_videos_channel ON youtube_videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_yt_comments_video ON youtube_comments(video_id);
CREATE INDEX IF NOT EXISTS idx_yt_comments_intent ON youtube_comments(intent);
CREATE INDEX IF NOT EXISTS idx_yt_replies_comment ON youtube_replies(comment_id);
CREATE INDEX IF NOT EXISTS idx_yt_leads_comment ON youtube_leads(comment_id);
CREATE INDEX IF NOT EXISTS idx_yt_analytics_channel ON youtube_analytics(channel_id);
