# VyaparAI - Expanded Multi-Agent Marketing & Sales Platform

VyaparAI is a production-quality MVP designed to automate digital marketing, localization, and conversational sales for Indian micro-businesses. This expanded version integrates an 8-agent workflow with campaign quality scoring, automatic regeneration loops, version control, and YouTube publishing.

---

## 🚀 Key Agent Architecture

The sequential CrewAI pipeline coordinates these 8 specialized agents:

1. **`KeywordAgent`**: Classifies product catalogs into primary, secondary, long-tail, intent, and regional keywords.
2. **`TrendAgent`**: Reviews Google Trends and search volume statistics to output trending topics and SEO titles.
3. **`ScriptAgent`**: Drafts structured ad templates (Title, Hook, Problem, Solution, Benefits, CTA, Voiceover, Captions).
4. **`ThumbnailAgent`**: Outlines graphic layouts and generative prompts for click-worthy covers.
5. **`QualityAgent`**: Conducts automatic campaign audit checks, scoring scripts out of 100. If the score is `< 80`, it triggers the crew to regenerate a fresh script copy.
6. **`VideoAgent`**: Combines product visuals, synced regional voiceovers, and Pillow-drawn subtitles into MP4 vertical videos.
7. **`ApprovalAgent`**: Intermediates human validation (APPROVE / REGENERATE).
8. **`YouTubePublishingAgent`**: Uploads approved videos and custom thumbnails directly to YouTube, returning URL records.

---

## 🗂️ Version & Regeneration Logic

If the human owner clicks **Regenerate Version 2**:
* The system calls the backend `/regenerate` endpoint.
* It increments the database script version (V1 -> V2 -> V3...).
* It invokes the `ScriptAgent` and `ThumbnailAgent` with user audit feedback to construct a fresh marketing layout without repeating previous styles.

---

## 📁 Project Structure

```text
VyaparAI/
├── backend/
│   ├── agents/          # Agent structures (Keyword, Trend, Script, Thumbnail, Quality, Publishing)
│   ├── crews/           # CrewAI sequence pipeline (marketing_crew.py)
│   ├── database/        # DB migration initial SQL schemas
│   ├── langgraph/       # LangGraph conversational state machine
│   ├── models/          # Input/output schemas
│   ├── routers/         # API routers (business, marketing, lead, sales, analytics)
│   ├── services/        # Audio, video compilers, Supabase, and YouTube API modules
│   ├── tests/           # Pytest unit tests suite
│   ├── Dockerfile
│   └── main.py          # Server main
├── frontend/
│   ├── app/             # App Router pages (upload, crm, chat, analytics)
│   ├── components/      # Navigation layouts
│   ├── Dockerfile
│   └── package.json
├── docker/
│   └── docker-compose.yml
├── n8n/
│   └── workflows/       # Webhook trigger automations
├── demo_data.json
└── installation_guide.md
```

---

## 🚥 Quick Start

Please check the detailed [installation_guide.md](file:///c:/Users/nidhi/OneDrive/Desktop/VyaparAI/installation_guide.md) to start the system.
Run backend tests with `pytest -v` inside the activated virtual environment.

---

## 📺 YouTube Comment Monitoring & Intelligent Reply System

VyaparAI includes a production-ready YouTube Comment Monitoring system that connects a channel once, monitors comments, qualifies sales leads, and automates reply workflows.

### 🤖 CrewAI Monitoring Workflow
The workflow runs every 5 minutes in a background task thread, coordinating 8 agents in sequence:
1. **`ChannelAgent`**: Verifies OAuth permissions, credentials, and channel details.
2. **`VideoMonitoringAgent`**: Identifies uploaded marketing videos from the channel feed.
3. **`CommentCollectorAgent`**: Reads incoming comments, filters duplicates/deleted messages, and logs unique items.
4. **`IntentAgent`**: Uses Llama 3.1 LLM (or regex heuristics) to classify comments:
   * **`HIGH_INTENT`**: Pricing queries, order placement, delivery availability, or contacts.
   * **`MEDIUM_INTENT`**: Generic Q&A or comparisons.
   * **`LOW_INTENT`**: Praise, greetings, and emoji reactions.
   * **`SPAM`**: Promotional links or unrelated messages.
5. **`ReplyAgent`**: Generates context-appropriate, human-like responses (provides direct WhatsApp ordering links for High Intent, Q&A support for Medium Intent, and emoji hearts/gratitude for Low Intent).
6. **`ApprovalAgent`**: Halts suggested replies in draft mode when `AUTO_REPLY` is disabled, enabling manual admin approval/edits.
7. **`LeadAgent`**: Promotes authors of `HIGH_INTENT` messages automatically into the CRM Leads panel with action CTAs.
8. **`PublisherAgent`**: Publishes approved replies onto YouTube comments, ensuring zero duplicate posts.

### 🛡️ Authentication & Sandbox Mode
- **Google OAuth Integration**: Connect your real channel by clicking "Connect YouTube Channel" to trigger Google login, storing secure access/refresh tokens in Supabase.
- **Sandbox Simulation Mode**: If Google credentials are not set up locally, click "Simulate Connection (Sandbox)" to link a mock channel. You can then use the built-in comment simulator to inject custom queries (e.g. "Do you ship to Mumbai? Price?") and watch the 8-agent pipeline classify comments, generate replies, register CRM leads, and track analytics in real-time.

### 📊 Dashboard Interfaces
We have created 6 new sections in the Sidebar:
- **YouTube Connect**: Connect/disconnect channels, display statistics, and view permissions.
- **Video Monitoring**: View all indexed marketing videos and their comments counts.
- **Comment Inbox**: Browse, search, and filter comments by intent or video ID, and inject simulated queries.
- **Reply Approval**: Approve, edit, reject, or request regeneration of reply drafts.
- **Lead Dashboard**: View qualified buyer leads, track intent categorization, and initiate direct outreach via WhatsApp.
- **YouTube Analytics**: Monitor total processed comments, Auto-Reply rates, conversion rates, and top performing video campaigns.
