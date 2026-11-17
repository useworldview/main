# UseWorldview — Frontend Web Studio

<div align="center">

<br />

### **Next.js 16 Web Studio for Synthetic User Research**

*Interactive dashboard, multi-step study wizard, psychographic persona explorer, and frame-by-frame journey replay scrubber.*

<br />

[![Next.js](https://img.shields.io/badge/Next.js-16_App_Router-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Supabase](https://img.shields.io/badge/Supabase-SSR_Auth_%7C_Realtime-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![TanStack Query](https://img.shields.io/badge/TanStack_Query-v5-FF4154?style=for-the-badge&logo=react-query&logoColor=white)](https://tanstack.com/)

<br />

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Tech Stack](#-tech-stack)
- [Key Architectural Principles](#-key-architectural-principles)
- [Application Routes & Features](#-application-routes--features)
- [Directory Structure](#-directory-structure)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
  - [Development Server](#development-server)
  - [Production Build](#production-build)
- [Supabase Integration & Realtime](#-supabase-integration--realtime)
- [Design System & Theming](#-design-system--theming)
- [License](#-license)

---

## 🌟 Overview

The **UseWorldview Frontend** is the user interface and analytics dashboard for the UseWorldview platform. Built using Next.js 16 (App Router) and React 19, it provides an intuitive, high-density interface for product managers, designers, and engineers to:

1. **Configure & Launch Studies**: Define research goals (conversion, navigation, pricing perception) and submit public URLs via a 5-step guided wizard.
2. **Review & Customize AI Personas**: Inspect auto-generated target audiences and fine-tune psychographic worldview parameters.
3. **Monitor Live Deployments**: Watch browser agent execution progress in real-time via Supabase Realtime channels.
4. **Scrub Synthetic User Journeys**: Step through captured sessions with visual screenshots, emotional states, and DOM interaction markers.
5. **Act on Prioritized Recommendations**: Access 5-part structured findings (`Problem → Evidence → Affected Users → Why It Matters → Suggested Fix`).

---

## 🛠 Tech Stack

| Layer | Library / Tool | Description |
|---|---|---|
| **Framework** | [Next.js 16](https://nextjs.org/) | Modern App Router, Server/Client Components, Route Handlers |
| **UI Runtime** | [React 19](https://react.dev/) | React Server Components & Actions |
| **Styling** | [Tailwind CSS v4](https://tailwindcss.com/) | Native CSS variables, modern utility cascade |
| **Icons** | [Lucide React](https://lucide.dev/) | Consistent, accessible iconography |
| **Charts & Telemetry** | [Recharts](https://recharts.org/) | Emotional trajectory graphs and conversion drop-off visualizations |
| **Auth & Data** | [`@supabase/ssr`](https://supabase.com/docs/guides/auth/server-side/nextjs) | Cookie-based session management and browser singleton |
| **Server State** | [TanStack Query v5](https://tanstack.com/query) | Async query orchestration, caching, and mutation handling |
| **Forms & Validation** | React Hook Form + [Zod](https://zod.dev/) | Type-safe form validation for study wizard and persona editing |
| **Theming** | [`next-themes`](https://github.com/pacocoursey/next-themes) | Light-first with dark mode support (Obsidian Slate) |

---

## 🏛 Key Architectural Principles

### "Thin API, Fat Supabase"
In alignment with the core system architecture:
- **Direct Supabase Queries**: The frontend queries Supabase directly for reading studies, personas, sessions, events, findings, and recommendations. All read access is secured via PostgreSQL Row-Level Security (RLS).
- **Direct Supabase Mutations**: Non-AI mutations (e.g., editing persona names, marking recommendations as "useful", saving theme preferences) write directly to Supabase.
- **Dedicated Orchestration API**: The frontend only calls the FastAPI backend via [`lib/api.ts`](lib/api.ts) for compute-heavy AI operations:
  - `POST /api/studies` (Site ingestion & audience detection)
  - `POST /api/studies/:id/personas/generate` (Worldview persona creation)
  - `POST /api/personas/:id/regenerate` (Single persona regeneration)
  - `POST /api/studies/:id/deploy` (Launching Playwright agent jobs)
  - `POST /api/studies/:id/cancel` (Aborting active study runs)
  - `POST /api/studies/:id/retry-failed-sessions` (Re-running failed runs)

---

## 📱 Application Routes & Features

```
app/
├── (marketing)/
│   └── page.tsx                         # Landing page with interactive cognitive telemetry demo
├── (auth)/
│   ├── sign-in/page.tsx                 # Supabase email/password & OAuth sign-in
│   ├── sign-up/page.tsx                 # New user registration
│   └── auth/callback/route.ts           # OAuth redirect handler
├── (app)/
│   ├── layout.tsx                       # Protected shell: navigation bar, user menu, theme switcher
│   ├── dashboard/page.tsx               # Active and completed studies, key statistics
│   ├── studies/
│   │   ├── new/page.tsx                 # 5-step guided study creation wizard
│   │   └── [studyId]/
│   │       ├── page.tsx                 # Study overview, executive summary, pattern cards
│   │       ├── personas/[personaId]/
│   │       │   ├── page.tsx             # Persona psychographic profile & individual findings
│   │       │   └── replay/page.tsx      # Video-like journey replay scrubber with inner-monologue
│   │       └── recommendations/page.tsx # Prioritized 5-part UX recommendations
│   └── settings/page.tsx                # User profile and UI preferences
```

### Key UI Capabilities
1. **Interactive Cognitive Telemetry**: Landing page features an interactive simulator displaying live cursor coordinates, emotional trajectory waveforms, and inner-monologue feed.
2. **5-Stage Creation Wizard**:
   - Step 1: Research Goal selection (Templated or Custom).
   - Step 2: Target URL submission and validation.
   - Step 3: Audience Segment review and editing.
   - Step 4: AI Persona Worldview generation & customization.
   - Step 5: Agent deployment confirmation.
3. **Studio Journey Replay Scrubber**:
   - Scrub forward and backward across browsing steps.
   - Inspect screenshot captures alongside exact DOM selectors.
   - View the persona's inner monologue, hesitation duration, and emotional state (`confused`, `suspicious`, `excited`).
4. **Actionable Recommendations Table**: Filter by severity, affected personas, and category.

---

## 📂 Directory Structure

```
frontend/
├── app/                           # App Router routes & layouts
│   ├── (marketing)/               # Public landing pages
│   ├── (auth)/                    # Authentication pages
│   ├── (app)/                     # Protected dashboard views
│   ├── globals.css                # Design system styling & CSS tokens
│   ├── layout.tsx                 # Root HTML shell
│   └── providers.tsx              # React Query & Theme providers
├── lib/
│   ├── supabase/
│   │   ├── client.ts              # Browser Supabase client
│   │   └── server.ts              # Server-side Supabase client (cookies)
│   ├── analytics.ts               # Product analytics logger
│   ├── api.ts                     # Type-safe client for backend endpoints
│   ├── types.ts                   # Supabase database TypeScript definitions
│   └── utils.ts                   # Class merging (`cn`) & formatting helpers
├── public/                        # Static assets (SVGs, favicon)
├── middleware.ts                  # Session validation & route protection
├── package.json                   # Node package dependencies
├── tsconfig.json                  # TypeScript compiler options
└── next.config.ts                 # Next.js runtime configuration
```

---

## 🚀 Getting Started

### Prerequisites
- **Node.js**: `v20.10.0` or later
- **npm** (or `pnpm` / `bun`)
- Running **Supabase** instance (Cloud or Local)

---

### Installation

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install
```

---

### Environment Configuration

Create a `.env.local` file in the `frontend` root:

```bash
cp .env.example .env.local
```

Fill in the required variables:

```ini
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here

# Backend FastAPI Service URL
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000
```

---

### Development Server

Start the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

### Production Build

```bash
# Type check and build optimized bundle
npm run build

# Start production server
npm run start
```

---

## ⚡ Supabase Integration & Realtime

The frontend uses `@supabase/ssr` to securely maintain authentication tokens within `HttpOnly` cookies across Next.js Server Components and Client Components.

When a study is deployed, the study detail view subscribes to PostgreSQL changes:

```typescript
const channel = supabase
  .channel('study-agent-updates')
  .on(
    'postgres_changes',
    {
      event: 'UPDATE',
      schema: 'public',
      table: 'agent_sessions',
      filter: `study_id=eq.${studyId}`,
    },
    (payload) => {
      queryClient.invalidateQueries({ queryKey: ['study', studyId] });
    }
  )
  .subscribe();
```

---

## 🎨 Design System & Theming

The interface follows the **Cognitive Intelligence Studio** visual language defined in [`DESIGN.md`](../DESIGN.md):
- **Primary Color**: Electric Violet (`#8b5cf6` / `#7c3aed`)
- **Telemetry Accents**:
  - Emerald (`#10b981`): Success, goal reached, confidence
  - Amber (`#f59e0b`): Cognitive friction, hesitation
  - Rose (`#ef4444`): Frustration, rage-click, abandonment
  - Sky (`#0284c7`): Autonomous DOM perception step
- **Dual Surface Harmony**:
  - Light theme (clean SaaS aesthetic, default)
  - Obsidian dark theme (`#090d16` base with slate cards)

---

## 📄 License

This frontend package is licensed under the [MIT License](../LICENSE).
