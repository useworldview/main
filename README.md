# UseWorldview

> **AI-Powered Synthetic User Research Platform**
> Simulate realistic, diverse human personas interacting with your web product autonomously via browser agents, delivering rich behavioral analytics, journey replays, and prioritized UX recommendations.

---

## 🏗 Repository Structure

```
.
├── backend/                  # FastAPI + Playwright backend service
│   ├── app/
│   │   ├── api/              # REST endpoints (studies, personas, jobs)
│   │   ├── core/             # Config, security (JWT), Supabase, LLM client
│   │   ├── db/migrations/    # Complete 0001_init.sql schema & RLS policies
│   │   ├── jobs/             # Postgres-backed job queue & worker
│   │   ├── models/           # Pydantic schemas
│   │   └── services/         # Agent loop, perception, persona engine, LLM
│   ├── Dockerfile            # API container definition
│   ├── Dockerfile.worker     # Background worker container definition
│   ├── requirements.txt      # Python dependencies
│   └── worker_entrypoint.py  # Worker daemon process
│
├── frontend/                 # Next.js 15 (App Router) frontend
│   ├── app/                  # Pages: Dashboard, Study creation, Replays, Recs
│   ├── lib/                  # Supabase clients, API client, TypeScript types
│   └── package.json          # Node dependencies
│
├── UseWorldview_PRD_v1.md    # Product Requirements Document
├── backend.md                # Backend Architecture Specification
└── frontend.md               # Frontend Design Specification
```

---

## 🚀 Quick Start

### 1. Database Setup (Supabase)
1. In your Supabase Project dashboard, open the **SQL Editor**.
2. Run the SQL migration script: [`backend/db/migrations/0001_init.sql`](backend/db/migrations/0001_init.sql).
*(Note: The `screenshots` storage bucket is created automatically on first backend startup).*

### 2. Backend Setup (FastAPI)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase URL, Service Role Key, and LLM API Keys (Groq, Gemini, OpenRouter, Claude)

# Start API and Worker (unified mode)
uvicorn app.main:app --reload --port 8000
```
*(Note: Playwright browser binaries are installed automatically on first startup).*

### 3. Frontend Setup (Next.js)
```bash
cd frontend
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your Supabase Anon Key and URL

# Start Dev Server
npm run dev
```

Visit `http://localhost:3000` to start using UseWorldview!
