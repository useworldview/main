# UseWorldview — Frontend Build Specification (v1 / MVP)

Companion document: `UseWorldview_Backend_Build_Spec.md` — they share ONE API contract (Section 8 here = Section 6 there). If the backend isn't built yet, you can still build almost everything here, since most of the app talks to Supabase directly, not to the backend.

---

## 0. How To Use This Doc With Claude Code

- Run this in its **own repo / own Claude Code session**, separate from the backend.
- Build in the milestone order in **Section 12**, one at a time, verifying each in the browser before moving on.
- If the backend API isn't live yet: everything except the 4 action calls in Section 8 works against Supabase directly and can be built and tested independently. Stub the 4 action calls behind a small `lib/api.ts` wrapper so swapping in the real backend later is a one-file change.

---

## 1. Tech Stack (decided, don't relitigate)

| Concern | Choice |
|---|---|
| Framework | Next.js 14+, App Router, TypeScript |
| Styling / components | Tailwind CSS + shadcn/ui |
| Auth | **Supabase Auth** via `@supabase/ssr` (cookie-based sessions) — email/password + Google OAuth |
| Data fetching/cache | TanStack Query, wrapping the Supabase client for reads |
| Realtime | Supabase Realtime (`postgres_changes`) for live study/session status |
| Charts | Recharts |
| Theming | `next-themes`, light default, persisted to `profiles.theme_preference` |
| Forms/validation | React Hook Form + Zod |

---

## 2. Repo Structure

```
useworldview-frontend/
  app/
    layout.tsx                      # root layout, ThemeProvider
    (marketing)/
      layout.tsx
      page.tsx                      # homepage — Section 6
    (auth)/
      sign-in/page.tsx
      sign-up/page.tsx
      auth/callback/route.ts        # OAuth callback handler
    (app)/
      layout.tsx                    # protected shell: topnav, theme toggle, sign out
      dashboard/page.tsx            # study list + empty state
      studies/
        new/page.tsx                # creation wizard, step state in the studies row itself
        [studyId]/
          page.tsx                  # results dashboard
          personas/[personaId]/page.tsx
          personas/[personaId]/replay/page.tsx
          recommendations/page.tsx
      settings/page.tsx
  components/
    marketing/                      # homepage sections
    auth/
    studies/
      wizard/
    dashboard/
    replay/
    ui/                             # shadcn primitives
  lib/
    supabase/
      client.ts                    # browser client
      server.ts                    # server component / route handler client
    api.ts                          # the 4 backend action calls, Bearer token attached
    types.ts                       # mirrors backend Section 10 schema
    queries.ts                     # TanStack Query hooks over Supabase reads
  middleware.ts                     # protects (app)/* routes
  tailwind.config.ts
  .env.local.example
  README.md
```

---

