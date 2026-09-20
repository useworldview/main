'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import {
  ArrowRight, Zap, Clock, Users, Brain, Search, Target,
  Shield, Eye, BarChart3, Globe, Lightbulb, MessageSquare,
  ChevronRight, Sparkles, MousePointerClick, Route, FileText,
  Menu, X, CheckCircle2, Play, Pause, AlertTriangle, ArrowUpRight,
  TrendingDown, Check, Layers, Compass, Terminal, ShieldCheck,
  Activity, Star
} from 'lucide-react';

// ─── Navbar ───
function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav
      id="main-nav"
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-white/95 backdrop-blur-md shadow-sm border-b border-surface-200 py-3'
          : 'bg-transparent py-5'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl gradient-bg flex items-center justify-center shadow-sm group-hover:shadow-glow transition-all">
            <Eye className="w-5 h-5 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-lg leading-none text-surface-900">
              Use<span className="gradient-text">Worldview</span>
            </span>
            <span className="text-[10px] font-mono tracking-widest text-surface-400 uppercase mt-0.5 font-semibold">
              Synthetic UX Studio
            </span>
          </div>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          <a href="#interactive-demo" className="text-sm font-medium text-surface-600 hover:text-brand-600 transition-colors">
            Live Simulation
          </a>
          <a href="#comparison" className="text-sm font-medium text-surface-600 hover:text-brand-600 transition-colors">
            Comparison
          </a>
          <a href="#how-it-works" className="text-sm font-medium text-surface-600 hover:text-brand-600 transition-colors">
            How It Works
          </a>
          <a href="#blueprints" className="text-sm font-medium text-surface-600 hover:text-brand-600 transition-colors">
            Study Blueprints
          </a>
        </div>

        <div className="hidden md:flex items-center gap-3">
          <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 border border-brand-200 text-[11px] font-mono font-medium text-brand-700">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            v2.4 Cognitive Engine
          </div>
          <Link href="/sign-in" className="btn-ghost text-surface-700 hover:text-surface-900">
            Sign in
          </Link>
          <Link href="/sign-up" className="btn-primary" id="navbar-get-started-btn">
            Deploy Personas
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Mobile menu button */}
        <button
          className="md:hidden p-2 rounded-lg hover:bg-surface-100 transition-colors text-surface-700"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle Navigation Menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden glass mt-2 mx-4 rounded-2xl p-4 animate-slide-down shadow-elevated border border-surface-200">
          <div className="flex flex-col gap-2">
            <a href="#interactive-demo" className="btn-ghost justify-start" onClick={() => setMobileOpen(false)}>Live Simulation</a>
            <a href="#comparison" className="btn-ghost justify-start" onClick={() => setMobileOpen(false)}>Comparison</a>
            <a href="#how-it-works" className="btn-ghost justify-start" onClick={() => setMobileOpen(false)}>How It Works</a>
            <a href="#blueprints" className="btn-ghost justify-start" onClick={() => setMobileOpen(false)}>Study Blueprints</a>
            <hr className="border-surface-200 my-1" />
            <Link href="/sign-in" className="btn-ghost justify-start">Sign in</Link>
            <Link href="/sign-up" className="btn-primary justify-center">Deploy Personas <ArrowRight className="w-4 h-4" /></Link>
          </div>
        </div>
      )}
    </nav>
  );
}

