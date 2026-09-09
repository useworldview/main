# UseWorldview — Product Requirements Document (PRD)

| | |
|---|---|
| **Document** | UseWorldview — Core Platform PRD |
| **Version** | v1.0 |
| **Status** | Draft for Review |
| **Owner** | Abhinav Sharma, Truebases |
| **Author** | Product Team, Truebases |
| **Last Updated** | September 2026 |
| **Classification** | Internal — Confidential |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Product Vision](#3-product-vision)
4. [Goals & Objectives](#4-goals--objectives)
5. [Success Metrics (KPIs)](#5-success-metrics-kpis)
6. [Target Customers & Buyer Personas](#6-target-customers--buyer-personas)
7. [Competitive Landscape & Differentiation](#7-competitive-landscape--differentiation)
8. [Scope](#8-scope)
9. [Core Product Flow](#9-core-product-flow)
10. [Detailed Functional Requirements](#10-detailed-functional-requirements)
11. [Non-Functional Requirements](#11-non-functional-requirements)
12. [System Architecture](#12-system-architecture)
13. [Data Model](#13-data-model)
14. [AI Agent Architecture](#14-ai-agent-architecture)
15. [UX / UI Requirements](#15-ux--ui-requirements)
16. [Security, Privacy & Ethics](#16-security-privacy--ethics)
17. [Analytics & Instrumentation](#17-analytics--instrumentation)
18. [Risks & Mitigations](#18-risks--mitigations)
19. [Assumptions & Dependencies](#19-assumptions--dependencies)
20. [Release Plan & Phasing](#20-release-plan--phasing)
21. [Open Questions](#21-open-questions)
22. [Glossary](#22-glossary)
23. [Appendix: Recommendation Format Spec](#23-appendix-recommendation-format-spec)

---

## 1. Executive Summary

**UseWorldview** is an AI-powered synthetic user research platform. It lets companies deploy AI-generated users — each with a fully-formed persona and "worldview" — into their live website or web application. These AI users autonomously explore, navigate, and interact with the product exactly as a real prospective customer would, and then report back on what they liked, disliked, trusted, distrusted, and why they completed or abandoned their goal.

Where existing UX-analysis tools stop at "scan a URL and generate a homepage report," UseWorldview treats research as a **lived experience**: an AI persona is given an identity, a context, and a goal, and is set loose inside the entire product to behave the way that person actually would. The output is not a generic audit — it is persona-specific, evidence-backed, and explainable, and it aggregates into cross-persona patterns and prioritized recommendations.

This document defines the V1 product requirements: the end-to-end user flow, the functional and non-functional requirements for every stage of that flow, the system and AI-agent architecture, and the phased rollout plan.

---

## 2. Problem Statement

Companies building digital products need to understand how real users experience their product — but traditional research is slow, expensive, and hard to scale:

- **User research is expensive and slow.** Recruiting, scheduling, and moderating sessions with real users takes days to weeks and thousands of dollars per study.
- **Sample sizes are small.** Most usability studies run 5–10 participants, which limits confidence and misses edge-case audience segments.
- **Existing "AI UX" tools are shallow.** Competing tools typically ingest a URL, review the homepage, and output a generic UX report. They do not enter the product, do not navigate multiple pages, and do not simulate a believable person with motivations, doubts, and biases.
- **Teams lack a "why."** Analytics tools (heatmaps, session replays, funnels) show *what* users did, but not *why* — what they were thinking, what confused them, what almost made them leave.
- **Feedback arrives too late.** Most research happens post-launch, once real users have already had a bad experience, rather than continuously, pre-launch, or pre-redesign.

UseWorldview addresses this by making believable, persona-driven, whole-application research available on demand, at a fraction of the cost and time of traditional studies.

---

## 3. Product Vision

> **Give UseWorldview a product and a research goal. It creates the people, puts them inside the product, lets them experience it from their own worldview, and tells you what happened — and why.**

Long-term, UseWorldview aims to become the default way product, growth, design, and marketing teams validate any user-facing experience *before* and *after* it ships — replacing ad hoc usability testing with an always-available panel of believable synthetic users.

---

## 4. Goals & Objectives

### 4.1 Business Goals
- Establish UseWorldview as Truebases's flagship AI research product and a category-defining entry in "synthetic user research."
- Acquire early design-partner customers (SaaS, e-commerce, fintech) to validate willingness to pay and refine the product.
- Build defensible IP around the **persona/worldview engine** and **whole-application autonomous browsing agent**, both of which are the primary differentiators versus homepage-scan competitors.

### 4.2 Product Goals (V1)
- Let a user go from "I have a URL and a question" to "I have a persona-level, evidence-backed research report" in a single guided flow, with no login required on the target site.
- Ensure AI personas behave with realistic skepticism, confusion, and friction — not artificially cooperative behavior that flatters the product.
- Make every finding traceable: every insight in the dashboard should be explainable by pointing to a specific action, page, or moment in a persona's session.
- Turn individual persona experiences into aggregate, statistically-framed, cross-persona insights and prioritized recommendations.

### 4.3 Non-Goals (V1)
- UseWorldview V1 is not a replacement for quantitative analytics (heatmaps, funnels) — it is a qualitative, explanatory research layer.
- V1 does not test authenticated/logged-in flows.
- V1 does not run on native mobile apps (iOS/Android) — web only.

---

## 5. Success Metrics (KPIs)

| Metric | Definition | V1 Target |
|---|---|---|
| **Time to first insight** | Time from URL submission to first completed persona report | < 15 minutes for a 5-page site |
| **Study completion rate** | % of started studies that reach a finished dashboard | > 90% |
| **Persona believability score** | Human-rated realism of AI persona behavior (internal QA panel, 1–5 scale) | ≥ 4.0 average |
| **Insight actionability rate** | % of recommendations customers mark as "useful" / "would act on" | ≥ 70% |
| **Whole-app exploration depth** | Average distinct pages/screens visited per persona per session | ≥ 3 pages beyond entry page |
| **Customer activation** | % of signed-up accounts that complete one full study within 7 days | ≥ 50% |
| **Design-partner retention** | % of early design partners still active after 60 days | ≥ 60% |

---

## 6. Target Customers & Buyer Personas

UseWorldview's *customers* are product, design, growth, and founder teams. (These are distinct from the *AI personas* the platform generates — see Section 10.5.)

| Persona | Role | Primary Use Case | Key Question They're Asking |
|---|---|---|---|
| **Startup Founder** | Early-stage SaaS/DTC founder | Pre-launch and post-launch validation with no research budget | "Will people understand and trust what I built?" |
| **Product Manager** | Mid-market/enterprise PM | Feature and onboarding validation before/after ship | "Why are users dropping off in this flow?" |
| **UX / Product Designer** | In-house or agency designer | Usability and navigation testing on new designs | "Where are users getting confused or stuck?" |
| **Growth / Conversion Marketer** | Growth lead, CRO specialist | Landing page, pricing, and signup conversion testing | "What's stopping visitors from converting?" |
| **Technical Founder / Eng Lead** | Developer tools, infra products | Onboarding and docs usability for developer audiences | "Can a new developer actually get started with this?" |

---

## 7. Competitive Landscape & Differentiation

| Dimension | Typical Competitors ("AI UX report" tools) | UseWorldview |
|---|---|---|
| Depth of review | Homepage only | Enters the app, discovers and navigates multiple pages |
| Persona depth | Basic demographic tags (age, gender, device) | Full worldview: motivations, fears, trust, price sensitivity, digital literacy, prior experience |
| Behavior model | Assumes the product is good; flatters the design | Skeptical, realistic; can get confused, distrust, or abandon |
| Output | Generic scored checklist | Persona-level narrative + evidence + cross-persona statistical patterns |
| Explainability | Rarely explains *why* a score was given | Every insight traces to specific actions/pages in a session |
| Scale | Single generic "AI reviewer" | N configurable personas representing distinct audience segments |

**Core differentiator, stated simply:**

> Competitors: `URL → Review homepage → Generate UX report`
> UseWorldview: `URL → Enter application → Navigate → Discover pages → Interact with features → Perform tasks → Observe behavior → Generate user insights`

---

## 8. Scope

### 8.1 In Scope (V1)
- Account creation and sign-in.
- Research goal definition (templated + custom).
- Public (non-authenticated) website/web app submission and multi-page autonomous exploration.
- Automatic target audience detection with manual edit.
- AI persona generation with full worldview attributes, editable by the user.
- Autonomous AI browser agents that navigate, interact with, and attempt goals on the target site.
- Session capture: actions, navigation paths, timings, errors, backtracking.
- Post-session persona reporting: likes, dislikes, feelings, trust signals, decision rationale.
- Results dashboard: overall study results, persona-level detail, journey replay.
- Cross-persona pattern detection and aggregate statistics.
- Actionable recommendations engine (Problem → Evidence → Affected Users → Why It Matters → Suggested Improvement).
- Light-first UI with dark mode toggle and persisted theme preference.

### 8.2 Out of Scope (V1 — candidates for V2+)
- Authenticated/login-gated flow testing.
- Native mobile app (iOS/Android) testing.
- Real-time collaborative study editing (multi-user).
- A/B comparison of two live versions of a product in a single study.
- Integrations with external analytics tools (e.g., importing real session-replay data alongside AI-user data).
- Team roles/permissions, SSO, enterprise admin console.
- Public API for programmatic study creation.
- Scheduled/recurring studies ("run this every release").

---

## 9. Core Product Flow

```
Sign In
  ↓
Define What You Want to Test
  ↓
Enter Website / Web App URL
  ↓
UseWorldview Understands the Product
  ↓
Automatically Detect Target Audience
  ↓
Edit Target Audience
  ↓
Create AI Personas
  ↓
Define Each Persona's Worldview + Context
  ↓
Deploy AI Users
  ↓
AI Users Enter the Web App
  ↓
Explore + Navigate + Interact Across the Whole Product
  ↓
Observe Actions + Decisions + Feelings + Friction
  ↓
AI Users Complete / Abandon Their Goals
  ↓
Explain Why They Did What They Did
  ↓
Individual Persona Results
  ↓
Cross-Persona Analysis
  ↓
Overall Product Insights
  ↓
Actionable Recommendations
```

---

## 10. Detailed Functional Requirements

Each requirement is tagged with an ID, priority (**P0** = required for V1 launch, **P1** = important but can trail V1 by a sprint, **P2** = desirable, can slip to V2), and acceptance criteria.

### 10.1 FR-1: Authentication & Onboarding

| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | User can create an account via email/password or OAuth (Google minimum). | P0 |
| FR-1.2 | User lands on a dashboard focused on a single primary action: "Create New Study." | P0 |
| FR-1.3 | First-time users see a lightweight guided walkthrough of the study-creation flow. | P1 |

**Acceptance criteria:** A new user can sign up, verify identity, and reach the "Create New Study" CTA in under 60 seconds.

### 10.2 FR-2: Define Research Goal

| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | User selects from a library of templated research goals (trust, value proposition, first impression, usability, navigation, onboarding, feature discoverability, pricing perception, conversion experience, purchase intent, signup experience, overall product experience, specific user journey). | P0 |
| FR-2.2 | User can instead write a free-text custom research goal (e.g., "I want to understand why first-time visitors don't sign up for my SaaS product"). | P0 |
| FR-2.3 | Selected/entered goal is used to condition persona behavior, exploration priorities, and the final report structure. | P0 |
| FR-2.4 | User can select more than one goal per study. | P1 |

**Acceptance criteria:** The chosen goal measurably changes what the AI persona prioritizes during exploration (e.g., a "pricing perception" goal causes personas to seek out and evaluate the pricing page).

### 10.3 FR-3: Website / Web App Submission & Exploration

| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | User submits a public URL; the app must not require login in V1. | P0 |
| FR-3.2 | System validates the URL is reachable and renders before proceeding. | P0 |
| FR-3.3 | Exploration is not limited to the homepage — the agent must be able to discover and traverse linked pages. | P0 |
| FR-3.4 | AI users can navigate menus, use in-page search, scroll, go backward/forward, and follow internal links the way a human would. | P0 |
| FR-3.5 | System respects `robots.txt` and reasonable crawl-rate limits on the target site. | P0 |
| FR-3.6 | System detects and gracefully handles pages that error, redirect, or fail to load, without terminating the whole study. | P1 |

**Acceptance criteria:** Given a marketing site with 5+ linked pages, at least one persona visits 3+ distinct pages beyond the entry URL during a session.

### 10.4 FR-4: Target Audience Detection

| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | On URL submission, system analyzes site content/category and proposes a likely target audience (e.g., SaaS → founders, PMs, developers; e-commerce → shoppers, bargain hunters, premium buyers). | P0 |
| FR-4.2 | Detected audience segments are shown to the user as an editable list. | P0 |
| FR-4.3 | User can add, remove, or edit segments, and add free-text context about their real customers. | P0 |

**Acceptance criteria:** For a known product category, the detected audience list matches expert judgment for at least 3 of the top 4 suggested segments.

### 10.5 FR-5: AI Persona Creation ("Worldview Engine")

This is the core differentiating capability of the product.

| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | System generates one or more personas per audience segment (or per user-defined segment). | P0 |
| FR-5.2 | Each persona includes, at minimum: name, age, location, profession, income level, education, technical ability, digital literacy, goals, motivations, prior experience with similar products, personality traits, habits, preferences, fears, frustrations, expectations, trust level, price sensitivity, decision-making style, risk tolerance, attention span, patience level, and familiarity with similar products. | P0 |
| FR-5.3 | Each persona is given situational context: current situation, reason for visiting the site, what they are trying to accomplish, and what influences their decision. | P0 |
| FR-5.4 | User can view, edit, regenerate, duplicate, or delete any persona before deployment. | P0 |
| FR-5.5 | User can manually author a fully custom persona from scratch. | P1 |
| FR-5.6 | User can control the number of personas per study (with a sensible default, e.g., 3–5). | P0 |

**Acceptance criteria:** A generated persona reads as a coherent individual (not a set of disconnected tags) — e.g., a low-digital-literacy, high-price-sensitivity persona should visibly behave differently in-session than a high-digital-literacy, low-price-sensitivity persona.

### 10.6 FR-6: Autonomous AI Agent Browsing & Interaction

| ID | Requirement | Priority |
|---|---|---|
| FR-6.1 | Each deployed persona is driven by an autonomous agent capable of visual perception (screenshots/DOM) and reasoning over what it sees. | P0 |
| FR-6.2 | Agent can click, scroll, type into forms, use search, open/close menus, and navigate browser-style (back/forward). | P0 |
| FR-6.3 | Agent decisions (what to click next, whether to continue or abandon) are driven by the persona's worldview and the stated research goal — not by a scripted path. | P0 |
| FR-6.4 | Agent maintains session memory across steps (what it has already seen, tried, or decided). | P0 |
| FR-6.5 | Agent has a maximum session length/step budget to prevent runaway sessions, configurable per study. | P0 |
| FR-6.6 | Agent can complete or intentionally abandon a task, and must record its reason for doing so. | P0 |

**Acceptance criteria:** Given the same site, two personas with different risk tolerance/patience attributes produce different navigation paths and different completion/abandonment outcomes.

### 10.7 FR-7: Realistic, Skeptical Behavior

| ID | Requirement | Priority |
|---|---|---|
| FR-7.1 | Agent must not assume the product is good; it must be capable of confusion, suspicion, hesitation, and rejection. | P0 |
| FR-7.2 | Agent-generated internal reactions must be persona-consistent (e.g., "This looks expensive," "I don't want to give my email," "I can't find what I'm looking for"). | P0 |
| FR-7.3 | System includes a QA/calibration mechanism to detect and correct "overly cooperative" agent behavior that doesn't reflect real user skepticism. | P1 |

**Acceptance criteria:** Internal QA review confirms that across a sample of studies, a meaningful share of personas (not 0%) report confusion, distrust, or abandonment where the underlying product genuinely has friction.

### 10.8 FR-8: Whole-Application Exploration Engine

| ID | Requirement | Priority |
|---|---|---|
| FR-8.1 | Exploration is treated as a first-class capability, not a byproduct of task completion. | P0 |
| FR-8.2 | Agent discovers pages via navigation structures (nav bars, footers, in-page links, search) rather than a pre-supplied sitemap. | P0 |
| FR-8.3 | Agent can test multiple distinct paths to the same goal when the site offers them. | P1 |
| FR-8.4 | System identifies and flags dead ends and broken/unreachable flows encountered during exploration. | P1 |

**Acceptance criteria:** The agent's behavior is describable as "you are this person, with this goal — go use this product and tell me what happened," not "review this URL."

### 10.9 FR-9: Session Observation & Recording

| ID | Requirement | Priority |
|---|---|---|
| FR-9.1 | System captures, per session: pages visited, actions taken, clicks, searches, navigation paths, time spent per step, errors encountered, failed attempts, backtracking events, feature usage, and task completion/abandonment status. | P0 |
| FR-9.2 | Session data is stored in a structured, queryable event log (not just free text) to support later aggregation. | P0 |
| FR-9.3 | Screenshots (or equivalent visual state) are captured at key steps to support journey replay. | P0 |

**Acceptance criteria:** Every claim shown later in the dashboard can be traced back to a specific stored event in the session log.

### 10.10 FR-10: Persona Feedback — Likes, Dislikes, Feelings

| ID | Requirement | Priority |
|---|---|---|
| FR-10.1 | After each session, the persona produces structured feedback: what they liked, what they disliked, and what they felt (from a defined feeling taxonomy: confused, interested, excited, frustrated, suspicious, confident, overwhelmed, curious, uncertain, satisfied). | P0 |
| FR-10.2 | "Liked" and "disliked" items are each linked to the specific page/action that produced them. | P0 |

**Acceptance criteria:** Every "liked"/"disliked" statement in a persona report has an associated evidence link (page + action + timestamp).

### 10.11 FR-11: Decision Explanation Engine

| ID | Requirement | Priority |
|---|---|---|
| FR-11.1 | For conversion-relevant moments (signup, purchase, feature use, task abandonment), the system generates a "why" explanation grounded in the persona's worldview and session evidence. | P0 |
| FR-11.2 | Explanations cover, as applicable: what stopped/convinced them, what information was missing or persuasive, whether trust was established, whether the value proposition was clear, whether the CTA was convincing, and whether friction was too high. | P0 |

**Acceptance criteria:** For any completed or abandoned goal, the user can click through to a plain-language "why" written by that persona, backed by at least one cited session event.

### 10.12 FR-12: Results Dashboard — Overall Study Results

| ID | Requirement | Priority |
|---|---|---|
| FR-12.1 | Dashboard shows overall product perception, trust score, value proposition clarity, usability score, task completion rate, and conversion intent, aggregated across personas. | P0 |
| FR-12.2 | Dashboard highlights major friction points and major positive moments, ranked by frequency/severity. | P0 |

**Acceptance criteria:** A user can understand top-line study results without opening any individual persona.

### 10.13 FR-13: Persona-Level Results

| ID | Requirement | Priority |
|---|---|---|
| FR-13.1 | Each persona has a detail view showing: identity/worldview, goal, navigation path, likes, dislikes, points of confusion, trust/distrust signals, feelings, actions, decisions and rationale, and goal outcome (completed/abandoned, converted/not, and why). | P0 |

**Acceptance criteria:** Opening any persona answers "who were they, what did they do, and why did they end up where they did?" without needing another view.

### 10.14 FR-14: Journey Replay

| ID | Requirement | Priority |
|---|---|---|
| FR-14.1 | User can replay a persona's session step-by-step: Persona → Website Entry → Actions → Decisions → Reactions → Outcome. | P0 |
| FR-14.2 | Replay includes captured screenshots/visual state alongside the persona's reasoning/reaction at each step. | P0 |
| FR-14.3 | User can scrub/jump to specific steps rather than only playing linearly. | P1 |

**Acceptance criteria:** A stakeholder unfamiliar with the study can watch a replay and understand "exactly how this persona experienced the product."

### 10.15 FR-15: Cross-Persona Insights

| ID | Requirement | Priority |
|---|---|---|
| FR-15.1 | System aggregates findings across all personas in a study into pattern statements (e.g., "8/10 users understood the value proposition," "6/10 users were confused by the pricing page"). | P0 |
| FR-15.2 | System detects and surfaces segment-level differences (e.g., "non-technical users struggled significantly more with onboarding," "price-sensitive users frequently compared alternatives before continuing"). | P1 |

**Acceptance criteria:** For a study with 5+ personas, the dashboard surfaces at least 3 cross-persona pattern statements with underlying counts shown.

### 10.16 FR-16: Actionable Recommendations Engine

| ID | Requirement | Priority |
|---|---|---|
| FR-16.1 | System converts aggregated findings into prioritized, structured recommendations. | P0 |
| FR-16.2 | Each recommendation follows the format: **Problem → Evidence → Affected Users → Why It Matters → Suggested Improvement** (see Section 23 for the full spec). | P0 |
| FR-16.3 | Recommendations are ranked by estimated impact (e.g., % of personas affected, severity of friction). | P1 |
| FR-16.4 | User can mark a recommendation as "useful," "not relevant," or "already fixed" to improve future studies. | P2 |

**Acceptance criteria:** Every recommendation on the dashboard cites specific evidence and affected personas — no generic, unsourced advice.

### 10.17 FR-17: Theming & UI Preferences

| ID | Requirement | Priority |
|---|---|---|
| FR-17.1 | Default theme is light mode: clean, modern SaaS interface, minimal clutter, strong typography/spacing, dashboard-oriented. | P0 |
| FR-17.2 | Dark mode is available via toggle. | P1 |
| FR-17.3 | Theme preference persists per user across sessions. | P1 |

---

## 11. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | Study creation flow (steps 1–7) should complete in under 5 minutes of active user time. A single persona session (5-page exploration) should complete within a target SLA (e.g., 3–8 minutes), configurable per step budget. |
| **Scalability** | Backend must support running multiple persona agents concurrently within a single study without serializing them unnecessarily. |
| **Reliability** | A single persona/agent failure must not fail the entire study; partial results should still be usable. |
| **Availability** | Target 99.5% uptime for the core web application in V1. |
| **Auditability** | Every insight and recommendation must be traceable to underlying session event data (no "black box" claims). |
| **Cost control** | Agent step budgets, LLM token usage, and browser session time must be bounded and monitored per study to control unit economics. |
| **Accessibility** | Dashboard UI should meet WCAG 2.1 AA where practical for V1. |
| **Internationalization** | V1 can be English-only; architecture should not preclude future localization. |
| **Data retention** | Study data (sessions, recordings, reports) retained per a defined policy (see Section 16) and deletable on request. |

---

## 12. System Architecture

### 12.1 Frontend
- **Framework:** Next.js (React).
- Responsive, dashboard-oriented UI.
- Light/dark theme support with persisted preference.
- Real-time or polling-based status updates while a study is running (persona sessions in progress).

### 12.2 Backend
- **Language/runtime:** Python.
- API/service layer exposing study, persona, and session management endpoints.
- **AI orchestration layer** responsible for: persona generation, audience detection, agent session orchestration, post-session analysis, and recommendation generation.
- Job/queue system to run persona agent sessions asynchronously and in parallel.

### 12.3 Database
- **Supabase** (Postgres + auth + storage) for:
  - User accounts and authentication.
  - Projects / studies.
  - Personas (including full worldview attribute sets).
  - Test runs / study runs.
  - AI-user sessions.
  - Interaction events (structured, queryable log).
  - Findings (likes, dislikes, feelings, decisions).
  - Reports (overall + persona-level + recommendations).

### 12.4 AI / Agent Layer
- LLM-powered persona generation (worldview attribute synthesis from audience segment + product context).
- Autonomous browser agents combining vision (screenshot/DOM understanding) and reasoning (next-action decision-making).
- Browser interaction layer (click, type, scroll, navigate) — headless browser automation.
- Session memory management per agent run.
- Post-test analysis layer: converts raw event logs into structured findings, decision explanations, cross-persona patterns, and recommendations.

### 12.5 High-Level Data Flow

```
[User] → [Next.js Frontend] → [Python API]
                                   ↓
                     [Orchestration Layer: Study/Persona Manager]
                                   ↓
                 ┌─────────────────────────────────────┐
                 │   Per-Persona Agent Session Runner    │
                 │  (Browser Automation + Vision + LLM)  │
                 └─────────────────────────────────────┘
                                   ↓
                    [Structured Event Log → Supabase]
                                   ↓
                  [Post-Session Analysis Layer (LLM)]
                                   ↓
        [Findings, Decision Explanations, Cross-Persona Patterns,
                       Recommendations → Supabase]
                                   ↓
                     [Dashboard API → Frontend]
```

---

## 13. Data Model

High-level entities (illustrative, not exhaustive DDL):

| Entity | Key Attributes |
|---|---|
| **User** | id, email, auth provider, theme preference, created_at |
| **Study** | id, user_id, research_goal(s), target_url, status, created_at, completed_at |
| **AudienceSegment** | id, study_id, name, description, source (detected/edited/manual) |
| **Persona** | id, study_id, audience_segment_id, name, demographic attributes, psychographic attributes (goals, motivations, fears, trust level, price sensitivity, risk tolerance, etc.), context (situation, reason for visiting, objective) |
| **AgentSession** | id, persona_id, study_id, status, start_time, end_time, step_count, outcome (completed/abandoned), outcome_reason |
| **InteractionEvent** | id, session_id, sequence_no, event_type (click/scroll/type/navigate/search/etc.), target_element, page_url, timestamp, screenshot_ref |
| **Finding** | id, session_id, type (like/dislike/feeling/trust/distrust), description, linked_event_id(s) |
| **DecisionExplanation** | id, session_id, decision_type (signup/purchase/feature_use/abandon), rationale_text, linked_event_id(s) |
| **CrossPersonaInsight** | id, study_id, statement, supporting_persona_count, total_persona_count, segment_filter (optional) |
| **Recommendation** | id, study_id, problem, evidence, affected_users, why_it_matters, suggested_improvement, priority_score, status |

---

## 14. AI Agent Architecture

### 14.1 Persona Generation
- Input: detected/edited audience segment + product context (from initial site analysis) + research goal.
- Output: a complete, internally consistent persona object covering identity, psychographics, and situational context (per FR-5.2/5.3).
- Consistency check: generated attributes should not contradict each other (e.g., "high digital literacy" + "struggles to use a mouse" should not co-occur without narrative justification).

### 14.2 Autonomous Browsing Agent
- Combines a vision/DOM-understanding component (to perceive the current page state) with an LLM reasoning component (to decide the next action) conditioned on the persona's worldview and goal.
- Operates in a perceive → decide → act → observe loop, updating session memory after each step.
- Must support standard web interactions: click, type, scroll, hover/open menus, use search, navigate back/forward, submit forms.
- Bounded by a configurable maximum step count and/or time budget per session to control cost and prevent infinite loops.

### 14.3 Post-Session Analysis
- Converts the raw structured event log for a session into: likes/dislikes, feelings, trust/distrust signals, and decision explanations — each linked back to specific events.
- Aggregates across all sessions in a study into cross-persona patterns and prioritized recommendations.

### 14.4 Guardrails
- Agents must not submit real payment information, must not create persistent real-world accounts with real personal data, and must not perform destructive actions (e.g., deleting content) on the target site.
- Agents must respect target-site rate limits and `robots.txt`.
- Session step/time budgets prevent runaway cost or infinite exploration loops.

---

## 15. UX / UI Requirements

- **Theme:** Light-first by default; dark mode available via toggle; preference persists per user (FR-17).
- **Design language:** Clean, modern SaaS aesthetic; minimal visual clutter; strong typographic hierarchy and generous spacing; dashboard-oriented layout.
- **Study creation flow:** A single, focused, step-by-step wizard (goal → URL → audience → personas → deploy) rather than a dense all-in-one form.
- **Dashboard:** Overall results should be scannable in under 60 seconds; drill-down to persona detail and journey replay should be no more than one click away.
- **Journey replay:** Visual, screenshot-driven, with the persona's reasoning/reaction surfaced alongside each step — should feel like watching someone use the product, not reading a log file.
- **Progressive disclosure:** Summary-first, detail-on-demand — avoid overwhelming first-time users with the full raw event log.

---

## 16. Security, Privacy & Ethics

- **No login required (V1):** Agents only interact with publicly accessible pages; no credentials are collected or used on the target site in V1.
- **No real transactions:** Agents must not complete real purchases or submit real payment details, even where forms allow it.
- **Synthetic data only:** Personas and any data they input into forms (e.g., name/email in a signup field) must be clearly synthetic/test data, never real user PII.
- **Respectful crawling:** Agents must honor `robots.txt`, apply reasonable request pacing, and identify themselves via a distinct user agent where required.
- **Target-site consent:** Product should clarify in ToS that users submitting a URL must have the right to test that site (i.e., be the owner or have permission).
- **Customer data isolation:** Each customer's studies, personas, and session data must be logically isolated (row-level security in Supabase).
- **Data retention & deletion:** Define a retention window for session recordings/screenshots and support customer-initiated deletion of a study and all associated data.
- **Model/vendor data handling:** Any data sent to third-party LLM/vision providers must comply with those providers' data-use terms; avoid sending sensitive customer data unnecessarily.

---

## 17. Analytics & Instrumentation

To measure the KPIs in Section 5, instrument the following product events:
- Account created, first study started, study step completed (per wizard step), study abandoned mid-creation.
- Persona generated, persona edited/regenerated, persona deployed.
- Agent session started/completed/failed, step count, duration, outcome.
- Dashboard viewed, persona detail viewed, journey replay opened/completed.
- Recommendation viewed, marked useful/not relevant/already fixed.
- Theme toggled (light/dark).

---

## 18. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Agents behave "too cooperatively" and fail to surface real friction | Low-value, non-credible insights | Calibration/QA loop (FR-7.3); benchmark against known-friction test sites |
| Autonomous browsing on arbitrary third-party sites raises abuse/ToS concerns | Legal/reputational risk | robots.txt compliance, rate limiting, ToS requiring submitter has rights to test the site |
| LLM/agent cost scales faster than revenue per study | Poor unit economics | Step/time budgets per session, model-tiering, caching of repeated site analysis |
| Target sites with heavy anti-bot protection block agents | Failed/incomplete studies | Graceful degradation, partial results, clear "site blocked automated access" messaging |
| Persona generation produces stereotyped or biased personas | Low-quality/insensitive output, reputational risk | Human-reviewed persona templates, bias review in QA, user ability to edit any persona |
| Users over-trust synthetic research as a full replacement for real user research | Poor customer outcomes, churn if real-world results diverge | Clear product messaging positioning UseWorldview as a complement to, not full replacement for, real user research |
| Dynamic/JS-heavy sites are hard to navigate reliably | Incomplete exploration, broken sessions | Invest in robust headless-browser + vision-based interaction rather than DOM-only parsing |

---

## 19. Assumptions & Dependencies

**Assumptions**
- Target websites/web apps in V1 are publicly accessible without login.
- Customers are willing to have an autonomous agent programmatically interact with their live production or staging site.
- Underlying LLM/vision models are capable of reliable multi-step web navigation and reasoning at acceptable cost.

**Dependencies**
- Availability and reliability of chosen LLM/vision model provider(s).
- Headless browser automation infrastructure (e.g., Chromium-based automation) capable of scaling to concurrent sessions.
- Supabase for auth, database, and storage.
- Hosting/infrastructure capable of running many concurrent, potentially long-lived agent sessions.

---

## 20. Release Plan & Phasing

### Phase 1 — MVP (Internal / Design Partners)
- Single-page + limited multi-page exploration (up to ~5 pages).
- 1 research goal per study, templated goals only.
- Up to 3 personas per study, auto-generated with light editing.
- Overall dashboard + persona detail (no replay scrubbing yet).
- Manual QA on persona believability.

### Phase 2 — V1 Public Launch
- Full whole-app exploration (unbounded page discovery within step budget).
- Custom free-text research goals.
- Full persona editing/regeneration and manual persona authoring.
- Journey replay with scrubbing.
- Cross-persona insights and full recommendations engine.
- Light/dark theme, persisted preference.

### Phase 3 — Post-V1 (Candidates)
- Authenticated flow testing.
- Native mobile app testing.
- Scheduled/recurring studies.
- Public API.
- Team roles/permissions and enterprise admin.
- Before/after (A/B) comparison studies.

---

## 21. Open Questions

1. What is the pricing model for V1 — per study, per persona-session, or subscription with usage caps?
2. What is the maximum acceptable session step/time budget per persona before cost becomes prohibitive?
3. How do we handle target sites that actively block automated browsers (CAPTCHA, bot detection)?
4. Should users be able to specify "must-visit" pages/flows in addition to letting the agent discover organically?
5. What is the minimum/maximum number of personas allowed per study in V1?
6. How is "trust score" and other aggregate scores in Section 12.1 actually computed — what's the scoring methodology?
7. What legal/ToS mechanism confirms a user has the right to run automated testing against a submitted URL?

---

## 22. Glossary

| Term | Definition |
|---|---|
| **Persona / Worldview** | A synthetic identity with a complete set of demographic and psychographic attributes, motivations, and situational context that drives how an AI agent behaves on a website. |
| **Study** | A single research project: one research goal, one target URL, one set of deployed personas, and the resulting dashboard. |
| **Agent Session** | A single persona's autonomous run through the target site, from entry to task completion or abandonment. |
| **Cross-Persona Insight** | A pattern or statistic derived by aggregating findings across all personas in a study. |
| **Journey Replay** | A step-by-step visual playback of a persona's session, including actions, reactions, and outcome. |

---

## 23. Appendix: Recommendation Format Spec

Every recommendation surfaced in the dashboard (FR-16) must follow this structure:

```
Problem:              <what is broken or unclear, in one sentence>
Evidence:             <specific session events / persona quotes that demonstrate the problem>
Affected Users:       <which personas / segments experienced this, and how many (e.g., 6/10)>
Why It Matters:       <the downstream impact — trust, conversion, task completion, etc.>
Suggested Improvement:<concrete, specific fix the team can act on>
```

**Example:**

```
Problem:              Pricing page does not clearly indicate what is included at each tier.
Evidence:             4 of 5 personas paused on the pricing page for 30+ seconds and
                       re-read it before either leaving or opening a competitor's site
                       in a new context.
Affected Users:       Price-sensitive personas (4/10 across study); especially first-time,
                       non-technical visitors.
Why It Matters:       Unclear pricing was cited as the top reason for signup abandonment
                       in this study, ahead of trust or usability concerns.
Suggested Improvement:Add a feature-comparison table under each pricing tier and surface
                       an inline FAQ addressing the most common pricing question observed.
```

---

*End of Document — UseWorldview PRD v1.0*