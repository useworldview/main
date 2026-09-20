'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import { type InteractionEvent, type Persona, type AgentSession } from '@/lib/types';
import { track } from '@/lib/analytics';
import {
  ArrowLeft, Play, Pause, SkipForward, SkipBack,
  MousePointerClick, ScrollText, Type, Globe, Search,
  ArrowLeftCircle, ArrowRightCircle, Clock, Eye, AlertTriangle,
  ChevronRight, Maximize2, XCircle, Brain, Target, Sparkles, Activity
} from 'lucide-react';

const EVENT_ICONS: Record<string, { icon: typeof MousePointerClick; color: string }> = {
  click: { icon: MousePointerClick, color: 'text-blue-500' },
  scroll: { icon: ScrollText, color: 'text-violet-500' },
  type: { icon: Type, color: 'text-emerald-500' },
  navigate: { icon: Globe, color: 'text-brand-500' },
  search: { icon: Search, color: 'text-amber-500' },
  back: { icon: ArrowLeftCircle, color: 'text-surface-500' },
  forward: { icon: ArrowRightCircle, color: 'text-surface-500' },
  wait: { icon: Clock, color: 'text-surface-400' },
  screenshot: { icon: Eye, color: 'text-purple-500' },
  form_submit: { icon: Type, color: 'text-teal-500' },
  page_error: { icon: AlertTriangle, color: 'text-error' },
  dead_end: { icon: XCircle, color: 'text-warning' },
};

