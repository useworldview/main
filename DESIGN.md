# Design System & Visual Identity — UseWorldview

<!-- impeccable:design-schema 1 -->

## Design Direction: Cognitive Intelligence Studio
UseWorldview is an AI-powered synthetic user research platform for product teams. The visual language conveys high analytical rigor, deep empathy for human psychology, and state-of-the-art autonomous intelligence.

## Modes
- **Persuade** (Marketing & Landing): Atmospheric, visionary, high-conversion, interactive live simulations demonstrating real cognitive reasoning.
- **Operate** (Dashboard, Study Wizard, Results Showcase, Journey Replay): High-density scanability, studio-grade replay scrubber, instant executive synthesis, and evidence-first telemetry.

---

## 1. Color System

### Primary & Brand (Electric Violet & Indigo)
- `--color-brand-50`: `#f5f3ff` (Soft lavender tint)
- `--color-brand-100`: `#ede9fe`
- `--color-brand-200`: `#ddd6fe`
- `--color-brand-500`: `#8b5cf6` (Electric Violet core)
- `--color-brand-600`: `#7c3aed` (Interactive primary hover)
- `--color-brand-700`: `#6d28d9`
- `--color-brand-900`: `#4c1d95`
- `--color-brand-950`: `#2e1065` (Midnight abyss)

### Accent & Telemetry
- **Emerald** (`#10b981`, `#059669`): Task completed, positive sentiment, goal reached.
- **Amber / Gold** (`#f59e0b`, `#d97706`): Cognitive friction, hesitation, pause warning.
- **Rose / Crimson** (`#ef4444`, `#dc2626`): Rage click, dead-end roadblock, severe UX confusion.
- **Cyan / Sky** (`#06b6d4`, `#0284c7`): Autonomous agent step, DOM inspection, navigation.

### Surfaces (Dual-Palette Harmony)
- **Light Theme**:
  - Base: `#fafafa` to `#f8fafc`
  - Cards: `#ffffff` with subtle border `rgba(15, 23, 42, 0.08)`
  - Frosted Glass: `rgba(255, 255, 255, 0.75)` with `backdrop-filter: blur(16px)`
- **Dark Theme (Obsidian & Slate)**:
  - Base: `#090d16` (Deep interstellar obsidian)
  - Elevated Cards: `#0f172a` and `#141d33`
  - Frosted Glass: `rgba(15, 23, 42, 0.75)` with `backdrop-filter: blur(16px)`
  - Border Accents: `rgba(255, 255, 255, 0.07)` with subtle violet edge sheen

---

## 2. Typography
- **Primary Sans**: Inter (`font-sans`), with tight negative letter-spacing on display headings (`tracking-tight` / `-0.025em`).
- **Telemetry & Monospace**: JetBrains Mono (`font-mono`) for coordinates, session timestamps, and cognitive state tags.
- **Hierarchy**:
  - Display Hero: `4.5rem` / `72px`, weight 800
  - Section Headings: `2.25rem` / `36px`, weight 700
  - Card Titles: `1.125rem` / `18px`, weight 600
  - Body Text: `0.9375rem` / `15px`, line-height 1.6
  - Telemetry & Micro-Labels: `0.75rem` / `12px`, uppercase, tracking-wider

---

## 3. Depth, Borders & Glassmorphism
- **Glass Dock**: `background: rgba(var(--surface-color), 0.75); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.1);`
- **Spotlight Cards**: Dynamic gradient borders that illuminate softly on hover (`border-color: rgba(139, 92, 246, 0.4)`).
- **Shadow Scale**:
  - `shadow-sm`: Crisp 1px ambient rim
  - `shadow-card`: `0 4px 20px -2px rgba(0, 0, 0, 0.05)`
  - `shadow-glow`: `0 0 30px rgba(139, 92, 246, 0.25)`

---

## 4. Key Component Blueprints
1. **Live Persona Telemetry Simulation**: Interactive widget rendering live cursor movements, emotional trajectory waves, and synchronized inner-monologue feed.
2. **Friction Heatmap Card**: Displays UX drop-off hotspots with severity badges, affected persona avatars, and exact DOM target selectors.
3. **Studio Replay Scrubber**: Browser chrome frame with play/pause, scrub slider, playback speed selector (0.5x, 1x, 2x), and step annotations.