// ─── Hero Section with Interactive Live Telemetry ───
const SIMULATED_PERSONAS = [
  {
    id: 'elena',
    name: 'Elena Rostova',
    role: 'VP of Procurement (Enterprise)',
    age: 38,
    avatarColor: 'from-purple-500 to-indigo-600',
    traits: ['Patience: 3/10', 'Budget Skepticism: 9/10', 'Security Obsessed'],
    currentAction: 'Hovering #annual-vs-monthly-toggle',
    emotion: 'Skeptical',
    sentimentScore: 42,
    confidence: '78%',
    innerMonologue: '"Where is the SOC-2 compliance mention? The pricing says $49/mo, but is SSO locked behind the custom Enterprise tier? I refuse to book a 30-minute sales call just to get base pricing."',
    detectedFriction: 'SSO pricing opacity creates immediate high-intent drop-off risk.',
    recommendation: 'Surface enterprise security badges & clarify SSO tier inclusion inline.',
    simulatedUrl: 'app.example.io/pricing',
    cursorPos: { x: '68%', y: '48%' },
  },
  {
    id: 'devon',
    name: 'Devon Vance',
    role: 'Senior Fullstack Architect',
    age: 29,
    avatarColor: 'from-blue-500 to-cyan-600',
    traits: ['Patience: 8/10', 'Tech Savviness: 10/10', 'API-First'],
    currentAction: 'Inspecting #docs-code-snippet',
    emotion: 'Impressed',
    sentimentScore: 88,
    confidence: '94%',
    innerMonologue: '"Quick start snippet is clean. Copy-pasted into terminal, executed with 0 errors. Let me check the rate limit documentation before committing the webhook endpoints."',
    detectedFriction: 'Zero critical blockers. Dwell time under 8 seconds to first API call.',
    recommendation: 'Add direct "Clone in StackBlitz" playground button above the code block.',
    simulatedUrl: 'docs.example.io/quickstart',
    cursorPos: { x: '42%', y: '36%' },
  },
  {
    id: 'priya',
    name: 'Priya Sharma',
    role: 'Growth Marketing Lead',
    age: 33,
    avatarColor: 'from-amber-500 to-rose-600',
    traits: ['Patience: 4/10', 'Visual Thinker', 'Mobile First'],
    currentAction: 'Stuck on #step-2-integration-modal',
    emotion: 'Frustrated',
    sentimentScore: 28,
    confidence: '35%',
    innerMonologue: '"Wait, it asked me to connect Slack, but the modal doesn\'t show which permissions it requires. Can I skip this step? The skip button is a low-contrast grey link below the fold."',
    detectedFriction: 'Mandatory OAuth step without clear scope triggers 65% bounce rate.',
    recommendation: 'Elevate "Skip for now" to secondary button and add permission preview.',
    simulatedUrl: 'app.example.io/onboarding/step-2',
    cursorPos: { x: '52%', y: '64%' },
  }
];

