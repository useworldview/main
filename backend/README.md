# UseWorldview Backend

AI-powered synthetic user research platform — backend orchestration layer.

## What This Does

This backend is the **AI/orchestration engine** for UseWorldview. It turns a submitted URL + research goal into:
- **Audience segments** detected from the target site
- **AI personas** with full psychographic worldviews
- **Autonomous browser sessions** where personas explore the target site
- **Structured findings** (likes, dislikes, trust signals, feelings)
- **Decision explanations** (why they converted, abandoned, etc.)
- **Cross-persona insights** (pattern statements with counts)
- **Prioritized recommendations** (Problem → Evidence → Affected Users → Why It Matters → Fix)

All data is written to Supabase, where the Next.js frontend reads it directly via RLS.

## Architecture

```
FastAPI API (6 endpoints) → Postgres job queue → Worker process
                                                    ↓
                                    Playwright headless browser
                                    LLM calls (Groq/Gemini/OpenRouter/Claude)
                                                    ↓
                                    Supabase (Postgres + Storage)
```

## Quick Start

### 1. Prerequisites
- Python 3.11+
- A Supabase project with the schema applied

### 2. Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy and fill in your env vars
cp .env.example .env
```
*(Note: Playwright browser installation is handled automatically on startup in development).*

### 3. Database Setup
Run the SQL in `db/migrations/0001_init.sql` against your Supabase project's SQL editor.

*(Note: The public `screenshots` storage bucket will be created automatically on startup).*

### 4. Run

The backend runs in **unified mode** by default, meaning the API and the worker run in the same process for local development.

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Test
```bash
# Health check
curl http://localhost:8000/api/health

# Create a study (requires valid Supabase JWT)
curl -X POST http://localhost:8000/api/studies \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://qurovo.com",
    "research_goals": [{"type": "template", "value": "overall product experience"}],
    "confirmed_authorized": true
  }'
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | No | Health check |
| POST | `/api/studies` | Yes | Create study + start site analysis |
| POST | `/api/studies/{id}/personas/generate` | Yes | Generate AI personas |
| POST | `/api/personas/{id}/regenerate` | Yes | Regenerate a single persona |
| POST | `/api/studies/{id}/deploy` | Yes | Deploy personas into the target site |
| POST | `/api/studies/{id}/retry-failed-sessions` | Yes | Retry failed agent sessions |
| DELETE | `/api/studies/{id}/purge-storage` | Yes | Delete screenshots from Storage |

Everything else (reading studies, personas, sessions, findings, etc.) is done by the frontend directly via Supabase with RLS.

## Environment Variables

See `.env.example` for the full list. Key ones:
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
- `GROQ_API_KEY` and/or `OPENROUTER_API_KEY` (at least one LLM key required)
- `LLM_FALLBACK_ORDER` — comma-separated provider order (default: groq,gemini,openrouter,claude)

## LLM Fallback Chain

The system tries LLM providers in order: **Groq → Gemini → OpenRouter → Claude**. If one fails (rate limit, timeout, error), it automatically falls to the next. Every call is logged to `llm_usage_log` for cost tracking.
