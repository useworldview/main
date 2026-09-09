'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { createClient } from '@/lib/supabase/client';
import { type InteractionEvent, type Persona, type AgentSession } from '@/lib/types';
import { track } from '@/lib/analytics';
import {
  ArrowLeft, Play, Pause, SkipForward, SkipBack,
  MousePointerClick, ScrollText, Type, Globe, Search,
  ArrowLeftCircle, ArrowRightCircle, Clock, Eye, AlertTriangle,
  ChevronRight, Maximize2, XCircle
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

  // Auto-play
  useEffect(() => {
    if (!isPlaying || events.length === 0) return;
    const timer = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= events.length - 1) {
          setIsPlaying(false);
          track('replay_completed', { persona_id: personaId });
          return prev;
        }
        return prev + 1;
      });
    }, 2000);
    return () => clearInterval(timer);
  }, [isPlaying, events.length, personaId]);

  if (loading || !persona) {
    return (
      <div className="page-enter">
        <div className="skeleton h-8 w-48 mb-6" />
        <div className="skeleton h-[600px] rounded-2xl" />
      </div>
    );
  }

  const currentEvent = events[currentStep];
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;

  return (
    <div className="page-enter">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-surface-400 mb-6">
        <Link href={`/studies/${studyId}`} className="hover:text-brand-600 transition-colors">
          Study
        </Link>
        <ChevronRight className="w-4 h-4" />
        <Link href={`/studies/${studyId}/personas/${personaId}`} className="hover:text-brand-600 transition-colors">
          {persona.name}
        </Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-surface-700 font-medium">Journey Replay</span>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full gradient-bg flex items-center justify-center text-white font-bold text-sm">
            {persona.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
          </div>
          <div>
            <h1 className="text-xl font-bold text-surface-900">{persona.name}&apos;s Journey</h1>
            <p className="text-sm text-surface-400">{events.length} steps • {session?.pages_visited || 0} pages visited</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main: Screenshot viewer */}
        <div className="lg:col-span-2">
          <div className="card overflow-hidden">
            {/* Screenshot area */}
            <div className="aspect-video bg-surface-100 relative flex items-center justify-center overflow-hidden">
              {currentEvent?.screenshot_ref ? (
                <img
                  src={`${supabaseUrl}/storage/v1/object/public/screenshots/${currentEvent.screenshot_ref}`}
                  alt={`Step ${currentStep + 1}`}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="text-center">
                  <Eye className="w-12 h-12 text-surface-300 mx-auto mb-2" />
                  <p className="text-sm text-surface-400">No screenshot available for this step</p>
                </div>
              )}

              {/* Event type overlay */}
              {currentEvent && (
                <div className="absolute top-4 left-4">
                  {currentEvent.event_type === 'page_error' ? (
                    <span className="badge badge-error">⚠️ Page Error</span>
                  ) : currentEvent.event_type === 'dead_end' ? (
                    <span className="badge badge-warning">🚫 Dead End</span>
                  ) : (
                    <span className="badge badge-brand capitalize">{currentEvent.event_type}</span>
                  )}
                </div>
              )}

              {/* Step counter */}
              <div className="absolute top-4 right-4">
                <span className="badge bg-surface-900/70 text-white backdrop-blur-sm">
                  Step {currentStep + 1} / {events.length}
                </span>
              </div>
            </div>

            {/* Controls */}
            <div className="p-4 border-t border-surface-200">
              {/* Timeline scrubber */}
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

              {/* Playback buttons */}
              <div className="flex items-center justify-center gap-3">
                <button
                  onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                  disabled={currentStep === 0}
                  className="btn-ghost disabled:opacity-30"
                >
                  <SkipBack className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="w-12 h-12 rounded-full gradient-bg flex items-center justify-center text-white shadow-lg hover:shadow-xl transition-shadow"
                >
                  {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                </button>
                <button
                  onClick={() => setCurrentStep(Math.min(events.length - 1, currentStep + 1))}
                  disabled={currentStep >= events.length - 1}
                  className="btn-ghost disabled:opacity-30"
                >
                  <SkipForward className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>

          {/* Current event reasoning */}
          {currentEvent && (
            <div className="card p-5 mt-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full gradient-bg flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
                  {persona.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                </div>
                <div>
                  <p className="text-sm font-medium text-surface-800 mb-1">
                    {persona.name}&apos;s Thought
                  </p>
                  <p className="text-sm text-surface-600 italic">
                    {(currentEvent.details as Record<string, string>)?.reasoning || 
                     (currentEvent.details as Record<string, string>)?.thought ||
                     `Performed ${currentEvent.event_type}${currentEvent.target_element ? ` on "${currentEvent.target_element}"` : ''}`}
                  </p>
                  {currentEvent.page_url && (
                    <p className="text-xs text-surface-400 mt-2 flex items-center gap-1">
                      <Globe className="w-3 h-3" />
                      {currentEvent.page_url}
                    </p>
                  )}
                </div>
              </div>

              {/* Collapsed details */}
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-xs text-brand-500 mt-3 hover:text-brand-700 transition-colors"
              >
                {showDetails ? 'Hide' : 'Show'} raw event data
              </button>
              {showDetails && (
                <pre className="mt-2 p-3 rounded-lg bg-surface-50 text-xs text-surface-600 overflow-auto max-h-48">
                  {JSON.stringify(currentEvent, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>

        {/* Right: Step timeline */}
        <div className="card p-4 max-h-[700px] overflow-y-auto">
          <h3 className="font-semibold text-surface-800 mb-4 px-2">Timeline</h3>
          <div className="space-y-1">
            {events.map((event, i) => {
              const eventConfig = EVENT_ICONS[event.event_type] || { icon: Eye, color: 'text-surface-400' };
              const Icon = eventConfig.icon;
              const isCurrent = i === currentStep;

              return (
                <button
                  key={event.id}
                  onClick={() => setCurrentStep(i)}
                  className={`w-full text-left p-3 rounded-xl transition-all flex items-start gap-3 ${
                    isCurrent
                      ? 'bg-brand-50 border border-brand-200'
                      : i < currentStep
                      ? 'hover:bg-surface-50 opacity-60'
                      : 'hover:bg-surface-50'
                  }`}
                >
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    isCurrent ? 'bg-brand-100' : 'bg-surface-100'
                  }`}>
                    <Icon className={`w-4 h-4 ${isCurrent ? 'text-brand-600' : eventConfig.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-medium capitalize ${isCurrent ? 'text-brand-700' : 'text-surface-700'}`}>
                      {event.event_type.replace(/_/g, ' ')}
                    </p>
                    {event.target_element && (
                      <p className="text-xs text-surface-400 truncate">{event.target_element}</p>
                    )}
                  </div>
                  <span className="text-xs text-surface-400 flex-shrink-0">{i + 1}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