function Hero() {
  const [selectedPersona, setSelectedPersona] = useState(SIMULATED_PERSONAS[0]);

  return (
    <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 overflow-hidden gradient-bg-subtle" id="interactive-demo">
      {/* Background ambient lighting */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[700px] rounded-full bg-brand-200/20 blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 -right-20 w-[400px] h-[400px] rounded-full bg-indigo-200/20 blur-[90px] pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-6">
        <div className="max-w-4xl mx-auto text-center mb-14">
          {/* Eyebrow badge (Crisp, light, high-contrast) */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-50 border border-brand-200 text-brand-700 text-xs md:text-sm font-semibold mb-6 shadow-sm">
            <Sparkles className="w-4 h-4 text-brand-600" />
            <span>Autonomous Synthetic UX Research</span>
            <span className="text-brand-300">•</span>
            <span className="text-surface-600 font-normal">10x Deeper Than Analytics</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight text-surface-900 leading-[1.08] mb-6">
            See your product through{' '}
            <span className="gradient-text">real human eyes</span>
            <br className="hidden sm:inline" />
            {' '}before users churn.
          </h1>

          {/* Subtitle */}
          <p className="text-lg md:text-xl text-surface-600 max-w-3xl mx-auto mb-10 leading-relaxed">
            Give UseWorldview a URL and a goal. Our autonomous psychographic personas explore your entire app, face real friction, and report traceable evidence with video replays in minutes.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/sign-up" className="btn-primary text-base px-8 py-4 shadow-elevated group" id="hero-start-study-btn">
              <span>Deploy Your First Study</span>
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <a href="#how-it-works" className="btn-secondary text-base px-7 py-4">
              <Compass className="w-4 h-4 text-brand-600" />
              Explore Engine Architecture
            </a>
          </div>

          <div className="mt-8 flex items-center justify-center gap-6 text-xs text-surface-500 font-medium">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" /> No code install required
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Headless browser replays
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" /> 100% reproducible
            </span>
          </div>
        </div>

        {/* ─── Interactive Live Persona Telemetry Frame ─── */}
        <div className="max-w-5xl mx-auto">
          {/* Persona selector tabs */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4 px-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-surface-600 uppercase tracking-wider">
              <Activity className="w-4 h-4 text-brand-600 animate-pulse" />
              <span>Interactive Telemetry Preview:</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {SIMULATED_PERSONAS.map(persona => (
                <button
                  key={persona.id}
                  onClick={() => setSelectedPersona(persona)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                    selectedPersona.id === persona.id
                      ? 'bg-surface-900 text-white shadow-md ring-2 ring-brand-400/50'
                      : 'bg-white text-surface-700 hover:bg-surface-100 border border-surface-200'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full bg-gradient-to-r ${persona.avatarColor}`} />
                  <span>{persona.name}</span>
                  <span className="opacity-70 text-[10px]">({persona.emotion})</span>
                </button>
              ))}
            </div>
          </div>

          {/* Studio Container */}
          <div className="browser-frame bg-white border border-surface-200 shadow-elevated">
            {/* Window Chrome */}
            <div className="flex items-center justify-between px-4 py-3 bg-surface-100 border-b border-surface-200">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-rose-500" />
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                <div className="w-3 h-3 rounded-full bg-emerald-500" />
                <div className="ml-3 hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-md bg-white text-xs font-mono text-surface-600 border border-surface-200 w-72">
                  <Globe className="w-3 h-3 text-brand-500" />
                  <span className="truncate">{selectedPersona.simulatedUrl}</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-100 border border-emerald-300 text-emerald-800 text-[11px] font-mono font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                  LIVE AUTONOMOUS SESSION
                </span>
                <span className="text-xs font-mono text-surface-400 hidden sm:inline">1920x1080 Headless</span>
              </div>
            </div>

            {/* Studio Body: Viewport + Cognitive Telemetry */}
            <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-surface-200">
              {/* Left Viewport (7 cols) */}
              <div className="lg:col-span-7 p-6 relative min-h-[320px] sm:min-h-[380px] bg-gradient-to-br from-surface-0 to-surface-50 flex flex-col justify-between overflow-hidden">
                {/* Simulated web app mockup in background */}
                <div className="rounded-xl border border-surface-200 p-4 bg-white shadow-sm opacity-95">
                  <div className="flex items-center justify-between border-b border-surface-200 pb-3 mb-4">
                    <div className="w-24 h-4 bg-surface-200 rounded" />
                    <div className="flex gap-2">
                      <div className="w-14 h-3 bg-surface-200 rounded" />
                      <div className="w-14 h-3 bg-surface-200 rounded" />
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="h-6 w-3/4 bg-brand-100 rounded" />
                    <div className="h-3 w-1/2 bg-surface-200 rounded" />
                    <div className="grid grid-cols-3 gap-2 pt-2">
                      <div className="h-20 bg-surface-50 rounded-lg border border-surface-200 p-2">
                        <div className="h-3 w-12 bg-surface-300 rounded mb-2" />
                        <div className="h-4 w-8 bg-brand-300 rounded" />
                      </div>
                      <div className="h-20 bg-brand-50 rounded-lg border-2 border-brand-400 p-2 relative">
                        <div className="h-3 w-12 bg-brand-400 rounded mb-2" />
                        <div className="h-4 w-8 bg-brand-600 rounded" />
                        <div className="absolute top-1 right-1 w-2 h-2 rounded-full bg-brand-500" />
                      </div>
                      <div className="h-20 bg-surface-50 rounded-lg border border-surface-200 p-2">
                        <div className="h-3 w-12 bg-surface-300 rounded mb-2" />
                        <div className="h-4 w-8 bg-surface-300 rounded" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Simulated Floating Pointer with coordinate tracker */}
                <div
                  className="absolute pointer-events-none transition-all duration-700 ease-out z-20"
                  style={{ left: selectedPersona.cursorPos.x, top: selectedPersona.cursorPos.y }}
                >
                  <div className="relative">
                    <MousePointerClick className="w-6 h-6 text-brand-600 drop-shadow-md animate-bounce" />
                    <span className="absolute left-5 -top-1 px-2 py-0.5 rounded bg-surface-900 text-white text-[10px] font-mono whitespace-nowrap shadow-lg">
                      {selectedPersona.currentAction}
                    </span>
                  </div>
                </div>

                {/* Bottom telemetry overlay */}
                <div className="relative z-10 mt-4 flex items-center justify-between text-xs bg-white/90 backdrop-blur-md px-3 py-2 rounded-lg border border-surface-200 shadow-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-surface-500 font-mono">Dwell Time:</span>
                    <span className="font-mono font-bold text-surface-800">00:14.2s</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-surface-500 font-mono">Confidence:</span>
                    <span className="font-mono font-bold text-brand-600">{selectedPersona.confidence}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-surface-500 font-mono">Status:</span>
                    <span className="badge badge-brand text-[10px]">Processing DOM</span>
                  </div>
                </div>
              </div>

              {/* Right Cognitive Telemetry Feed (5 cols) */}
              <div className="lg:col-span-5 p-6 bg-white flex flex-col justify-between">
                <div>
                  {/* Persona Identity Header */}
                  <div className="flex items-center justify-between mb-4 pb-3 border-b border-surface-200">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full bg-gradient-to-tr ${selectedPersona.avatarColor} flex items-center justify-center text-white font-bold text-sm shadow-sm`}>
                        {selectedPersona.name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <h4 className="font-bold text-sm text-surface-900">{selectedPersona.name}</h4>
                        <p className="text-xs text-surface-500">{selectedPersona.role}</p>
                      </div>
                    </div>
                    <span className={`badge ${
                      selectedPersona.sentimentScore > 70 ? 'badge-success' : selectedPersona.sentimentScore > 40 ? 'badge-warning' : 'badge-error'
                    }`}>
                      {selectedPersona.emotion}
                    </span>
                  </div>

                  {/* Psychographic Traits */}
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {selectedPersona.traits.map(trait => (
                      <span key={trait} className="px-2 py-0.5 rounded bg-surface-100 text-[11px] font-mono text-surface-600 border border-surface-200">
                        {trait}
                      </span>
                    ))}
                  </div>

                  {/* Inner Monologue Stream */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-semibold text-surface-700 flex items-center gap-1.5">
                        <Brain className="w-3.5 h-3.5 text-brand-500" />
                        Synchronized Inner Monologue
                      </span>
                      <span className="text-[10px] font-mono text-surface-400">Step #4 / 12</span>
                    </div>
                    <div className="p-3.5 rounded-xl bg-surface-50 border border-surface-200 text-xs text-surface-700 italic leading-relaxed">
                      {selectedPersona.innerMonologue}
                    </div>
                  </div>

                  {/* Friction & Recommendation Card */}
                  <div className="p-3.5 rounded-xl bg-brand-50 border border-brand-200">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-brand-800 mb-1">
                      <Target className="w-3.5 h-3.5 text-brand-600" />
                      Automated Fix Specification
                    </div>
                    <p className="text-xs text-surface-700 mb-2 leading-snug">
                      {selectedPersona.recommendation}
                    </p>
                    <div className="flex items-center justify-between text-[11px] font-mono text-surface-500 pt-1 border-t border-brand-200">
                      <span>Impact: <strong className="text-brand-700">High</strong></span>
                      <span>Confidence: <strong className="text-emerald-600">92%</strong></span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-surface-200 flex items-center justify-between">
                  <span className="text-xs text-surface-400 font-mono">Trace ID: #wv-sim-8842</span>
                  <Link href="/sign-up" className="text-xs font-semibold text-brand-600 hover:underline flex items-center gap-1">
                    Run on your site <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── The Core Contrast: Analytics vs Generic AI vs UseWorldview ───
function ComparisonSection() {
  return (
    <section className="py-20 md:py-28 bg-white border-t border-surface-200" id="comparison">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <p className="text-xs font-bold text-brand-600 uppercase tracking-wider mb-3">
            The Fundamental Shift
          </p>
          <h2 className="text-3xl md:text-5xl font-extrabold text-surface-900 tracking-tight mb-4">
            Why Traditional Analytics & Surface AI Both Fall Short
          </h2>
          <p className="text-surface-600 text-base md:text-lg">
            Analytics shows you numbers without reasons. Surface AI scans only landing pages. UseWorldview deploys autonomous psychographic agents inside your whole product.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Analytics */}
          <div className="card p-7 flex flex-col justify-between border-surface-200">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-surface-100 flex items-center justify-center mb-5 text-surface-600">
                <BarChart3 className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-surface-900 mb-2">Standard Web Analytics</h3>
              <p className="text-xs font-mono text-surface-400 uppercase mb-4">Google Analytics, Mixpanel, PostHog</p>
              <ul className="space-y-3 text-sm text-surface-600">
                <li className="flex items-start gap-2">
                  <TrendingDown className="w-4 h-4 text-error shrink-0 mt-0.5" />
                  <span>Tells you <strong>where</strong> users drop off, never <strong>why</strong>.</span>
                </li>
                <li className="flex items-start gap-2">
                  <TrendingDown className="w-4 h-4 text-error shrink-0 mt-0.5" />
                  <span>Requires thousands of real users to get statistical significance.</span>
                </li>
                <li className="flex items-start gap-2">
                  <TrendingDown className="w-4 h-4 text-error shrink-0 mt-0.5" />
                  <span>Feedback arrives post-launch after churn damage is already done.</span>
                </li>
              </ul>
            </div>
            <div className="mt-8 pt-4 border-t border-surface-200 text-xs font-medium text-surface-400">
              Verdict: Blind to user reasoning
            </div>
          </div>

          {/* Card 2: Generic AI Scrapers */}
          <div className="card p-7 flex flex-col justify-between border-surface-200">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-amber-50 flex items-center justify-center mb-5 text-amber-600">
                <Brain className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-surface-900 mb-2">Shallow AI Scrapers</h3>
              <p className="text-xs font-mono text-surface-400 uppercase mb-4">Basic LLM Website Checklists</p>
              <ul className="space-y-3 text-sm text-surface-600">
                <li className="flex items-start gap-2">
                  <TrendingDown className="w-4 h-4 text-warning shrink-0 mt-0.5" />
                  <span>Only scans static HTML of public landing pages.</span>
                </li>
                <li className="flex items-start gap-2">
                  <TrendingDown className="w-4 h-4 text-warning shrink-0 mt-0.5" />
                  <span>Cannot fill forms, authenticate, or click multi-step flows.</span>
                </li>
                <li className="flex items-start gap-2">
                  <TrendingDown className="w-4 h-4 text-warning shrink-0 mt-0.5" />
                  <span>Generic advice like &quot;Make CTA button bigger&quot;.</span>
                </li>
              </ul>
            </div>
            <div className="mt-8 pt-4 border-t border-surface-200 text-xs font-medium text-surface-400">
              Verdict: Superficial & non-actionable
            </div>
          </div>

          {/* Card 3: UseWorldview */}
          <div className="spotlight-card p-7 flex flex-col justify-between border-2 border-brand-500 shadow-glow relative bg-gradient-to-b from-brand-50/60 to-white">
            <div className="absolute top-4 right-4">
              <span className="badge badge-brand text-[10px] font-bold">STATE OF THE ART</span>
            </div>
            <div>
              <div className="w-12 h-12 rounded-2xl gradient-bg flex items-center justify-center mb-5 text-white shadow-md">
                <Eye className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-surface-900 mb-2">UseWorldview Cognitive Engine</h3>
              <p className="text-xs font-mono text-brand-700 uppercase mb-4">Psychographic Synthetic Research</p>
              <ul className="space-y-3 text-sm text-surface-800 font-medium">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><strong>Deep Psychographic Profiles:</strong> Anxieties, tech fluency, and mental models.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><strong>Whole-App Autonomous Traversal:</strong> Fills forms, logs in, clicks through multi-step journeys.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><strong>Traceable Video Replays:</strong> Screen recording, DOM selector logs, and emotional sparklines.</span>
                </li>
              </ul>
            </div>
            <div className="mt-8 pt-4 border-t border-brand-200 flex items-center justify-between text-xs font-bold text-brand-700">
              <span>Turnaround: 3 to 5 minutes</span>
              <span>100% Traceable</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── The 4-Stage Autonomous Engine ───
function HowItWorks() {
  const stages = [
    {
      step: '01',
      title: 'Synthesize Psychographic Matrix',
      desc: 'Define your research target or pick a blueprint. The system crafts realistic personas with diverse cognitive biases, patience thresholds, and domain expectations.',
      badge: 'Cognitive Modeling',
      icon: Users,
    },
    {
      step: '02',
      title: 'Autonomous Headless Traversal',
      desc: 'Playwright-backed AI agents load your live application. They scroll, search, fill forms, and make decisions based on their assigned mental models.',
      badge: 'Browser Execution',
      icon: Globe,
    },
    {
      step: '03',
      title: 'Hesitation & Friction Detection',
      desc: 'The engine monitors micro-dwell times, confusion loops, rage clicks, and emotional state transitions at every DOM interaction.',
      badge: 'Telemetry & Sentiment',
      icon: Activity,
    },
    {
      step: '04',
      title: 'Evidence & Prioritized Action Items',
      desc: 'Synthesizes cross-persona patterns into executive scorecards, session replay scrubbers, and copyable engineering tickets ranked by impact.',
      badge: 'Actionable Delivery',
      icon: Target,
    },
  ];

  return (
    <section className="py-20 md:py-28 bg-surface-50 border-t border-surface-200" id="how-it-works">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <p className="text-xs font-bold text-brand-600 uppercase tracking-wider mb-3">
            Autonomous Engine Architecture
          </p>
          <h2 className="text-3xl md:text-5xl font-extrabold text-surface-900 tracking-tight mb-4">
            How Synthetic Agents Test Your Product
          </h2>
          <p className="text-surface-600 text-base md:text-lg">
            From initial URL submission to fully analyzed, evidence-backed recommendations in four automated stages.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stages.map((stage) => (
            <div key={stage.step} className="card p-6 flex flex-col justify-between hover:shadow-card-hover transition-all">
              <div>
                <div className="flex items-center justify-between mb-6">
                  <span className="text-3xl font-black font-mono text-brand-400">{stage.step}</span>
                  <span className="badge badge-brand text-[10px]">{stage.badge}</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center text-brand-600 mb-4">
                  <stage.icon className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-surface-900 mb-2">{stage.title}</h3>
                <p className="text-xs text-surface-600 leading-relaxed">{stage.desc}</p>
              </div>
              <div className="mt-6 pt-3 border-t border-surface-200 text-[11px] font-mono text-surface-400">
                Autonomous pass
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Research Blueprint Explorer ───
const BLUEPRINTS = [
  {
    id: 'onboarding',
    title: 'Onboarding Drop-off Detective',
    goal: 'Identify the exact form field, modal, or step where first-time signups give up.',
    personaExample: 'Non-technical Business Owner (Patience: 3/10)',
    frictionFound: '4/5 personas paused on phone verification step before abandoning.',
    tags: ['Activation', 'Sign-up', 'High Priority'],
  },
  {
    id: 'pricing',
    title: 'Pricing Clarity & Hesitation',
    goal: 'Determine whether plan tiers, limits, and annual discounts are immediately understood.',
    personaExample: 'Enterprise Budget Approver (Cost-conscious)',
    frictionFound: 'Hidden add-on fees triggered distrust in 80% of exploratory sessions.',
    tags: ['Conversion', 'Revenue', 'Friction'],
  },
  {
    id: 'paywall',
    title: 'Checkout & Paywall Stress-Test',
    goal: 'Find confusing payment form validation errors and billing address friction.',
    personaExample: 'International Mobile Shopper (EUR Currency)',
    frictionFound: 'Zip code validation rejected non-US postal formats without error labels.',
    tags: ['Paywall', 'Checkout', 'Critical'],
  },
  {
    id: 'feature',
    title: 'New Feature Discoverability',
    goal: 'Test whether newly launched dashboard tools are found without guided tooltips.',
    personaExample: 'Power User (Keyboard shortcut oriented)',
    frictionFound: 'Feature buried 3 levels deep in settings sidebar navigation.',
    tags: ['Adoption', 'Navigation', 'UX Polish'],
  },
];

function BlueprintExplorer() {
  const [activeBlueprint, setActiveBlueprint] = useState(BLUEPRINTS[0]);

  return (
    <section className="py-20 md:py-28 bg-white border-t border-surface-200" id="blueprints">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <p className="text-xs font-bold text-brand-600 uppercase tracking-wider mb-3">
            Pre-Engineered Blueprints
          </p>
          <h2 className="text-3xl md:text-5xl font-extrabold text-surface-900 tracking-tight mb-4">
            Tested Scenarios Built for Product Teams
          </h2>
          <p className="text-surface-600 text-base md:text-lg">
            Deploy turnkey research blueprints tailored for product managers, growth designers, and founders.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Blueprint Selector list */}
          <div className="lg:col-span-5 space-y-3">
            {BLUEPRINTS.map(bp => (
              <div
                key={bp.id}
                onClick={() => setActiveBlueprint(bp)}
                className={`p-5 rounded-2xl cursor-pointer transition-all border ${
                  activeBlueprint.id === bp.id
                    ? 'bg-brand-50 border-brand-300 shadow-sm translate-x-1'
                    : 'bg-white border-surface-200 hover:border-brand-200 hover:bg-surface-50'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-bold text-sm text-surface-900">{bp.title}</h4>
                  <ChevronRight className={`w-4 h-4 transition-transform ${activeBlueprint.id === bp.id ? 'text-brand-600 translate-x-1' : 'text-surface-400'}`} />
                </div>
                <p className="text-xs text-surface-600 leading-relaxed mb-3">{bp.goal}</p>
                <div className="flex flex-wrap gap-1.5">
                  {bp.tags.map(t => (
                    <span key={t} className="px-2 py-0.5 rounded bg-surface-100 text-[10px] font-mono text-surface-700 border border-surface-200">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Blueprint Live Output Preview */}
          <div className="lg:col-span-7 card p-8 border-surface-200 shadow-elevated bg-gradient-to-br from-white to-surface-50">
            <div className="flex items-center justify-between pb-4 mb-6 border-b border-surface-200">
              <div className="flex items-center gap-2">
                <Compass className="w-5 h-5 text-brand-600" />
                <span className="font-bold text-sm text-surface-900">Blueprint Simulation Output</span>
              </div>
              <span className="badge badge-brand text-xs">Turnaround ~3 min</span>
            </div>

            <div className="space-y-6">
              <div>
                <p className="text-xs font-mono uppercase text-surface-400 mb-1">Target Persona Assigned</p>
                <p className="text-sm font-semibold text-surface-800">{activeBlueprint.personaExample}</p>
              </div>

              <div>
                <p className="text-xs font-mono uppercase text-surface-400 mb-1">Core Evidence Uncovered</p>
                <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 leading-relaxed flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <span>{activeBlueprint.frictionFound}</span>
                </div>
              </div>

              <div>
                <p className="text-xs font-mono uppercase text-surface-400 mb-2">Deliverables Provided</p>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-lg bg-surface-50 border border-surface-200 flex items-center gap-2">
                    <Play className="w-3.5 h-3.5 text-brand-500" />
                    <span>Synchronized Screen Replay</span>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-50 border border-surface-200 flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5 text-brand-500" />
                    <span>Jira / Linear Spec Ticket</span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-surface-200 flex items-center justify-between">
                <span className="text-xs text-surface-500">Deploy this blueprint in 1 click</span>
                <Link href="/sign-up" className="btn-primary text-xs py-2 px-4">
                  Run Study Now
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Hard Benchmark Metrics & ROI ───
function BenchmarkSection() {
  const stats = [
    { value: '94%', label: 'Faster Recruitment', sub: 'Instant AI persona synthesis vs 2-week interview cycles' },
    { value: '$0.12', label: 'Average Session Cost', sub: 'Compute cost per study vs $150 incentive per user' },
    { value: '100%', label: 'Reproducible Replays', sub: 'Every click, DOM pause, and monologue is recorded' },
    { value: '< 5m', label: 'End-to-End Turnaround', sub: 'From URL submission to prioritized recommendations' },
  ];

  return (
    <section className="py-16 md:py-24 bg-surface-50 border-t border-surface-200">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map(s => (
            <div key={s.label} className="card p-6 text-center">
              <p className="text-3xl sm:text-4xl font-extrabold text-surface-900 font-mono gradient-text mb-1">{s.value}</p>
              <p className="text-sm font-bold text-surface-800 mb-1">{s.label}</p>
              <p className="text-xs text-surface-500 leading-relaxed">{s.sub}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── High Impact CTA Banner ───
function CTABanner() {
  return (
    <section className="py-20 md:py-28 relative overflow-hidden bg-white border-t border-surface-200">
      <div className="absolute inset-0 bg-gradient-to-r from-brand-50 via-indigo-50/50 to-transparent pointer-events-none" />
      <div className="max-w-5xl mx-auto px-6 relative z-10 text-center">
        <div className="w-16 h-16 rounded-3xl gradient-bg flex items-center justify-center mx-auto mb-8 shadow-glow">
          <Eye className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-3xl sm:text-5xl font-extrabold text-surface-900 tracking-tight mb-6">
          Ready to experience your product through real human eyes?
        </h2>
        <p className="text-surface-600 text-lg max-w-2xl mx-auto mb-10">
          Enter your live URL, pick your target audience, and watch autonomous AI personas reveal every UX blind spot in minutes.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href="/sign-up" className="btn-primary text-base px-9 py-4 shadow-elevated" id="cta-banner-start-btn">
            Start Free Synthetic Study
            <ArrowRight className="w-5 h-5" />
          </Link>
          <Link href="/sign-in" className="btn-secondary text-base px-8 py-4">
            Sign In to Dashboard
          </Link>
        </div>
        <p className="mt-6 text-xs text-surface-400">
          No credit card required • Instant setup • 100% cloud executed
        </p>
      </div>
    </section>
  );
}

// ─── Footer ───
function Footer() {
  return (
    <footer className="py-12 bg-surface-50 border-t border-surface-200 text-xs text-surface-500">
      <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-lg gradient-bg flex items-center justify-center shadow-sm">
            <Eye className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-bold text-surface-800">
            UseWorldview
          </span>
          <span className="text-surface-400">© {new Date().getFullYear()} All rights reserved.</span>
        </div>

        <div className="flex items-center gap-6 font-medium">
          <a href="#interactive-demo" className="hover:text-surface-800 transition-colors">Simulation</a>
          <a href="#comparison" className="hover:text-surface-800 transition-colors">Comparison</a>
          <a href="#how-it-works" className="hover:text-surface-800 transition-colors">How It Works</a>
          <a href="#blueprints" className="hover:text-surface-800 transition-colors">Blueprints</a>
          <Link href="/sign-in" className="hover:text-surface-800 transition-colors">Dashboard</Link>
        </div>
      </div>
    </footer>
  );
}

// ─── Main Landing Page ───
export default function LandingPage() {
  return (
    <main className="min-h-screen bg-surface-50 text-surface-900">
      <Navbar />
      <Hero />
      <ComparisonSection />
      <HowItWorks />
      <BlueprintExplorer />
      <BenchmarkSection />
      <CTABanner />
      <Footer />
    </main>
  );
}
