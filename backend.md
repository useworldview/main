# UseWorldview — Backend Build Specification (v1 / MVP)

Companion document: `UseWorldview_Frontend_Build_Spec.md` — they share ONE API contract (Section 6). If you change an endpoint here, change it there too.

---

## 0. How To Use This Doc With Claude Code

- Run this in its **own repo / own Claude Code session**, separate from the frontend.
- Build in the milestone order in **Section 9**, one milestone at a time. After each milestone, run it and confirm it actually works (curl the endpoint, check the DB row, watch the worker log) before starting the next. Do not ask Claude Code to build all of Section 9 in a single pass — that's what caused the earlier collapse.
- Section 6 is a **complete list of the API surface**. There is nothing else to build beyond it — resist the temptation to add "nice to have" endpoints; the frontend gets everything else straight from Supabase.

---

## 1. What This Service Does

UseWorldview deploys AI personas into a customer's live website and reports back what they experienced. This backend is the AI/orchestration layer: it turns a submitted URL + research goal into audience segments, personas, autonomous browser-agent sessions, and finally structured findings and recommendations — all written to Supabase, where the frontend reads them.

---

## 2. Architecture Decision: Thin API, Fat Supabase

This is the single biggest scope-reduction lever, so it's worth stating explicitly.

- **Frontend reads everything directly from Supabase**, protected by Row-Level Security. Studies, personas, sessions, events, findings, insights, recommendations — no backend endpoint needed for any of it.
- **Frontend writes directly to Supabase** for anything that doesn't require AI/browser work: editing a persona's fields, adding a manual audience segment, marking a recommendation "useful," toggling theme preference.
- **This backend only owns actions that require the AI/orchestration layer**: analyzing a site, generating personas, running an agent session, deploying a study. That's 4 real actions — Section 6 has 6 endpoints total including retry and health.
- The **worker** (the async job processor) writes all AI-generated output (events, findings, insights, recommendations) straight into Supabase using the service-role key. It never talks to the frontend directly — the frontend sees new rows via Supabase Realtime or its next query.

Net effect: this backend is small on purpose. If you find yourself adding a 7th REST endpoint, stop and check whether it actually needs the AI layer, or whether it's just a Supabase read/write the frontend should do itself.

---

## 3. Tech Stack (decided, don't relitigate)

| Concern | Choice | Why |
|---|---|---|
| API framework | FastAPI (Python 3.11+), Pydantic v2 | async-native, pairs cleanly with a polling worker |
| DB / Auth / Storage | Supabase (Postgres + Auth + Storage) | per PRD; also gives RLS + Realtime for free |
| Browser automation | Playwright (Python, headless Chromium) | industry standard, screenshot + DOM access |
| LLM | Groq, Gemini, OpenRouter, Claude API (with fallback) | needed for persona generation, agent reasoning over screenshots, and post-session analysis. Implement a resilient fallback mechanism: attempt generation using Groq first, then Gemini, then OpenRouter, and finally Claude based on API availability. Model names should be configurable. |
| Job queue | **Postgres table** (`agent_jobs`) claimed with `FOR UPDATE SKIP LOCKED`, polled by a worker process | zero extra infra for V1 scale; no Redis to run/pay for/monitor. Upgrade path: swap to Redis + ARQ/Celery later if concurrency needs outgrow a few polling workers. |
| Site fetch / robots.txt | httpx | lightweight for the initial site-analysis pass |
| Deployment | Any container host running 2 processes: `api` (uvicorn) and `worker` (poll loop) | keep them separately scalable |

---

## 4. Repo Structure

