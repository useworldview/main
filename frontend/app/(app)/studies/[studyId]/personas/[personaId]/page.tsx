'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import {
  type Persona, type AgentSession, type Finding, type DecisionExplanation,
  FEELING_CONFIG, type FeelingLabel
} from '@/lib/types';
import { track } from '@/lib/analytics';
import {
  ArrowLeft, Play, User, MapPin, Briefcase, GraduationCap,
  Brain, Shield, Target, Heart, AlertTriangle, ThumbsUp,
  ThumbsDown, CheckCircle, XCircle, MessageSquare, Eye,
  Route, Clock, ChevronRight, Sparkles
} from 'lucide-react';

export default function PersonaDetailPage() {
  const params = useParams();
  const studyId = params.studyId as string;
  const personaId = params.personaId as string;

  const [persona, setPersona] = useState<Persona | null>(null);
  const [session, setSession] = useState<AgentSession | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [decisions, setDecisions] = useState<DecisionExplanation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    track('persona_detail_viewed', { persona_id: personaId });
    const supabase = createClient();

    async function fetchData() {
      const [personaRes, sessionRes] = await Promise.all([
        supabase.from('personas').select('*').eq('id', personaId).single(),
        supabase.from('agent_sessions').select('*').eq('persona_id', personaId).single(),
      ]);

      if (personaRes.data) setPersona(personaRes.data as Persona);
      if (sessionRes.data) {
        const sess = sessionRes.data as AgentSession;
        setSession(sess);

        const [findingsRes, decisionsRes] = await Promise.all([
          supabase.from('findings').select('*').eq('session_id', sess.id),
          supabase.from('decision_explanations').select('*').eq('session_id', sess.id),
        ]);
        if (findingsRes.data) setFindings(findingsRes.data as Finding[]);
        if (decisionsRes.data) setDecisions(decisionsRes.data as DecisionExplanation[]);
      }
      setLoading(false);
    }

    fetchData();
  }, [personaId]);

  if (loading || !persona) {
    return (
      <div className="page-enter">
        <div className="skeleton h-8 w-48 mb-6" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="skeleton h-96 rounded-2xl" />
          <div className="lg:col-span-2 skeleton h-96 rounded-2xl" />
        </div>
      </div>
    );
  }

  const likes = findings.filter(f => f.type === 'like');
  const dislikes = findings.filter(f => f.type === 'dislike');
  const feelings = findings.filter(f => f.type === 'feeling');
  const trustSignals = findings.filter(f => f.type === 'trust');
  const distrustSignals = findings.filter(f => f.type === 'distrust');

  return (
    <div className="page-enter">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-surface-400 mb-6">
        <Link href={`/studies/${studyId}`} className="hover:text-brand-600 transition-colors flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" />
          Study Results
        </Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-surface-700 font-medium">{persona.name}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Identity & Worldview */}
        <div className="space-y-4">
          {/* Identity Card */}
          <div className="card p-6">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-14 h-14 rounded-full gradient-bg flex items-center justify-center text-white font-bold text-lg">
                {persona.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
              </div>
              <div>
                <h1 className="text-xl font-bold text-surface-900">{persona.name}</h1>
                <p className="text-sm text-surface-400">
                  {persona.age && `${persona.age} • `}{persona.profession}
                </p>
              </div>
            </div>

            <div className="space-y-3 text-sm">
              {persona.location && (
                <div className="flex items-center gap-2.5 text-surface-600">
                  <MapPin className="w-4 h-4 text-surface-400" />
                  {persona.location}
                </div>
              )}
              {persona.education && (
                <div className="flex items-center gap-2.5 text-surface-600">
                  <GraduationCap className="w-4 h-4 text-surface-400" />
                  {persona.education}
                </div>
              )}
              {persona.income_level && (
                <div className="flex items-center gap-2.5 text-surface-600">
                  <Briefcase className="w-4 h-4 text-surface-400" />
                  {persona.income_level}
                </div>
              )}
            </div>
          </div>

          {/* Worldview Card */}
          <div className="card p-6">
            <h3 className="font-semibold text-surface-800 mb-4 flex items-center gap-2">
              <Brain className="w-5 h-5 text-brand-500" />
              Worldview
            </h3>
            <div className="space-y-3 text-sm">
              {persona.worldview?.trust_level && (
                <WorldviewItem label="Trust Level" value={persona.worldview.trust_level} />
              )}
              {persona.worldview?.digital_literacy && (
                <WorldviewItem label="Digital Literacy" value={persona.worldview.digital_literacy} />
              )}
              {persona.worldview?.price_sensitivity && (
                <WorldviewItem label="Price Sensitivity" value={persona.worldview.price_sensitivity} />
              )}
              {persona.worldview?.risk_tolerance && (
                <WorldviewItem label="Risk Tolerance" value={persona.worldview.risk_tolerance} />
              )}
              {persona.worldview?.decision_making_style && (
                <WorldviewItem label="Decision Style" value={persona.worldview.decision_making_style} />
              )}
              {persona.worldview?.patience_level && (
                <WorldviewItem label="Patience" value={persona.worldview.patience_level} />
              )}
              {persona.worldview?.attention_span && (
                <WorldviewItem label="Attention Span" value={persona.worldview.attention_span} />
              )}
            </div>

            {persona.worldview?.goals && persona.worldview.goals.length > 0 && (
              <div className="mt-4 pt-4 border-t border-surface-100">
                <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-2">Goals</p>
                <div className="flex flex-wrap gap-1.5">
                  {persona.worldview.goals.map((g, i) => (
                    <span key={i} className="badge badge-brand">{formatTraitValue(g)}</span>
                  ))}
                </div>
              </div>
            )}

            {persona.worldview?.fears && persona.worldview.fears.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-2">Fears</p>
                <div className="flex flex-wrap gap-1.5">
                  {persona.worldview.fears.map((f, i) => (
                    <span key={i} className="badge badge-error">{formatTraitValue(f)}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Context Card */}
          {persona.situational_context && (
            <div className="card p-6">
              <h3 className="font-semibold text-surface-800 mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-brand-500" />
                Context
              </h3>
              <div className="space-y-3 text-sm">
                {persona.situational_context.reason_for_visiting && (
                  <div>
                    <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Why visiting</p>
                    <p className="text-surface-600">{formatTraitValue(persona.situational_context.reason_for_visiting)}</p>
                  </div>
                )}
                {persona.situational_context.objective && (
                  <div>
                    <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Objective</p>
                    <p className="text-surface-600">{formatTraitValue(persona.situational_context.objective)}</p>
                  </div>
                )}
                {persona.situational_context.current_situation && (
                  <div>
                    <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Situation</p>
                    <p className="text-surface-600">{formatTraitValue(persona.situational_context.current_situation)}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Journey Replay CTA */}
          {session && (
            <Link
              href={`/studies/${studyId}/personas/${personaId}/replay`}
              className="card p-5 flex items-center gap-4 card-interactive gradient-border group"
            >
              <div className="w-12 h-12 rounded-xl gradient-bg flex items-center justify-center">
                <Play className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-surface-800">Watch Journey Replay</p>
                <p className="text-xs text-surface-400">{session.step_count} steps • {session.pages_visited} pages</p>
              </div>
              <ChevronRight className="w-5 h-5 text-surface-400 group-hover:text-brand-500 transition-colors" />
            </Link>
          )}
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Outcome */}
          {session && (
            <div className={`card p-6 ${
              session.outcome === 'completed' ? 'border-success/30' :
              session.outcome === 'abandoned' ? 'border-warning/30' : 'border-error/30'
            }`}>
              <div className="flex items-center gap-3 mb-3">
                {session.outcome === 'completed' && <CheckCircle className="w-6 h-6 text-success" />}
                {session.outcome === 'abandoned' && <XCircle className="w-6 h-6 text-warning" />}
                {session.outcome === 'error' && <AlertTriangle className="w-6 h-6 text-error" />}
                <div>
                  <h3 className="font-semibold text-surface-800 capitalize">{session.outcome || session.status}</h3>
                  <p className="text-xs text-surface-400">
                    {session.pages_visited} pages • {session.step_count} steps
                  </p>
                </div>
              </div>
              {session.outcome_reason && (
                <p className="text-sm text-surface-600 italic border-l-3 border-brand-300 pl-4 py-1">
                  &quot;{session.outcome_reason}&quot;
                </p>
              )}
            </div>
          )}

          {/* Feelings */}
          {feelings.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold text-surface-800 mb-4 flex items-center gap-2">
                <Heart className="w-5 h-5 text-pink-500" />
                How They Felt
              </h3>
              <div className="flex flex-wrap gap-2">
                {feelings.map((f) => {
                  const config = f.feeling_label ? FEELING_CONFIG[f.feeling_label as FeelingLabel] : null;
                  return (
                    <div key={f.id} className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-50 border border-surface-200">
                      {config && <span>{config.emoji}</span>}
                      <span className="text-sm text-surface-700 capitalize">{f.feeling_label || f.description}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Likes & Dislikes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="card p-5">
              <h3 className="font-semibold text-surface-800 mb-3 flex items-center gap-2">
                <ThumbsUp className="w-4 h-4 text-success" />
                Liked ({likes.length})
              </h3>
              <div className="space-y-2">
                {likes.map((f) => (
                  <div key={f.id} className="p-3 rounded-lg bg-success-light/50 text-sm text-surface-700">
                    {f.description}
                  </div>
                ))}
                {likes.length === 0 && <p className="text-sm text-surface-400">Nothing liked.</p>}
              </div>
            </div>

            <div className="card p-5">
              <h3 className="font-semibold text-surface-800 mb-3 flex items-center gap-2">
                <ThumbsDown className="w-4 h-4 text-error" />
                Disliked ({dislikes.length})
              </h3>
              <div className="space-y-2">
                {dislikes.map((f) => (
                  <div key={f.id} className="p-3 rounded-lg bg-error-light/50 text-sm text-surface-700">
                    {f.description}
                  </div>
                ))}
                {dislikes.length === 0 && <p className="text-sm text-surface-400">Nothing disliked.</p>}
              </div>
            </div>
          </div>

          {/* Trust Signals */}
          {(trustSignals.length > 0 || distrustSignals.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="card p-5">
                <h3 className="font-semibold text-surface-800 mb-3 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-success" />
                  Trust Signals ({trustSignals.length})
                </h3>
                <div className="space-y-2">
                  {trustSignals.map((f) => (
                    <div key={f.id} className="p-3 rounded-lg bg-success-light/30 text-sm text-surface-700">{f.description}</div>
                  ))}
                </div>
              </div>
              <div className="card p-5">
                <h3 className="font-semibold text-surface-800 mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-error" />
                  Distrust Signals ({distrustSignals.length})
                </h3>
                <div className="space-y-2">
                  {distrustSignals.map((f) => (
                    <div key={f.id} className="p-3 rounded-lg bg-error-light/30 text-sm text-surface-700">{f.description}</div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Decision Explanations */}
          {decisions.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold text-surface-800 mb-4 flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-brand-500" />
                Decision Explanations
              </h3>
              <div className="space-y-4">
                {decisions.map((d) => (
                  <div key={d.id} className="p-4 rounded-xl bg-surface-50 border border-surface-100">
                    <span className={`badge ${
                      d.decision_type === 'abandon' ? 'badge-warning' :
                      d.decision_type === 'signup' || d.decision_type === 'purchase' ? 'badge-success' : 'badge-info'
                    } mb-2`}>
                      {d.decision_type.replace(/_/g, ' ')}
                    </span>
                    <p className="text-sm text-surface-700">{d.rationale_text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function formatTraitValue(val: unknown): string {
  if (val === null || val === undefined) return '';
  if (typeof val === 'string' || typeof val === 'number') return String(val);
  if (typeof val === 'object') {
    const obj = val as Record<string, unknown>;
    if (obj.score !== undefined && obj.explanation) {
      return `${obj.score}/10 — ${obj.explanation}`;
    }
    if (obj.score !== undefined) return `${obj.score}/10`;
    if (obj.level !== undefined) return `${obj.level}/10`;
    if (obj.value !== undefined) return String(obj.value);
    if (obj.explanation) return String(obj.explanation);
    if (obj.description) return String(obj.description);
    return (
      Object.values(obj)
        .filter((v) => typeof v === 'string' || typeof v === 'number')
        .join(' - ') || ''
    );
  }
  return String(val);
}

function WorldviewItem({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-surface-500">{label}</span>
      <span className="text-surface-800 font-medium text-right">{formatTraitValue(value)}</span>
    </div>
  );
}
