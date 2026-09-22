-- UseWorldview Backend — Database Schema (v1)
-- Run this migration against your Supabase project FIRST before starting the backend.

-- ============================================================================
-- PROFILES (auto-created on signup via trigger)
-- ============================================================================

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

-- ============================================================================
-- STUDIES
-- ============================================================================

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
  confirmed_authorized boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);

-- ============================================================================
-- AUDIENCE SEGMENTS
-- ============================================================================

create table public.audience_segments (
  id uuid primary key default gen_random_uuid(),
  study_id uuid not null references public.studies(id) on delete cascade,
  name text not null,
  description text,
  source text not null check (source in ('detected','edited','manual')),
  created_at timestamptz not null default now()
);

-- ============================================================================
-- PERSONAS
-- ============================================================================

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

-- ============================================================================
-- AGENT SESSIONS
-- ============================================================================

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

-- ============================================================================
-- INTERACTION EVENTS
-- ============================================================================

create table public.interaction_events (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.agent_sessions(id) on delete cascade,
  sequence_no int not null,
  event_type text not null check (event_type in
    ('click','scroll','type','navigate','search','back','forward','wait','screenshot','form_submit','page_error','dead_end','overlay_dismissed')),
  target_element text,
  page_url text,
  details jsonb not null default '{}',
  screenshot_ref text,
  reasoning text,
  occurred_at timestamptz not null default now()
);

-- ============================================================================
-- FINDINGS
-- ============================================================================

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

-- ============================================================================
-- DECISION EXPLANATIONS
-- ============================================================================

create table public.decision_explanations (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.agent_sessions(id) on delete cascade,
  decision_type text not null check (decision_type in ('signup','purchase','feature_use','abandon','other')),
  rationale_text text not null,
  linked_event_ids uuid[] not null default '{}',
  created_at timestamptz not null default now()
);

-- ============================================================================
-- CROSS-PERSONA INSIGHTS
-- ============================================================================

create table public.cross_persona_insights (
  id uuid primary key default gen_random_uuid(),
  study_id uuid not null references public.studies(id) on delete cascade,
  statement text not null,
  supporting_persona_count int not null,
  total_persona_count int not null,
  segment_filter text,
  created_at timestamptz not null default now()
);

-- ============================================================================
-- RECOMMENDATIONS
-- ============================================================================

create table public.recommendations (
  id uuid primary key default gen_random_uuid(),
  study_id uuid not null references public.studies(id) on delete cascade,
  problem text not null,
  evidence text not null,
  affected_users text not null,
  why_it_matters text not null,
  suggested_improvement text not null,
  priority_score numeric not null default 0,
  affected_persona_count int not null default 0,
  total_persona_count int not null default 0,
  severity_weight numeric not null default 0.6,
  status text not null default 'new' check (status in ('new','useful','not_relevant','already_fixed')),
  created_at timestamptz not null default now()
);

-- ============================================================================
-- INTERNAL JOB QUEUE (never exposed to frontend)
-- ============================================================================

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

-- ============================================================================
-- LLM USAGE LOG (cost tracking)
-- ============================================================================

create table public.llm_usage_log (
  id uuid primary key default gen_random_uuid(),
  study_id uuid references public.studies(id) on delete set null,
  session_id uuid references public.agent_sessions(id) on delete set null,
  purpose text not null,
  model_name text,
  provider text,
  input_tokens int,
  output_tokens int,
  estimated_cost_usd numeric,
  created_at timestamptz not null default now()
);

-- ============================================================================
-- ANALYTICS EVENTS (server-side product analytics)
-- ============================================================================

create table public.analytics_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete set null,
  study_id uuid references public.studies(id) on delete set null,
  event_name text not null,
  properties jsonb not null default '{}',
  occurred_at timestamptz not null default now()
);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Users only ever see their own studies and everything under them.
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

-- agent_jobs, llm_usage_log, analytics_events: RLS enabled, NO policies -> deny-all to authenticated users.
-- Only the service-role key (used exclusively by this backend/worker) can touch them.
alter table public.agent_jobs enable row level security;
alter table public.llm_usage_log enable row level security;
alter table public.analytics_events enable row level security;

-- ============================================================================
-- INDEXES for performance
-- ============================================================================

create index idx_studies_user_id on public.studies(user_id);
create index idx_studies_status on public.studies(status);
create index idx_audience_segments_study_id on public.audience_segments(study_id);
create index idx_personas_study_id on public.personas(study_id);
create index idx_agent_sessions_study_id on public.agent_sessions(study_id);
create index idx_agent_sessions_persona_id on public.agent_sessions(persona_id);
create index idx_agent_sessions_status on public.agent_sessions(status);
create index idx_interaction_events_session_id on public.interaction_events(session_id);
create index idx_interaction_events_sequence on public.interaction_events(session_id, sequence_no);
create index idx_findings_session_id on public.findings(session_id);
create index idx_decision_explanations_session_id on public.decision_explanations(session_id);
create index idx_cross_persona_insights_study_id on public.cross_persona_insights(study_id);
create index idx_recommendations_study_id on public.recommendations(study_id);
create index idx_agent_jobs_status on public.agent_jobs(status, created_at);
create index idx_llm_usage_log_study_id on public.llm_usage_log(study_id);

-- ============================================================================
-- STORAGE BUCKET for screenshots
-- ============================================================================
-- Run this separately in the Supabase dashboard or via the management API:
-- Create a bucket named 'screenshots' with public access disabled.
-- insert into storage.buckets (id, name, public) values ('screenshots', 'screenshots', false);
