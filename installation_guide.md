# VyaparAI Platform (8-Agent Version) - Installation Guide

This guide details instructions to set up, build, and run the expanded VyaparAI platform.

## Prerequisites

1. **Python 3.10+**
2. **Node.js 18+**
3. **Ollama** (Local LLM runner running `llama3.1`)
4. **Docker Desktop** (optional, for Compose deployments)
5. **Supabase** (PostgreSQL schema setups)
6. **YouTube Data API v3** secrets file (optional, for real uploads)

---

## 1. Setup Local LLM (Ollama)
1. Download and start [Ollama](https://ollama.com).
2. Pull the required model:
   ```bash
   ollama pull llama3.1
   ```

---

## 2. Set Up Database (Supabase)
1. Open the SQL Editor in your Supabase Console.
2. Copy and execute the contents of the updated schema file [001_initial_schema.sql](file:///c:/Users/nidhi/OneDrive/Desktop/VyaparAI/backend/database/migrations/001_initial_schema.sql) to initialize tables (`products`, `keywords`, `scripts`, `thumbnails`, `videos`, `leads`, `conversations`).
3. Obtain your Supabase API credentials.

---

## 3. Configure YouTube API (Optional)
To enable real uploads instead of sandbox simulation:
1. Go to the [Google Cloud Console](https://console.cloud.google.com).
2. Enable the **YouTube Data API v3** for a project.
3. Configure your OAuth Consent Screen and create **OAuth 2.0 Client IDs** credentials.
4. Download the JSON file, rename it to `client_secrets.json`, and place it in the `backend/` root directory.
*Note: If `client_secrets.json` is missing, the platform automatically runs in a secure Sandbox Simulation Mode, creating mock YouTube links.*

---

## 4. Run Backend Services (FastAPI)
1. Open your terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Setup virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Unix:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure `.env`:
   ```env
   SUPABASE_URL=https://your-supabase-project.supabase.co
   SUPABASE_KEY=your-supabase-service-key
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.1
   ```
5. Run dev server:
   ```bash
   python main.py
   ```
   *API documentation will run at [http://localhost:8000/docs](http://localhost:8000/docs).*

---

## 5. Run Frontend App (Next.js)
1. Navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install dependencies and start the dev server:
   ```bash
   npm install
   npm run dev
   ```
3. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 6. Running Unit Tests
Verify all QA criteria, model scoring rules, and database version counters:
```bash
cd backend
pytest -v
```