```
useworldview-backend/
  app/
    main.py                        # FastAPI app + route registration
    api/
      deps.py                      # verify Supabase JWT -> current_user_id
      routes/
        studies.py                 # the 6 endpoints live here (+ health)
    core/
      config.py                    # env settings (pydantic-settings)
      supabase_client.py           # service-role client factory
      security.py                  # JWT verification against SUPABASE_JWT_SECRET
      llm_client.py                # unified LLM router with fallback (Groq->Gemini->OpenRouter->Claude)
    services/
      site_analysis.py
      audience_detection.py
      persona_generation.py
      agent_session/
        browser_driver.py          # Playwright wrapper: launch, screenshot, DOM snapshot
        perceive.py
        decide.py                  # LLM call (using fallback router): persona + goal + memory + perception -> next action
        act.py                     # executes the decided action via Playwright
        guardrails.py              # robots.txt, blocklist, budgets (Section 8)
        runner.py                  # the perceive->decide->act->observe loop
      post_session_analysis.py
      cross_persona_analysis.py
      recommendations_engine.py
    jobs/
      queue.py                     # claim_job(), complete_job(), fail_job()
      worker.py                    # poll loop entrypoint
      job_types.py
    models/
      schemas.py                   # Pydantic request/response models
    db/
      migrations/
        0001_init.sql              # Section 6 SQL, run this first, verbatim
  tests/
  worker_entrypoint.py
  requirements.txt
  .env.example
  Dockerfile
  Dockerfile.worker
  README.md
```

---

## 5. Environment Variables

```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=        # backend/worker only — never sent to frontend
SUPABASE_JWT_SECRET=              # to verify incoming user JWTs
GROQ_API_KEY=
GEMINI_API_KEY=
OPENROUTER_API_KEY=
ANTHROPIC_API_KEY=
LLM_FALLBACK_ORDER=groq,gemini,openrouter,claude # Comma-separated list indicating preferred API usage order
PLAYWRIGHT_HEADLESS=true
MAX_STEP_BUDGET_DEFAULT=40
MAX_PAGES_DEFAULT=5
SESSION_WALL_CLOCK_TIMEOUT_SECONDS=600
WORKER_POLL_INTERVAL_SECONDS=2
WORKER_CONCURRENCY=4
ENV=development
```

---

## 6. API Contract — this is the ENTIRE backend surface

All endpoints require `Authorization: Bearer <supabase_access_token>`, verified via `SUPABASE_JWT_SECRET`. All other reads/writes happen frontend → Supabase directly (see Section 2).

| Method | Path | Body | Effect |
|---|---|---|---|
| `POST` | `/api/studies` | `{target_url, research_goals: [{type:"template"\|"custom", value:string}]}` | Creates `studies` row (status `draft`), enqueues `analyze_site` job, returns the row |
| `POST` | `/api/studies/{id}/personas/generate` | `{segment_ids: string[], personas_per_segment?: int}` | Enqueues `generate_personas` job |
| `POST` | `/api/personas/{id}/regenerate` | `{}` | Enqueues a single-persona regeneration |
| `POST` | `/api/studies/{id}/deploy` | `{}` | Validates study has ≥1 active persona, creates `agent_sessions` rows, enqueues one `run_agent_session` job per persona, sets `studies.status = 'running'` |
| `POST` | `/api/studies/{id}/retry-failed-sessions` | `{}` | Re-enqueues only sessions with `status = 'failed'` |
| `GET` | `/api/health` | — | `{status: "ok"}`, no auth |

