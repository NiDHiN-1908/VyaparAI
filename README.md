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
