'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import {
  ArrowRight, Zap, Clock, Users, Brain, Search, Target,
  Shield, Eye, BarChart3, Globe, Lightbulb, MessageSquare,
  ChevronRight, Sparkles, MousePointerClick, Route, FileText,
  Menu, X
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
          ? 'glass shadow-md py-3'
          : 'bg-transparent py-5'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-xl gradient-bg flex items-center justify-center shadow-md group-hover:shadow-lg transition-shadow">
            <Eye className="w-4.5 h-4.5 text-white" />
          </div>
          <span className="font-bold text-lg text-surface-800">
            Use<span className="gradient-text">Worldview</span>
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8">
          <a href="#how-it-works" className="text-sm font-medium text-surface-500 hover:text-surface-800 transition-colors">
            How it works
          </a>
          <a href="#who-its-for" className="text-sm font-medium text-surface-500 hover:text-surface-800 transition-colors">
            Who it&apos;s for
          </a>
          <a href="#features" className="text-sm font-medium text-surface-500 hover:text-surface-800 transition-colors">
            Features
          </a>
        </div>

        <div className="hidden md:flex items-center gap-3">
          <Link href="/sign-in" className="btn-ghost">
            Sign in
          </Link>
          <Link href="/sign-up" className="btn-primary">
            Get Started
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Mobile menu button */}
        <button
          className="md:hidden p-2 rounded-lg hover:bg-surface-100 transition-colors"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden glass mt-2 mx-4 rounded-2xl p-4 animate-slide-down shadow-elevated">
          <div className="flex flex-col gap-2">
            <a href="#how-it-works" className="btn-ghost justify-start" onClick={() => setMobileOpen(false)}>How it works</a>
            <a href="#who-its-for" className="btn-ghost justify-start" onClick={() => setMobileOpen(false)}>Who it&apos;s for</a>
            <a href="#features" className="btn-ghost justify-start" onClick={() => setMobileOpen(false)}>Features</a>
            <hr className="border-surface-200 my-1" />
            <Link href="/sign-in" className="btn-ghost justify-start">Sign in</Link>
            <Link href="/sign-up" className="btn-primary">Get Started <ArrowRight className="w-4 h-4" /></Link>
          </div>
        </div>
      )}
    </nav>
  );
}