export default function JourneyReplayPage() {
  const params = useParams();
  const studyId = params.studyId as string;
  const personaId = params.personaId as string;

  const [persona, setPersona] = useState<Persona | null>(null);
  const [session, setSession] = useState<AgentSession | null>(null);
  const [events, setEvents] = useState<InteractionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    track('replay_opened', { persona_id: personaId });
    const supabase = createClient();

    async function fetchData() {
      const [personaRes, sessionRes] = await Promise.all([
        supabase.from('personas').select('*').eq('id', personaId).single(),
        supabase.from('agent_sessions').select('*').eq('persona_id', personaId).single(),
      ]);

      if (personaRes.data) setPersona(personaRes.data as Persona);
      if (sessionRes.data) {
        setSession(sessionRes.data as AgentSession);
        const { data: eventsData } = await supabase
          .from('interaction_events')
          .select('*')
          .eq('session_id', sessionRes.data.id)
          .order('sequence_no', { ascending: true });
        if (eventsData) setEvents(eventsData as InteractionEvent[]);
      }
      setLoading(false);
    }

    fetchData();
  }, [personaId]);

  // Auto-play loop with configurable speed
  useEffect(() => {
    if (!isPlaying || events.length === 0) return;
    const intervalMs = Math.max(500, Math.floor(2000 / playbackSpeed));
    const timer = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= events.length - 1) {
          setIsPlaying(false);
          track('replay_completed', { persona_id: personaId });
          return prev;
        }
        return prev + 1;
      });
    }, intervalMs);
    return () => clearInterval(timer);
  }, [isPlaying, events.length, personaId, playbackSpeed]);

  if (loading || !persona) {
    return (
      <div className="page-enter space-y-6">
        <div className="skeleton h-8 w-48 mb-6" />
        <div className="skeleton h-[600px] rounded-2xl" />
      </div>
    );
  }

  const currentEvent = events[currentStep];
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;

  return (
    <div className="page-enter space-y-6">
      {/* ─── Breadcrumb & Top Bar ─── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs font-mono text-surface-400">
          <Link href={`/studies/${studyId}`} className="hover:text-brand-600 transition-colors flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" />
            Study Results
          </Link>
          <ChevronRight className="w-3 h-3" />
          <Link href={`/studies/${studyId}/personas/${personaId}`} className="hover:text-brand-600 transition-colors">
            {persona.name}
          </Link>
          <ChevronRight className="w-3 h-3" />
          <span className="text-surface-700 dark:text-surface-300 font-semibold">Studio Replay</span>
        </div>

        <div className="flex items-center gap-3">
          <span className="badge badge-brand text-[11px] font-mono">
            <Activity className="w-3 h-3 animate-pulse mr-1" />
            {events.length} Steps Logged
          </span>
          <span className="text-xs font-mono text-surface-400">
            {session?.pages_visited || 0} Pages Traversed
          </span>
        </div>
      </div>

      {/* ─── Persona Header Bar ─── */}
      <div className="card p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center text-white font-bold text-sm shadow-sm">
            {persona.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
          </div>
          <div>
            <h1 className="text-base font-bold text-surface-900">{persona.name}&apos;s Traversal</h1>
            <p className="text-xs text-surface-400">{persona.profession || 'Autonomous Persona'} • Session ID #{session?.id?.slice(0, 8)}</p>
          </div>
        </div>

        {/* Playback speed buttons */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-surface-100 dark:bg-surface-100 border border-surface-200 dark:border-surface-200 text-xs font-mono">
          {[0.5, 1, 2].map((speed) => (
            <button
              key={speed}
              onClick={() => setPlaybackSpeed(speed)}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                playbackSpeed === speed
                  ? 'bg-surface-0 dark:bg-surface-0 text-brand-600 font-bold shadow-sm'
                  : 'text-surface-400 hover:text-surface-700'
              }`}
            >
              {speed}x
            </button>
          ))}
        </div>
      </div>

      {/* ─── Studio Grid: Viewport & Timeline ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Main: Browser Viewport & Controls (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          <div className="browser-frame glass-card border border-surface-200 dark:border-surface-200 shadow-elevated">
            {/* Browser Chrome Header */}
            <div className="flex items-center justify-between px-4 py-2.5 bg-surface-100/80 dark:bg-surface-900/60 border-b border-surface-200 dark:border-surface-200">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                <div className="ml-3 flex items-center gap-1.5 px-3 py-1 rounded-md bg-surface-0/90 dark:bg-surface-100 text-xs font-mono text-surface-600 border border-surface-200 dark:border-surface-200 max-w-sm truncate">
                  <Globe className="w-3 h-3 text-brand-500 shrink-0" />
                  <span className="truncate">{currentEvent?.page_url || 'Target Application'}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 font-mono text-xs">
                <span className="badge badge-brand text-[10px]">
                  Step {currentStep + 1} of {events.length}
                </span>
              </div>
            </div>

            {/* Viewport Screen */}
            <div className="aspect-video bg-surface-900/5 dark:bg-surface-950 relative flex items-center justify-center overflow-hidden">
              {currentEvent?.screenshot_ref ? (
                <img
                  src={`${supabaseUrl}/storage/v1/object/public/screenshots/${currentEvent.screenshot_ref}`}
                  alt={`Step ${currentStep + 1}`}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="text-center p-8">
                  <div className="w-14 h-14 rounded-2xl bg-surface-100 dark:bg-surface-100 flex items-center justify-center mx-auto mb-3">
                    <Eye className="w-7 h-7 text-surface-400" />
                  </div>
                  <p className="text-sm font-semibold text-surface-700 dark:text-surface-300">Headless Browser Step #{currentStep + 1}</p>
                  <p className="text-xs text-surface-400 mt-1">Autonomous headless DOM action executed</p>
                </div>
              )}

              {/* Status overlay badge */}
              {currentEvent && (
                <div className="absolute top-4 left-4 z-10">
                  {currentEvent.event_type === 'page_error' ? (
                    <span className="badge badge-error">⚠️ Page Error</span>
                  ) : currentEvent.event_type === 'dead_end' ? (
                    <span className="badge badge-warning">🚫 Dead End</span>
                  ) : (
                    <span className="badge badge-brand capitalize">{currentEvent.event_type.replace(/_/g, ' ')}</span>
                  )}
                </div>
              )}
            </div>

            {/* Controls Bar */}
            <div className="p-4 border-t border-surface-200 dark:border-surface-200 bg-surface-0 dark:bg-surface-0">
              {/* Timeline scrubber slider */}
              <div className="mb-4">
                <input
                  type="range"
                  min={0}
                  max={Math.max(events.length - 1, 0)}
                  value={currentStep}
                  onChange={(e) => setCurrentStep(Number(e.target.value))}
                  className="w-full h-2 rounded-full appearance-none cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, var(--color-brand-500) ${(currentStep / Math.max(events.length - 1, 1)) * 100}%, var(--color-surface-200) ${(currentStep / Math.max(events.length - 1, 1)) * 100}%)`,
                  }}
                />
              </div>

              {/* Playback action buttons */}
              <div className="flex items-center justify-between">
                <div className="text-xs font-mono text-surface-400">
                  Step {currentStep + 1} / {events.length}
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                    disabled={currentStep === 0}
                    className="p-2 rounded-lg hover:bg-surface-100 text-surface-600 disabled:opacity-30 transition-colors"
                    aria-label="Previous step"
                  >
                    <SkipBack className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="w-11 h-11 rounded-full gradient-bg flex items-center justify-center text-white shadow-glow hover:brightness-105 transition-all"
                    aria-label={isPlaying ? 'Pause replay' : 'Play replay'}
                  >
                    {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                  </button>
                  <button
                    onClick={() => setCurrentStep(Math.min(events.length - 1, currentStep + 1))}
                    disabled={currentStep >= events.length - 1}
                    className="p-2 rounded-lg hover:bg-surface-100 text-surface-600 disabled:opacity-30 transition-colors"
                    aria-label="Next step"
                  >
                    <SkipForward className="w-5 h-5" />
                  </button>
                </div>

                <div className="text-xs font-mono text-surface-400">
                  {playbackSpeed}x Speed
                </div>
              </div>
            </div>
          </div>

          {/* Synchronized Inner Monologue card */}
          {currentEvent && (
            <div className="card p-5">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-brand-50 dark:bg-brand-950 flex items-center justify-center text-brand-600 shrink-0">
                  <Brain className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <p className="text-xs font-bold text-surface-900 mb-1 flex items-center gap-2">
                    <span>{persona.name}&apos;s Cognitive Monologue</span>
                    <span className="badge badge-brand text-[10px]">Active Step</span>
                  </p>
                  <p className="text-sm text-surface-700 dark:text-surface-300 italic leading-relaxed">
                    &ldquo;{(currentEvent.details as Record<string, string>)?.reasoning || 
                     (currentEvent.details as Record<string, string>)?.thought ||
                     `Executed ${currentEvent.event_type}${currentEvent.target_element ? ` on element "${currentEvent.target_element}"` : ''}. Continuing objective traversal.`}&rdquo;
                  </p>
                  {currentEvent.target_element && (
                    <div className="mt-3 flex items-center gap-2 text-xs font-mono text-surface-400 bg-surface-100 dark:bg-surface-100 px-2.5 py-1 rounded-md w-fit">
                      <Target className="w-3 h-3 text-brand-500" />
                      <span>Target: {currentEvent.target_element}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Raw JSON toggle */}
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-xs text-brand-500 mt-4 hover:underline transition-colors block"
              >
                {showDetails ? 'Hide' : 'Inspect'} Raw Event Telemetry
              </button>
              {showDetails && (
                <pre className="mt-2 p-3 rounded-xl bg-surface-100 dark:bg-surface-100 text-xs font-mono text-surface-700 dark:text-surface-300 overflow-auto max-h-48">
                  {JSON.stringify(currentEvent, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>

        {/* Right: Step Timeline List (4 cols) */}
        <div className="lg:col-span-4 card p-4 max-h-[780px] overflow-y-auto">
          <div className="flex items-center justify-between mb-4 px-2">
            <h3 className="font-bold text-sm text-surface-900">Step Timeline</h3>
            <span className="text-xs font-mono text-surface-400">{events.length} events</span>
          </div>

          <div className="space-y-1.5">
            {events.map((event, i) => {
              const eventConfig = EVENT_ICONS[event.event_type] || { icon: Eye, color: 'text-surface-400' };
              const Icon = eventConfig.icon;
              const isCurrent = i === currentStep;

              return (
                <button
                  key={event.id}
                  onClick={() => setCurrentStep(i)}
                  className={`w-full text-left p-2.5 rounded-xl transition-all flex items-start gap-2.5 ${
                    isCurrent
                      ? 'bg-brand-50/80 dark:bg-brand-950/60 border border-brand-300 dark:border-brand-700 shadow-sm'
                      : i < currentStep
                      ? 'hover:bg-surface-100 dark:hover:bg-surface-100 opacity-70'
                      : 'hover:bg-surface-100 dark:hover:bg-surface-100'
                  }`}
                >
                  <div className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 ${
                    isCurrent ? 'bg-brand-500 text-white' : 'bg-surface-100 dark:bg-surface-100'
                  }`}>
                    <Icon className={`w-3.5 h-3.5 ${isCurrent ? 'text-white' : eventConfig.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-semibold capitalize ${isCurrent ? 'text-brand-700 dark:text-brand-300' : 'text-surface-700 dark:text-surface-300'}`}>
                      {event.event_type.replace(/_/g, ' ')}
                    </p>
                    {event.target_element && (
                      <p className="text-[11px] text-surface-400 truncate font-mono">{event.target_element}</p>
                    )}
                  </div>
                  <span className="text-[10px] font-mono text-surface-400 shrink-0">#{i + 1}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