## 3. Environment Variables

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_BACKEND_API_URL=          # the FastAPI service from the backend doc
```

Never put the Supabase service-role key in this repo — anon key + RLS only.

---

## 4. Auth Flow (Supabase Auth)

- **Sign up**: email/password, plus "Continue with Google" (OAuth minimum per PRD FR-1.1). Supabase's default email-confirmation flow applies.
- **Sign in**: same two methods.
- Use `@supabase/ssr`'s `createBrowserClient` in client components and `createServerClient` in server components/route handlers, sharing session via cookies.
- A `profiles` row is auto-created by the DB trigger in the backend's migration (Section 10 there) — don't duplicate that logic here, just assume it exists after first sign-in.
- `middleware.ts`: unauthenticated users hitting `/dashboard` or `/studies/*` get redirected to `/sign-in`; authenticated users hitting `/sign-in` or `/sign-up` get redirected to `/dashboard`.
- Sign-out button lives in the app shell topnav.
- Target: sign-up → land on the "Create New Study" CTA in under 60 seconds (PRD acceptance criterion for FR-1).

---

## 5. Site Map

**Public (no auth):** `/`, `/sign-in`, `/sign-up`

**App (auth required):**
- `/dashboard` — study list, primary CTA "Create New Study" (FR-1.2)
- `/studies/new` — creation wizard
- `/studies/[id]` — results dashboard, or live progress if still running
- `/studies/[id]/personas/[personaId]` — persona detail
- `/studies/[id]/personas/[personaId]/replay` — journey replay
- `/studies/[id]/recommendations` — recommendations list
- `/settings` — theme preference, minimal account info

---

## 6. Homepage Spec (`/`) — "everything about UseWorldview," in this order

1. **Nav** — logo, "How it works," "Who it's for," Sign in, primary CTA "Get Started."
2. **Hero** — the product in one sentence ("Give UseWorldview a URL and a goal — it creates AI users, sends them into your product, and tells you what happened and why"), primary CTA, a simple illustrative visual (a mock persona/journey card — clearly illustrative, not a real study).
3. **Problem** — the 5 problems from PRD Section 2 as a scannable grid (expensive/slow research, small samples, shallow AI tools, no "why," feedback arrives too late) — not a wall of text.
4. **How it works** — the core flow (PRD Section 9) condensed into ~6 visual steps: define goal → submit URL → AI builds personas → personas use your product → they explain why → you get prioritized recommendations.
5. **What makes it different** — 3–4 row comparison: competitors scan a homepage and output a checklist; UseWorldview enters the app, navigates multiple pages, and produces persona-level evidence-backed narratives.
6. **Who it's for** — the 5 buyer personas from PRD Section 6 as cards, each with its "key question" (e.g. founder: "Will people understand and trust what I built?").
7. **Depth preview** — 3 feature highlights: the Worldview Engine (full psychographic personas, not demographic tags), Whole-App Exploration (not homepage-only), the Recommendations Engine (Problem→Evidence→Affected Users→Why It Matters→Suggested Improvement, cite PRD Section 23's format).
8. **CTA band** — "Get Started."
9. **Footer** — product links, a line noting that submitters must have the right to test the URL they submit (this is a real ToS requirement from PRD Section 16, not filler), copyright.

**One explicit call before you build this:** there are no design partners or case studies for this product yet. Do not put fabricated customer logos, usage counts, or testimonial quotes anywhere on this page — build honest positioning instead ("Now onboarding early design partners," with an apply/waitlist CTA if you want a social-proof-shaped section). Fake social proof here creates the exact claims-vs-evidence gap that's already a known problem on Truebases's own site — don't repeat it on the product site.

---

## 7. Study Creation Wizard (`/studies/new`)

One focused step at a time (PRD Section 15 explicitly rules out a dense all-in-one form):

1. **Research goal** — template list (trust, value proposition, first impression, usability, navigation, onboarding, feature discoverability, pricing perception, conversion experience, purchase intent, signup experience, overall product experience, specific user journey) with multi-select, plus a free-text custom-goal option.
2. **Target URL** — validated for reachability before advancing.
3. **Audience segments** — calls backend `POST /studies` on step 1→2 transition (or on entering this step), then shows detected segments once `studies.status` flips to `audience_ready`. Subscribe to the `studies` row via Realtime rather than polling; edit/add/remove segments write straight to Supabase.
4. **Personas** — calls backend `POST /studies/{id}/personas/generate`; list with edit/regenerate/duplicate/delete (edits/duplicates/deletes are direct Supabase writes; regenerate calls the backend); persona-count control.
5. **Review & deploy** — calls backend `POST /studies/{id}/deploy`, then redirects to `/studies/[id]` to watch it run.

Persist wizard position in the `studies.status` field itself so a page refresh doesn't lose progress — don't invent separate client-only wizard state for this.

---

## 8. Backend Action Calls (the ONLY calls that hit the Python backend)

Mirror of the backend doc's Section 6 — keep these two lists identical.

```ts
POST {BACKEND_API_URL}/api/studies
  body: { target_url, research_goals: [{ type: "template" | "custom", value: string }] }

POST {BACKEND_API_URL}/api/studies/{id}/personas/generate
  body: { segment_ids: string[], personas_per_segment?: number }

POST {BACKEND_API_URL}/api/personas/{id}/regenerate
  body: {}

POST {BACKEND_API_URL}/api/studies/{id}/deploy
  body: {}

POST {BACKEND_API_URL}/api/studies/{id}/retry-failed-sessions
  body: {}
```

Every call attaches `Authorization: Bearer <supabase access token>`. Everything else — every list view, every detail view, every status update, every "mark recommendation useful" click, the theme toggle — is a Supabase read or write straight from the client, RLS-protected.

---

## 9. Results Dashboard (`/studies/[id]`)

- **While running**: live per-persona progress (X/Y sessions completed), Realtime-subscribed to `agent_sessions` filtered by `study_id`.
- **Once completed**: overall metrics from `studies.summary_metrics` (trust score, value-prop clarity, usability score, completion rate, conversion intent — computed backend-side as plain ratios, see backend doc Section 7 step 2, so display them with their underlying counts rather than as a bare unexplained number, per the PRD's "no black box" requirement).
- Major friction points / positive moments — top `findings` grouped by frequency.
- Persona cards grid → click through to persona detail.
- A recommendations tab/section.
- Target: a user should understand top-line results without opening any individual persona (PRD acceptance criterion for FR-12), scannable in under 60 seconds (Section 15).

---

## 10. Persona Detail (`/studies/[id]/personas/[personaId]`)

One view answering "who were they, what did they do, and why did they end up where they did?" (PRD FR-13 acceptance criterion): identity/worldview panel, goal, navigation path, likes/dislikes/confusion/trust signals/feelings (from `findings`), decisions and rationale (from `decision_explanations`), outcome (completed/abandoned + why). Link out to the replay.

---

## 11. Journey Replay (`/.../replay`)

Step-by-step player over `interaction_events`: screenshot + the persona's reasoning/reaction at each step, play/pause, and a scrub control to jump to any step (not just linear playback — PRD FR-14.3). Should feel like watching someone use the product, not reading a log file (Section 15) — so lead with the screenshot, reasoning text alongside it, raw event metadata collapsed by default.

---

## 12. Design Language & Theming

- Light-first, modern SaaS aesthetic: generous whitespace, strong type hierarchy, dashboard-oriented layout (PRD Section 15).
- Dark mode via `next-themes`, toggle in the app shell, default light, persisted to `profiles.theme_preference` and applied on load.
- Progressive disclosure everywhere: dashboard summary first, detail on click, raw event log never shown by default.
- WCAG 2.1 AA where practical; responsive down to ~375px width.

---

## 13. Build Milestones

| # | Milestone | Definition of done |
|---|---|---|
| M0 | Scaffold, Tailwind + shadcn, Supabase client, theme provider | App boots, theme toggle works locally |
| M1 | Homepage (Section 6) | All 9 sections render, no fake social proof |
| M2 | Auth pages + middleware | Sign up, confirm, sign in, Google OAuth, protected-route redirects all work end-to-end |
| M3 | Dashboard shell + empty state | New user sees "Create New Study" CTA per FR-1.2 |
| M4 | Wizard steps 1–5 | Can be built/tested against a stubbed backend if the real one isn't live yet |
| M5 | Realtime status/progress wiring | Wizard and results dashboard update live without manual refresh |
| M6 | Results dashboard (Section 9) | Scannable top-line results, no individual persona needed |
| M7 | Persona detail (Section 10) | |
| M8 | Journey replay (Section 11) | Scrub works, not just linear play |
| M9 | Recommendations view + accessibility/responsive pass | Problem/Evidence/Affected/Why/Suggested format matches PRD Section 23 exactly |
| M10 | Gap-closing additions (Section 15) — walkthrough, manual persona form, consent checkbox, analytics stub, data deletion, error/dead-end surfacing | Each item in Section 15 verified individually |

---

## 14. Explicit Non-Goals For This Build

Don't build, even if it seems easy to add while you're in there: authenticated-flow testing, native mobile testing, multi-user real-time collaboration, A/B comparison studies, a public API, team roles/SSO. These are all explicitly out of scope for V1 per the PRD (Section 8.2) — adding them now is exactly the kind of scope creep that causes a collapse.

---

## 15. Gap-Closing Additions (build as M10, after M0–M9 work)

These close out PRD requirements the milestones above don't touch.

### 15.1 First-time guided walkthrough (FR-1.3, P1)

On first visit to `/dashboard`, show a short 3–4 step coachmark/tooltip sequence pointing at the "Create New Study" CTA and briefly explaining the flow. Dismissible, doesn't reappear after. A `localStorage` flag (`uw_seen_walkthrough`) is sufficient for V1 — no schema change needed. Note for later: if you want it to persist across devices, that needs a `profiles` column, which is a backend-doc change, not something to add here unilaterally.

### 15.2 Manual persona authoring from scratch (FR-5.5, P1)

In the wizard's persona step, add an "Add persona manually" action alongside AI-generated ones: a full form covering every `worldview` and `situational_context` field (same fields the AI generates — name, age, location, profession, income, education, technical ability, digital literacy, goals, motivations, prior experience, personality traits, habits, preferences, fears, frustrations, expectations, trust level, price sensitivity, decision-making style, risk tolerance, attention span, patience level, familiarity with similar products). This is a direct Supabase insert into `personas` — no backend call, since no AI is involved in a hand-authored persona.

### 15.3 Consent checkbox at URL submission (resolves PRD Open Question #7)

On the wizard's "Target URL" step, before the user can advance: a required checkbox — "I confirm I own this site or have permission to run automated testing against it." Its value is sent as `confirmed_authorized` in the `POST /api/studies` call (backend doc Section 12.1 rejects the request without it). Don't let the URL field advance the wizard without this checked.

### 15.4 Client-side analytics events (PRD Section 17)

Stub a tool-agnostic `lib/analytics.ts` with a single `track(eventName: string, properties?: Record<string, unknown>)` function (no-op or console.log for now — wire to a real provider later, that's a business decision, not an engineering one to make silently here). Call it at these points: `study_creation_started`, `study_wizard_step_completed` (with step number), `study_creation_abandoned` (wizard unmounted before deploy), `persona_generated`, `persona_edited`, `persona_deployed`, `dashboard_viewed`, `persona_detail_viewed`, `replay_opened`, `replay_completed`, `recommendation_viewed`, `recommendation_status_changed`, `theme_toggled`.

### 15.5 Data deletion UI (PRD Section 16)

On `/settings` (or a delete action on each study card), add "Delete study" with a confirmation dialog. On confirm: call `DELETE` on the study's Supabase row directly (RLS-scoped, cascades to all child rows per the backend schema), **then** call backend `DELETE /api/studies/{id}/purge-storage` (backend doc Section 12.8) to clean up the associated screenshots in Storage — the two calls are both required, the Supabase delete alone leaves orphaned Storage objects.

### 15.6 Surfacing page-level errors / dead ends (pairs with backend Section 12.2/12.3)

In the journey replay and persona detail views, render `page_error` and `dead_end` events distinctly (e.g. a small warning-styled marker in the replay timeline) rather than showing them as generic steps — these are meaningfully different from a normal click/scroll and stakeholders should be able to spot them at a glance.

### 15.7 Surfacing blocked-site outcomes (pairs with backend Section 12.10)

When a session's `outcome_reason` indicates the target blocked automated access, show that distinctly on the results dashboard and persona card — "This site blocked automated testing" — not as a generic failure. It's a site-protection issue, not a bug in the customer's product or in UseWorldview, and the UI should make that distinction obvious. Also cap the persona-count control in the wizard at the same max as the backend enforces (Section 12.11) so the UI never lets someone submit a request the backend will just reject.