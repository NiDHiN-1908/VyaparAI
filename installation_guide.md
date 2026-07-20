# 🌿 VyaparAI Platform - Complete Installation & Deployment Guide

This guide details step-by-step instructions to set up, configure, build, run, and verify the expanded VyaparAI platform (11-Agent Architecture).

---

## 📋 System Prerequisites

1. **Python 3.10+** (Recommended: Python 3.10 or 3.11)
2. **Node.js 18+** (Recommended: Node.js 18.x or 20.x)
3. **FFmpeg** (Required for background video rendering, audio compilation, and ASS subtitle burning)
4. **Ollama** (Local LLM runner running `llama3.1`)
5. **Supabase Account / Instance** (PostgreSQL schema & realtime database)
6. **Google Cloud Account** (Optional: YouTube Data API v3 OAuth secrets for live publishing)

---

## ⚡ 1. Set Up Local LLM (Ollama)

1. Download and install [Ollama](https://ollama.com).
2. Pull the required `llama3.1` model in your terminal:
   ```bash
   ollama pull llama3.1
   ```
3. Start the Ollama server service:
   ```bash
   ollama serve
   ```

---

## 💾 2. Database Setup (Supabase & Postgres Migrations)

1. Open the **SQL Editor** in your Supabase Console.
2. Execute the migration SQL scripts in order from the repository:
   - [001_initial_schema.sql](file:///c:/Users/nidhi/Desktop/VyaparAI/backend/database/migrations/001_initial_schema.sql) — Initial product, lead, conversation, and order tables.
   - [002_youtube_schema.sql](file:///c:/Users/nidhi/Desktop/VyaparAI/backend/database/migrations/002_youtube_schema.sql) — YouTube channels, comments, replies, and intent analytics tables.
   - [003_whatsapp_module.sql](file:///c:/Users/nidhi/Desktop/VyaparAI/backend/database/migrations/003_whatsapp_module.sql) — WhatsApp instance & message payload tables.
   - [004_video_jobs.sql](file:///c:/Users/nidhi/Desktop/VyaparAI/backend/database/migrations/004_video_jobs.sql) — Asynchronous background video rendering job queue.

3. Obtain your Supabase **Project URL** and **Service/Anon API Key**.

---

## 🐍 3. Configure & Run Backend Services (FastAPI)

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   
   # On Windows:
   .\venv\Scripts\activate
   
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Create your `.env` configuration file in `backend/.env`:
   ```env
   PORT=8000
   SUPABASE_URL=https://your-supabase-project.supabase.co
   SUPABASE_KEY=your-supabase-service-key
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.1
   OPENAI_API_KEY=your-openai-api-key-optional
   EVOLUTION_API_ENDPOINT=http://localhost:8080
   EVOLUTION_API_KEY=your-evolution-key
   ```
5. Start the FastAPI backend server:
   ```bash
   python main.py
   ```
   *The API will be available at [http://localhost:8000](http://localhost:8000) (Interactive Swagger Docs at [http://localhost:8000/docs](http://localhost:8000/docs)).*

---

## ⚛️ 4. Configure & Run Frontend Application (Next.js 14)

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your web browser.

---

## 🚀 5. Quick Launch via Windows Batch Script

To start Ollama, FastAPI Backend, and Next.js Frontend simultaneously in parallel terminal windows, run:

```cmd
start_all.bat
```

---

## 🧪 6. Verification & Running Test Suites

Run backend test suites using `pytest`:

```bash
cd backend
pytest -v
```

Specifically test Nursery Delivery & Discount Rules Engine:
```bash
pytest backend/tests/test_delivery_discounts.py -v
```

Specifically test Module Specifications & Infrastructure:
```bash
pytest backend/tests/test_modules_review.py -v
```