Every endpoint checks `studies.user_id = current_user_id` (via a Supabase query using the caller's own JWT, not the service key) before doing anything — don't trust RLS alone here since the backend uses the service-role key internally for the actual writes.

Response shape for the study-mutating endpoints: return the current `studies` row as JSON so the frontend can immediately reflect the new status without a refetch.

---

## 7. Worker: Job Pipeline

The worker polls `agent_jobs` (`status='pending'`, oldest first, `FOR UPDATE SKIP LOCKED`, up to `WORKER_CONCURRENCY` at a time), marks it `claimed` → `running`, executes, then `done` or `failed` (retry up to `max_attempts`, then leave `failed` and surface `error_message` on the parent `studies` row).

**`analyze_site`**
1. Check `robots.txt` for `target_url`. If disallowed → set `studies.status='failed'`, `error_message='Target site disallows automated access'`, stop.
2. Fetch the page(s) (httpx first; fall back to a quick Playwright render if content looks JS-rendered/empty), extract text content, nav structure, meta tags.
3. LLM call (using fallback router): infer product category + candidate audience segments from the extracted content + `research_goals`.
4. Insert `audience_segments` rows (`source='detected'`), store extracted context in `studies.site_context`, set `studies.status='audience_ready'`.

**`generate_personas`**
1. For each requested `segment_id`, LLM call (using fallback router): synthesize N personas (default 1 per segment, respecting FR-5.6's 3–5 total default) with full `worldview` + `situational_context` per Section 13's schema.
2. Self-consistency pass: ask the model to flag any internally contradictory attribute combination (e.g. "high digital literacy" + "struggles to use a mouse" with no narrative reason) and regenerate just that persona if flagged.
3. Insert `personas` rows (`status='draft'`), set `studies.status='personas_ready'`.

**`run_agent_session`** (one job per persona, can run concurrently across personas in a study)
1. Launch a Playwright browser context, navigate to `target_url`.
2. Loop, bounded by `step_budget` **and** a wall-clock timeout:
   - **Perceive**: screenshot + simplified DOM/accessibility snapshot.
   - **Decide**: LLM call (using fallback router) with persona worldview + research goal + running session memory + current perception → next action (click/type/scroll/navigate/search/back/forward) or a decision to complete/abandon, with reasoning text.
   - **Guardrail check** (Section 8) on the proposed action before executing it.
   - **Act**: execute via Playwright.
   - **Observe**: insert `interaction_events` row (upload screenshot to Supabase Storage, store the path), update in-memory session state.
3. On loop end, write `agent_sessions.status/outcome/outcome_reason/step_count/pages_visited`, enqueue `analyze_session`.

**`analyze_session`**
1. LLM call (using fallback router) over the full `interaction_events` log + persona worldview → structured `findings` (like/dislike/feeling/trust/distrust, each with `linked_event_ids`) and `decision_explanations`.
2. If this was the last session in the study to reach a terminal state, enqueue `synthesize_study`.

**`synthesize_study`**
1. LLM call (using fallback router) over all `findings`/`decision_explanations` across the study → `cross_persona_insights` (pattern statements with supporting/total counts) and `recommendations` (Problem/Evidence/Affected Users/Why It Matters/Suggested Improvement — see PRD Section 23 for the exact format, copy it verbatim).
2. **Aggregate scores** (trust score, value-prop clarity, usability score, conversion intent — required by frontend FR-12.1): the PRD doesn't specify a scoring methodology (its own Open Question #6). Don't invent an opaque 0–100 score. Compute these as **plain ratios grounded in the data you already have** — e.g. trust score = (# trust findings) / (# trust + distrust findings) across all sessions, task completion rate = (# completed sessions) / (# total sessions). Store them in a `studies.summary_metrics jsonb` column (add this to the schema) so the frontend just displays what you computed, with the underlying counts available for drill-down. This keeps every number traceable to source events, per the PRD's own auditability requirement (Section 11).
3. Set `studies.status='completed'`, `completed_at=now()`. If zero sessions reached `completed`/`abandoned` (all errored), set `studies.status='failed'` instead.

Log every LLM call's token usage to `llm_usage_log` (purpose, tokens, estimated cost) — cheap to add now, and it's the only way to actually monitor the cost-control NFR later.

---

## 8. Guardrails (non-negotiable — build these before `run_agent_session` touches any real site)

- **robots.txt compliance**, checked before first navigation and re-checked if the agent navigates to a new path.
- **Never submit real payment info.** Any form with card-number/CVV/payment-looking fields gets filled with obviously synthetic data (e.g. `Jane Testerson`, `test+useworldview@example.com`) and the agent must never click a final "Pay / Place Order / Complete Purchase" button — reaching that screen counts as goal completion for a purchase-intent study, full stop.
- **No destructive actions** (delete, cancel account, unsubscribe others, etc.) — enforce this two ways: in the `decide()` prompt AND as a hard keyword/element-role blocklist in `act()` as defense in depth. Prompt-only guardrails are not sufficient here.
- **Step budget + wall-clock timeout**, both enforced independently — a slow page shouldn't let a session run forever even under budget.
- **Honest User-Agent string** identifying the agent.
- **Rate limiting** — stagger session starts hitting the same target domain; cap concurrent Playwright contexts per domain (e.g. 2) so a study with 5 personas doesn't hammer the target site simultaneously.

---

## 9. Build Milestones — build in this order, verify each before moving on

| # | Milestone | Definition of done |
|---|---|---|
| M0 | Scaffold + DB | Repo structure exists, `0001_init.sql` (Section 10) applied to a Supabase project, RLS enabled, `/api/health` returns 200 |
| M1 | Auth + read-only study endpoints removed from scope (frontend does this via Supabase) — confirm JWT verification works | A hand-crafted request with a valid Supabase user JWT resolves to the right `user_id` in `deps.py`; an invalid/missing token gets 401 |
| M2 | `POST /api/studies` + `analyze_site` job | Submitting a real URL produces `audience_segments` rows and flips study status to `audience_ready` end-to-end |
| M3 | `generate_personas` job + regenerate endpoint | Personas with full worldview JSON appear in the DB, readable via the Supabase dashboard |
| M4 | `run_agent_session` — single persona, no concurrency yet | One persona session against a real test page produces a sensible `interaction_events` sequence and a terminal outcome |
| M5 | Guardrails hardened (Section 8) + `deploy` endpoint running multiple sessions concurrently | 3-persona study deploys, all sessions run without violating any guardrail |
| M6 | `analyze_session` + `synthesize_study` | Findings, decision explanations, cross-persona insights, and recommendations all populate for a completed study, each traceable to source events |
| M7 | Job retry/failure handling, cost logging, wall-clock timeouts | Killing a worker mid-job doesn't corrupt state; a failed session doesn't fail the whole study |
| M8 | Gap-closing additions (Section 12) — consent capture, page-error/dead-end handling, segment-level insights, recommendation scoring, retention/deletion, analytics events | Each item in Section 12 verified individually against a real study |

---

## 10. Database Schema (Supabase Postgres) — `db/migrations/0001_init.sql`

Give Claude Code this SQL verbatim as the first migration. Don't let it improvise the schema.

```sql
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  theme_preference text not null default 'light' check (theme_preference in ('light','dark')),
  created_at timestamptz not null default now()
);

-- auto-create a profile row on signup
create function public.handle_new_user() returns trigger as $$
begin
  insert into public.profiles (id, email) values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

create table public.studies (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text,
  research_goals jsonb not null default '[]',
  target_url text not null,
  status text not null default 'draft' check (status in (
    'draft','analyzing_site','audience_ready','personas_ready',
    'deploying','running','analyzing_results','completed','failed'
  )),
  step_budget_per_session int not null default 40,
  max_pages int not null default 5,
  site_context jsonb,
  summary_metrics jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);

create table public.audience_segments (
  id uuid primary key default gen_random_uuid(),
  study_id uuid not null references public.studies(id) on delete cascade,
  name text not null,
  description text,
  source text not null check (source in ('detected','edited','manual')),
  created_at timestamptz not null default now()
);

create table public.personas (
  id uuid primary key default gen_random_uuid(),
  study_id uuid not null references public.studies(id) on delete cascade,
  audience_segment_id uuid references public.audience_segments(id) on delete set null,
  name text not null,
  age int,
  location text,
  profession text,
  education text,
  income_level text,
  worldview jsonb not null default '{}',
  situational_context jsonb not null default '{}',
  status text not null default 'draft' check (status in ('draft','active','archived')),
  created_at timestamptz not null default now()
);

create table public.agent_sessions (
  id uuid primary key default gen_random_uuid(),
  study_id uuid not null references public.studies(id) on delete cascade,
  persona_id uuid not null references public.personas(id) on delete cascade,
  status text not null default 'queued' check (status in ('queued','running','completed','failed','aborted')),
  start_time timestamptz,
  end_time timestamptz,
  step_count int not null default 0,
  step_budget int not null default 40,
  outcome text check (outcome in ('completed','abandoned','error')),
  outcome_reason text,
  pages_visited int not null default 0,
  created_at timestamptz not null default now()
);

create table public.interaction_events (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.agent_sessions(id) on delete cascade,
  sequence_no int not null,
  event_type text not null check (event_type in
    ('click','scroll','type','navigate','search','back','forward','wait','screenshot','form_submit')),
  target_element text,
  page_url text,
  details jsonb not null default '{}',
  screenshot_ref text,
  occurred_at timestamptz not null default now()
);

create table public.findings (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.agent_sessions(id) on delete cascade,
  type text not null check (type in ('like','dislike','feeling','trust','distrust')),
  feeling_label text check (feeling_label in
    ('confused','interested','excited','frustrated','suspicious','confident',
     'overwhelmed','curious','uncertain','satisfied')),
  description text not null,
  linked_event_ids uuid[] not null default '{}',
  created_at timestamptz not null default now()
);

create table public.decision_explanations (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.agent_sessions(id) on delete cascade,
  decision_type text not null check (decision_type in ('signup','purchase','feature_use','abandon','other')),
  rationale_text text not null,
  linked_event_ids uuid[] not null default '{}',
  created_at timestamptz not null default now()
);

create table public.cross_persona_insights (
  id uuid primary key default gen_random_uuid(),
  study_id uuid not null references public.studies(id) on delete cascade,
  statement text not null,
  supporting_persona_count int not null,
  total_persona_count int not null,
  segment_filter text,
  created_at timestamptz not null default now()
);

create table public.recommendations (
  id uuid primary key default gen_random_uuid(),
  study_id uuid not null references public.studies(id) on delete cascade,
  problem text not null,
  evidence text not null,
  affected_users text not null,
  why_it_matters text not null,
  suggested_improvement text not null,
  priority_score numeric not null default 0,
  status text not null default 'new' check (status in ('new','useful','not_relevant','already_fixed')),
  created_at timestamptz not null default now()
);

-- internal job queue — never exposed to the frontend
create table public.agent_jobs (
  id uuid primary key default gen_random_uuid(),
  job_type text not null check (job_type in
    ('analyze_site','generate_personas','run_agent_session','analyze_session','synthesize_study')),
  payload jsonb not null,
  status text not null default 'pending' check (status in ('pending','claimed','running','done','failed')),
  attempts int not null default 0,
  max_attempts int not null default 3,
  error_message text,
  claimed_at timestamptz,
  claimed_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.llm_usage_log (
  id uuid primary key default gen_random_uuid(),
  study_id uuid references public.studies(id) on delete set null,
  session_id uuid references public.agent_sessions(id) on delete set null,
  purpose text not null,
  input_tokens int,
  output_tokens int,
  estimated_cost_usd numeric,
  created_at timestamptz not null default now()
);

-- Row Level Security: users only ever see their own studies and everything under them.
alter table public.studies enable row level security;
create policy "own studies" on public.studies for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

alter table public.audience_segments enable row level security;
create policy "own segments" on public.audience_segments for all
  using (exists (select 1 from public.studies s where s.id = study_id and s.user_id = auth.uid()))
  with check (exists (select 1 from public.studies s where s.id = study_id and s.user_id = auth.uid()));

alter table public.personas enable row level security;
create policy "own personas" on public.personas for all
  using (exists (select 1 from public.studies s where s.id = study_id and s.user_id = auth.uid()))
  with check (exists (select 1 from public.studies s where s.id = study_id and s.user_id = auth.uid()));

alter table public.agent_sessions enable row level security;
create policy "own sessions" on public.agent_sessions for all
  using (exists (select 1 from public.studies s where s.id = study_id and s.user_id = auth.uid()))
  with check (exists (select 1 from public.studies s where s.id = study_id and s.user_id = auth.uid()));

alter table public.interaction_events enable row level security;
create policy "own events" on public.interaction_events for select
  using (exists (
    select 1 from public.agent_sessions ags join public.studies s on s.id = ags.study_id
    where ags.id = session_id and s.user_id = auth.uid()
  ));

alter table public.findings enable row level security;
create policy "own findings" on public.findings for select
  using (exists (
    select 1 from public.agent_sessions ags join public.studies s on s.id = ags.study_id
    where ags.id = session_id and s.user_id = auth.uid()
  ));

alter table public.decision_explanations enable row level security;
create policy "own decisions" on public.decision_explanations for select
  using (exists (
    select 1 from public.agent_sessions ags join public.studies s on s.id = ags.study_id
    where ags.id = session_id and s.user_id = auth.uid()
  ));

alter table public.cross_persona_insights enable row level security;
create policy "own insights" on public.cross_persona_insights for select
  using (exists (select 1 from public.studies s where s.id = study_id and s.user_id = auth.uid()));

alter table public.recommendations enable row level security;
create policy "own recommendations" on public.recommendations for all
  using (exists (select 1 from public.studies s where s.id = study_id and s.user_id = auth.uid()))
  with check (exists (select 1 from public.studies s where s.id = study_id and s.user_id = auth.uid()));

alter table public.profiles enable row level security;
create policy "own profile" on public.profiles for all
  using (auth.uid() = id) with check (auth.uid() = id);

-- agent_jobs and llm_usage_log: RLS enabled, NO policies -> deny-all to authenticated users.
-- Only the service-role key (used exclusively by this backend/worker) can touch them.
alter table public.agent_jobs enable row level security;
alter table public.llm_usage_log enable row level security;
```

---

## 11. Non-Functional Recap

- A single persona/agent failure must never fail the whole study (Section 7's `analyze_session`/`synthesize_study` handle partial results).
- Every insight and recommendation must trace back to specific `interaction_events` via `linked_event_ids` — no unsourced claims.
- Bound and log LLM cost per study (`llm_usage_log`) so unit economics are visible from day one, not retrofitted later.
- English-only for V1; don't hardcode strings in a way that blocks future i18n, but don't build i18n infrastructure now either.

---

## 12. Gap-Closing Additions (build these as M8, after the M0–M7 core loop works)

These close out PRD requirements that the core loop above doesn't touch. Don't fold them into M0–M7 — they're real scope, do them once the happy path is proven.

### 12.1 Consent capture (resolves PRD Open Question #7)

`POST /api/studies` must require `confirmed_authorized: true` in the body and reject the request (422) if it's missing or false. This is the actual mechanism satisfying Section 16's "submitter must have the right to test this URL" requirement — the frontend collects it as a required checkbox before this call fires (see frontend doc Section 15.3). Store it: add `submitter_confirmed_rights boolean not null default false` to `studies` in a new migration `0002_gap_closing.sql`.

### 12.2 Page-level error handling inside a session (FR-3.6)

A page load error, redirect loop, or timeout **mid-session** must not crash the job or kill the whole session — it's a normal thing a real user encounters. Add `'page_error'` to the `interaction_events.event_type` check constraint. On a page error during `run_agent_session`'s loop: log a `page_error` event with the error detail in `details`, then let `decide()` choose what a real user would do next (retry, go back, abandon) rather than the runner hard-failing. Only abort the whole session if the *entry* URL itself is unreachable at start (that's a study-level failure, per M2).

### 12.3 Dead-end / broken-flow detection (FR-8.4)

Add `'dead_end'` to the same `event_type` constraint. When `decide()` determines it has hit a genuine dead end (no visible way forward toward the goal, or a broken link/button), log a `dead_end` event instead of silently backtracking. `analyze_session` should specifically scan for these and surface them as a distinct `findings` entry (`type='dislike'`, description naming the specific dead end) rather than letting them get absorbed into generic friction commentary.

### 12.4 Multi-path testing (FR-8.3, P1 — can trail by a sprint)

Not required for the first working version. When you get to it: allow `run_agent_session` to optionally re-run a persona a second time with an instruction to find an *alternate* route to the same goal if the first path succeeded easily, to test whether the site offers just one workable path or several. Gate this behind a per-study flag so it doesn't double session cost by default.

### 12.5 Segment-level cross-persona insights (FR-15.2)

In `synthesize_study`, don't only generate study-wide pattern statements — also group findings by `personas.audience_segment_id` and ask the model explicitly for segment-level differences ("non-technical users struggled more with onboarding than technical users"). Populate `cross_persona_insights.segment_filter` with the segment name when an insight is segment-specific, `null` for study-wide ones.

### 12.6 Recommendation `priority_score` — concrete formula (FR-16.3)

Same principle as `summary_metrics` in Section 7 step 2: don't let the model output an unexplained number. Compute it as:

```
priority_score = (affected_persona_count / total_persona_count) * severity_weight
```

where `severity_weight` is a small fixed scale (e.g. 1.0 = blocks task completion / trust-breaking, 0.6 = causes friction but task still completable, 0.3 = minor annoyance) that `synthesize_study` assigns per recommendation based on the linked findings' `type`. Store `affected_persona_count`, `total_persona_count`, and the chosen `severity_weight` alongside the score (extend the `recommendations` table with these three columns) so the ranking is auditable, not a black box.

### 12.7 Persona-behavior QA/calibration (FR-7.3)

Full automation isn't a V1 requirement — the PRD tags this P1 with an explicit "calibration/QA loop" as mitigation, not a live system. Concretely for V1: maintain a small fixed set of 2–3 "known-friction" test pages (sites you've manually verified have real usability problems) and, whenever you materially change the `decide()` prompt, re-run a study against them and check that a non-zero share of sessions report `distrust`/`confused`/`abandoned` findings. If a prompt change makes agents report zero friction against a page you know has friction, that prompt change made the agent too cooperative — revert or adjust. Document this as a manual pre-release check, not a runtime system.

### 12.8 Data retention & deletion (PRD Section 16)

- Add a default retention window (e.g. 90 days) for session screenshots, configurable via `SCREENSHOT_RETENTION_DAYS` env var.
- Add a new job type `purge_expired_sessions`, enqueued on a schedule (cron, or a periodic check in the worker's poll loop): finds `agent_sessions` older than the retention window, deletes their Supabase Storage screenshot objects, and nulls out `interaction_events.screenshot_ref` for them. Postgres FK cascades already handle deleting DB rows when a `study` is deleted directly, but **Storage objects are not covered by FK cascade** — you must explicitly delete them.
- On a user-initiated study deletion (a direct Supabase `DELETE` on their own `studies` row, which they can do via RLS), the DB rows cascade automatically, but the orphaned Storage screenshots won't clean themselves up. Add `DELETE /api/studies/{id}/purge-storage` (auth-checked like every other endpoint) that the frontend calls right before or right after the Supabase-side delete, to remove that study's screenshot objects from Storage.

### 12.9 Server-side analytics events (PRD Section 17)

Add a lightweight table (not the same as `llm_usage_log`, which is for cost, not product analytics):

```sql
create table public.analytics_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete set null,
  study_id uuid references public.studies(id) on delete set null,
  event_name text not null,
  properties jsonb not null default '{}',
  occurred_at timestamptz not null default now()
);
alter table public.analytics_events enable row level security;
-- no policies -> deny-all to authenticated users; service role only, this is for internal reporting, not user-facing
```

Emit rows from the worker for the server-originated events in Section 17's list: `persona_generated`, `persona_regenerated`, `agent_session_started`, `agent_session_completed`, `agent_session_failed`. The remaining events in that list (study started, step completed, dashboard viewed, etc.) are UI-originated — see frontend doc Section 15.4.

### 12.10 Bot-detection / CAPTCHA graceful degradation (PRD risk table + Open Question #3)

`robots.txt` allowing access doesn't mean the site won't still block the agent at runtime (Cloudflare challenge, CAPTCHA, 403/429 responses). After each navigation in `run_agent_session`, check for these signals. If detected: don't retry-loop — mark that session `outcome='error'`, `outcome_reason='target site blocked automated access'`, stop cleanly, and let the study's other persona sessions continue independently (existing partial-failure handling already covers this). The dashboard must show this as a distinct, clearly-worded state, not a generic failure — see frontend Section 15.7.

### 12.11 Persona count bounds (cost-control backstop)

Enforce server-side: minimum 1, maximum `MAX_PERSONAS_PER_STUDY` (env var, default 10) total personas per study. Reject `POST /api/studies/{id}/personas/generate` if it would exceed the max. This is the concrete backstop for the PRD's "LLM/agent cost scales faster than revenue" risk — a config default isn't a mitigation until something actually enforces it.

### 12.12 Minimize data sent to the LLM (PRD's vendor data-handling note)

Before `site_context` goes into any LLM prompt, strip it to visible text/structure only — no raw HTML, no script/style tags, no hidden form-field names or embedded tracking/personal data from the target site. This is what "avoid sending sensitive customer data unnecessarily" (Section 16) actually requires in code, not just a policy line.