// ─── Hero Section ───
function Hero() {
  return (
    <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 gradient-bg-subtle" />
      <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-brand-200/20 blur-3xl pointer-events-none" />
      <div className="absolute top-40 right-0 w-[300px] h-[300px] rounded-full bg-indigo-200/20 blur-3xl pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-6">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-50 border border-brand-200 text-brand-700 text-sm font-medium mb-8 animate-fade-in">
            <Sparkles className="w-4 h-4" />
            AI-Powered Synthetic User Research
          </div>

          {/* Headline */}
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-extrabold tracking-tight text-surface-900 leading-[1.1] mb-6 animate-slide-up">
            See your product through{' '}
            <span className="gradient-text">real eyes</span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg md:text-xl text-surface-500 max-w-2xl mx-auto mb-10 leading-relaxed animate-slide-up" style={{ animationDelay: '0.1s' }}>
            Give UseWorldview a URL and a goal — it creates AI users with real worldviews, 
            sends them into your product, and tells you what happened and why.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up" style={{ animationDelay: '0.2s' }}>
            <Link href="/sign-up" className="btn-primary text-base px-8 py-3.5 shadow-lg hover:shadow-xl">
              Start Your First Study
              <ArrowRight className="w-5 h-5" />
            </Link>
            <a href="#how-it-works" className="btn-secondary text-base px-8 py-3.5">
              See How It Works
            </a>
          </div>
        </div>

        {/* Illustrative mock card */}
        <div className="mt-16 md:mt-20 max-w-5xl mx-auto animate-slide-up" style={{ animationDelay: '0.3s' }}>
          <div className="glass-card rounded-2xl p-6 md:p-8 shadow-elevated">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-3 h-3 rounded-full bg-error" />
              <div className="w-3 h-3 rounded-full bg-warning" />
              <div className="w-3 h-3 rounded-full bg-success" />
              <div className="flex-1 mx-4 h-8 rounded-lg bg-surface-100 flex items-center px-4">
                <Search className="w-4 h-4 text-surface-400 mr-2" />
                <span className="text-sm text-surface-400">example-saas.com</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Mock persona card */}
              <div className="card p-5 border-brand-100 hover:border-brand-300 transition-colors">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-full gradient-bg flex items-center justify-center text-white font-bold text-sm">SP</div>
                  <div>
                    <p className="font-semibold text-surface-800 text-sm">Sarah Park</p>
                    <p className="text-xs text-surface-400">Startup Founder, 32</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 mb-2">
                  <span className="badge badge-success text-xs">Completed</span>
                  <span className="text-xs text-surface-400">7 pages visited</span>
                </div>
                <p className="text-xs text-surface-500 leading-relaxed">
                  &quot;The pricing page was confusing — I couldn&apos;t tell what was included in each tier.&quot;
                </p>
              </div>

              {/* Mock insight card */}
              <div className="card p-5 border-warning/30">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-warning-light flex items-center justify-center">
                    <Lightbulb className="w-4 h-4 text-warning" />
                  </div>
                  <p className="font-semibold text-surface-800 text-sm">Key Insight</p>
                </div>
                <p className="text-xs text-surface-500 leading-relaxed mb-3">
                  4/5 personas paused on the pricing page for 30+ seconds before leaving or comparing alternatives.
                </p>
                <div className="h-2 rounded-full bg-surface-100 overflow-hidden">
                  <div className="h-full w-4/5 rounded-full bg-gradient-to-r from-warning to-warning/60" />
                </div>
                <p className="text-xs text-surface-400 mt-1">80% affected</p>
              </div>

              {/* Mock recommendation card */}
              <div className="card p-5 border-success/30">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-success-light flex items-center justify-center">
                    <Target className="w-4 h-4 text-success" />
                  </div>
                  <p className="font-semibold text-surface-800 text-sm">Recommendation</p>
                </div>
                <p className="text-xs text-surface-500 leading-relaxed">
                  Add a feature-comparison table under each pricing tier and surface an inline FAQ addressing common questions.
                </p>
                <div className="mt-3 flex items-center gap-1">
                  <span className="badge badge-error text-xs">High Impact</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Problem Section ───
function ProblemSection() {
  const problems = [
    { icon: Clock, title: 'Expensive & Slow', desc: 'User research takes days to weeks and thousands of dollars per study.' },
    { icon: Users, title: 'Tiny Samples', desc: 'Most studies run 5–10 participants, missing edge-case segments entirely.' },
    { icon: Search, title: 'Shallow AI Tools', desc: 'Competitors scan a homepage and output a generic UX checklist. That\'s it.' },
    { icon: MessageSquare, title: 'No "Why"', desc: 'Analytics shows what users did — not what they were thinking or feeling.' },
    { icon: Zap, title: 'Feedback Too Late', desc: 'Most research happens post-launch, after users already had a bad experience.' },
  ];

  return (
    <section className="py-20 md:py-28 bg-surface-0">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-14">
          <p className="text-sm font-semibold text-brand-600 uppercase tracking-wider mb-3">The Problem</p>
          <h2 className="text-3xl md:text-4xl font-bold text-surface-900 mb-4">
            Traditional research is broken
          </h2>
          <p className="text-surface-500 max-w-2xl mx-auto">
            Companies need to understand how real users experience their product — but current methods aren&apos;t keeping up.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {problems.map((problem, i) => (
            <div
              key={problem.title}
              className="card card-interactive p-6 text-center"
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <div className="w-12 h-12 rounded-2xl bg-brand-50 flex items-center justify-center mx-auto mb-4">
                <problem.icon className="w-6 h-6 text-brand-600" />
              </div>
              <h3 className="font-semibold text-surface-800 mb-2 text-sm">{problem.title}</h3>
              <p className="text-xs text-surface-500 leading-relaxed">{problem.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── How It Works ───
function HowItWorks() {
  const steps = [
    { icon: Target, title: 'Define Your Goal', desc: 'Choose from 13 research templates or write your own question.' },
    { icon: Globe, title: 'Submit Your URL', desc: 'Enter your website or web app URL. No login needed.' },
    { icon: Brain, title: 'AI Builds Personas', desc: 'Full personalities with goals, fears, biases — not just demographics.' },
    { icon: MousePointerClick, title: 'Personas Use Your Product', desc: 'They navigate, click, read, doubt, and decide — like real people.' },
    { icon: MessageSquare, title: 'They Explain Why', desc: 'What confused them, what they trusted, why they left or stayed.' },
    { icon: BarChart3, title: 'You Get Recommendations', desc: 'Prioritized fixes with evidence, affected users, and impact.' },
  ];

  return (
    <section id="how-it-works" className="py-20 md:py-28 gradient-bg-subtle">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-brand-600 uppercase tracking-wider mb-3">How It Works</p>
          <h2 className="text-3xl md:text-4xl font-bold text-surface-900 mb-4">
            From URL to insights in minutes
          </h2>
          <p className="text-surface-500 max-w-2xl mx-auto">
            A single guided flow takes you from &quot;I have a URL and a question&quot; to &quot;I have persona-level, evidence-backed research.&quot;
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {steps.map((step, i) => (
            <div key={step.title} className="relative">
              <div className="card card-interactive p-6 h-full">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center text-white font-bold text-sm shadow-md">
                      {i + 1}
                    </div>
                  </div>
                  <div>
                    <h3 className="font-semibold text-surface-800 mb-1.5">{step.title}</h3>
                    <p className="text-sm text-surface-500 leading-relaxed">{step.desc}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Differentiator ───
function Differentiator() {
  const rows = [
    { dimension: 'Depth', competitor: 'Homepage scan only', uw: 'Enters the app, navigates multiple pages' },
    { dimension: 'Personas', competitor: 'Basic demographic tags', uw: 'Full worldview: motivations, fears, trust, price sensitivity' },
    { dimension: 'Behavior', competitor: 'Assumes the product is good', uw: 'Skeptical, realistic — can get confused or abandon' },
    { dimension: 'Output', competitor: 'Generic scored checklist', uw: 'Persona-level narrative + evidence + cross-persona patterns' },
    { dimension: 'Explainability', competitor: 'Rarely explains why', uw: 'Every insight traces to specific actions in a session' },
  ];

  return (
    <section className="py-20 md:py-28 bg-surface-0">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-14">
          <p className="text-sm font-semibold text-brand-600 uppercase tracking-wider mb-3">Why UseWorldview</p>
          <h2 className="text-3xl md:text-4xl font-bold text-surface-900 mb-4">
            Not another homepage scanner
          </h2>
          <p className="text-surface-500 max-w-2xl mx-auto">
            Competitors scan your homepage and output a checklist. We enter your product, use it as a real person would, and explain what happened.
          </p>
        </div>

        <div className="card overflow-hidden max-w-4xl mx-auto">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-surface-200">
                  <th className="text-left p-4 text-sm font-semibold text-surface-500 w-[20%]">Dimension</th>
                  <th className="text-left p-4 text-sm font-semibold text-surface-400 w-[40%]">Typical AI UX Tools</th>
                  <th className="text-left p-4 text-sm font-semibold text-brand-600 w-[40%]">UseWorldview</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.dimension} className="border-b border-surface-100 last:border-0 hover:bg-surface-50 transition-colors">
                    <td className="p-4 text-sm font-medium text-surface-700">{row.dimension}</td>
                    <td className="p-4 text-sm text-surface-400">{row.competitor}</td>
                    <td className="p-4 text-sm text-surface-700 font-medium">{row.uw}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Who It's For ───
function WhoItsFor() {
  const personas = [
    { role: 'Startup Founder', question: 'Will people understand and trust what I built?', icon: Zap, color: 'bg-violet-50 text-violet-600' },
    { role: 'Product Manager', question: 'Why are users dropping off in this flow?', icon: BarChart3, color: 'bg-blue-50 text-blue-600' },
    { role: 'UX Designer', question: 'Where are users getting confused or stuck?', icon: Eye, color: 'bg-pink-50 text-pink-600' },
    { role: 'Growth Marketer', question: 'What\'s stopping visitors from converting?', icon: Target, color: 'bg-emerald-50 text-emerald-600' },
    { role: 'Technical Founder', question: 'Can a new developer actually get started with this?', icon: FileText, color: 'bg-orange-50 text-orange-600' },
  ];

  return (
    <section id="who-its-for" className="py-20 md:py-28 gradient-bg-subtle">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-14">
          <p className="text-sm font-semibold text-brand-600 uppercase tracking-wider mb-3">Who It&apos;s For</p>
          <h2 className="text-3xl md:text-4xl font-bold text-surface-900 mb-4">
            Built for teams that ship
          </h2>
          <p className="text-surface-500 max-w-2xl mx-auto">
            Product, design, growth, and founding teams — anyone who needs to understand how real users experience their product.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {personas.map((persona) => (
            <div key={persona.role} className="card card-interactive p-6 text-center">
              <div className={`w-12 h-12 rounded-2xl ${persona.color} flex items-center justify-center mx-auto mb-4`}>
                <persona.icon className="w-6 h-6" />
              </div>
              <h3 className="font-semibold text-surface-800 mb-2 text-sm">{persona.role}</h3>
              <p className="text-xs text-surface-500 leading-relaxed italic">&quot;{persona.question}&quot;</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Depth Preview / Features ───
function Features() {
  const features = [
    {
      icon: Brain,
      title: 'The Worldview Engine',
      desc: 'Full psychographic personas — not demographic tags. Goals, fears, trust levels, price sensitivity, decision-making style, attention span, and 20+ attributes that make each AI user behave like a real person.',
      highlight: 'Not demographic tags — full personalities',
    },
    {
      icon: Route,
      title: 'Whole-App Exploration',
      desc: 'AI personas don\'t just scan your homepage. They enter your product, discover pages via navigation, interact with features, test multiple paths, and report on the entire experience.',
      highlight: 'Not homepage-only — the entire product',
    },
    {
      icon: FileText,
      title: 'Evidence-Backed Recommendations',
      desc: 'Every recommendation follows a rigorous format: Problem → Evidence → Affected Users → Why It Matters → Suggested Improvement. No generic, unsourced advice — every claim traces to a specific session event.',
      highlight: 'Not generic advice — traceable evidence',
    },
  ];

  return (
    <section id="features" className="py-20 md:py-28 bg-surface-0">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-14">
          <p className="text-sm font-semibold text-brand-600 uppercase tracking-wider mb-3">What Makes It Different</p>
          <h2 className="text-3xl md:text-4xl font-bold text-surface-900 mb-4">
            Depth you can actually trust
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <div key={feature.title} className="card card-interactive p-8">
              <div className="w-14 h-14 rounded-2xl bg-brand-50 flex items-center justify-center mb-6">
                <feature.icon className="w-7 h-7 text-brand-600" />
              </div>
              <h3 className="font-bold text-surface-900 text-lg mb-2">{feature.title}</h3>
              <p className="text-sm text-brand-600 font-medium mb-3">{feature.highlight}</p>
              <p className="text-sm text-surface-500 leading-relaxed">{feature.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── CTA Band ───
function CTABand() {
  return (
    <section className="py-20 md:py-24">
      <div className="max-w-7xl mx-auto px-6">
        <div className="relative rounded-3xl overflow-hidden gradient-bg p-12 md:p-16 text-center">
          {/* Decorative orbs */}
          <div className="absolute top-0 left-1/4 w-64 h-64 rounded-full bg-white/10 blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-48 h-48 rounded-full bg-white/10 blur-3xl" />

          <div className="relative">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Ready to see your product through their eyes?
            </h2>
            <p className="text-white/80 max-w-xl mx-auto mb-8 text-lg">
              Start your first study in minutes. No credit card required.
            </p>
            <Link
              href="/sign-up"
              className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-brand-700 font-semibold rounded-xl hover:bg-white/90 transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
            >
              Get Started Free
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Footer ───
function Footer() {
  return (
    <footer className="bg-surface-0 border-t border-surface-200 py-12">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg gradient-bg flex items-center justify-center">
              <Eye className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-surface-800">
              Use<span className="gradient-text">Worldview</span>
            </span>
          </div>

          <div className="flex items-center gap-6 text-sm text-surface-400">
            <a href="#how-it-works" className="hover:text-surface-600 transition-colors">How it works</a>
            <a href="#who-its-for" className="hover:text-surface-600 transition-colors">Who it&apos;s for</a>
            <a href="#features" className="hover:text-surface-600 transition-colors">Features</a>
          </div>

          <p className="text-xs text-surface-400 text-center md:text-right max-w-sm">
            By submitting a URL, you confirm you own the site or have permission to run automated testing against it.
          </p>
        </div>

        <div className="mt-8 pt-6 border-t border-surface-100 text-center">
          <p className="text-xs text-surface-400">
            © {new Date().getFullYear()} Truebases. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}

// ─── Page ───
export default function HomePage() {
  return (
    <main className="min-h-screen">
      <Navbar />
      <Hero />
      <ProblemSection />
      <HowItWorks />
      <Differentiator />
      <WhoItsFor />
      <Features />
      <CTABand />
      <Footer />
    </main>
  );
}
