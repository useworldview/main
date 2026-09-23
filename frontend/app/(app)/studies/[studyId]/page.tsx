'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import { retryFailedSessions, cancelStudy } from '@/lib/api';
import {
  type Study, type AgentSession, type Persona, type Finding,
  type CrossPersonaInsight, type Recommendation,
  STUDY_STATUS_CONFIG, FEELING_CONFIG
} from '@/lib/types';
import { formatDate, getDomainFromUrl, percentDisplay } from '@/lib/utils';
import { track } from '@/lib/analytics';
import {
  Globe, Clock, Users, Loader2, CheckCircle, XCircle,
  AlertTriangle, ArrowRight, ThumbsUp, ThumbsDown, Shield,
  ShieldAlert, Brain, TrendingUp, Eye, BarChart3,
  ChevronRight, RefreshCw, Lightbulb, Target, Sparkles, StopCircle
} from 'lucide-react';

export default function StudyResultsPage() {
  const params = useParams();
  const studyId = params.studyId as string;

  const [study, setStudy] = useState<Study | null>(null);
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [insights, setInsights] = useState<CrossPersonaInsight[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'insights' | 'recommendations'>('overview');
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    track('dashboard_viewed', { study_id: studyId });
    const supabase = createClient();

    async function fetchAll() {
      const [studyRes, sessionsRes, personasRes, findingsRes, insightsRes, recsRes] = await Promise.all([
        supabase.from('studies').select('*').eq('id', studyId).single(),
        supabase.from('agent_sessions').select('*').eq('study_id', studyId).order('created_at'),
        supabase.from('personas').select('*').eq('study_id', studyId),
        supabase.from('findings').select('*').in('session_id',
          (await supabase.from('agent_sessions').select('id').eq('study_id', studyId)).data?.map(s => s.id) || []
        ),
        supabase.from('cross_persona_insights').select('*').eq('study_id', studyId),
        supabase.from('recommendations').select('*').eq('study_id', studyId).order('priority_score', { ascending: false }),
      ]);

      if (studyRes.data) setStudy(studyRes.data as Study);
      if (sessionsRes.data) setSessions(sessionsRes.data as AgentSession[]);
      if (personasRes.data) setPersonas(personasRes.data as Persona[]);
      if (findingsRes.data) setFindings(findingsRes.data as Finding[]);
      if (insightsRes.data) setInsights(insightsRes.data as CrossPersonaInsight[]);
      if (recsRes.data) setRecommendations(recsRes.data as Recommendation[]);
      setLoading(false);
    }

    fetchAll();

    // Realtime for live updates
    const channel = supabase
      .channel(`study-results-${studyId}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'studies', filter: `id=eq.${studyId}` },
        (payload) => { 
          if (payload.new) {
            setStudy(payload.new as Study);
          }
        }
      )
      .on('postgres_changes', { event: '*', schema: 'public', table: 'agent_sessions', filter: `study_id=eq.${studyId}` },
        (payload) => {
          if (payload.eventType === 'INSERT') setSessions(prev => [...prev, payload.new as AgentSession]);
          else if (payload.eventType === 'UPDATE') setSessions(prev => prev.map(s => s.id === (payload.new as AgentSession).id ? payload.new as AgentSession : s));
        }
      )
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [studyId, study?.status]);

  if (loading || !study) {
    return (
      <div className="page-enter">
        <div className="skeleton h-10 w-64 mb-4" />
        <div className="skeleton h-6 w-96 mb-8" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {[1,2,3,4].map(i => <div key={i} className="skeleton h-32 rounded-2xl" />)}
        </div>
        <div className="skeleton h-96 rounded-2xl" />
      </div>
    );
  }

  const statusConfig = STUDY_STATUS_CONFIG[study.status];
  const isRunning = ['analyzing_site', 'deploying', 'running', 'analyzing_results'].includes(study.status);
  const completedSessions = sessions.filter(s => s.status === 'completed');
  const failedSessions = sessions.filter(s => s.status === 'failed');

  // Aggregate findings
  const likes = findings.filter(f => f.type === 'like');
  const dislikes = findings.filter(f => f.type === 'dislike');
  const trustFindings = findings.filter(f => f.type === 'trust');
  const distrustFindings = findings.filter(f => f.type === 'distrust');

  const getPersonaForSession = (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId);
    return session ? personas.find(p => p.id === session.persona_id) : null;
  };

  return (
    <div className="page-enter">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold text-surface-900">
              {study.title || getDomainFromUrl(study.target_url)}
            </h1>
            <span className={statusConfig.badgeClass}>
              {isRunning && <Loader2 className="w-3 h-3 animate-spin" />}
              {statusConfig.label}
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm text-surface-400">
            <span className="flex items-center gap-1.5">
              <Globe className="w-4 h-4" />
              {study.target_url}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              {formatDate(study.created_at)}
            </span>
            <span className="flex items-center gap-1.5">
              <Users className="w-4 h-4" />
              {personas.length} personas
            </span>
          </div>
        </div>

        {failedSessions.length > 0 && (
          <button
            onClick={() => retryFailedSessions(studyId)}
            className="btn-secondary text-warning"
          >
            <RefreshCw className="w-4 h-4" />
            Retry {failedSessions.length} Failed
          </button>
        )}

        {isRunning && (
          <button
            onClick={async () => {
              if (confirm('Are you sure you want to cancel this study? All running sessions will be stopped.')) {
                setCancelling(true);
                try {
                  await cancelStudy(studyId);
                  setStudy(prev => prev ? { ...prev, status: 'failed' } : prev);
                  setSessions(prev => prev.map(s => ['queued', 'running'].includes(s.status) ? { ...s, status: 'failed' } : s));
                } catch (e) {
                  console.error('Failed to cancel:', e);
                } finally {
                  setCancelling(false);
                }
              }
            }}
            disabled={cancelling}
            className="btn-secondary text-error hover:bg-red-50"
            id="cancel-study-btn"
          >
            {cancelling ? <Loader2 className="w-4 h-4 animate-spin" /> : <StopCircle className="w-4 h-4" />}
            {cancelling ? 'Cancelling...' : 'Cancel Study'}
          </button>
        )}
      </div>

      {/* Running State: Progress */}
      {isRunning && (
        <div className="card p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Loader2 className="w-5 h-5 text-brand-500 animate-spin" />
            <h3 className="font-semibold text-surface-800">Study in progress</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {sessions.map((session) => {
              const persona = personas.find(p => p.id === session.persona_id);
              return (
                <Link 
                  key={session.id} 
                  href={`/studies/${studyId}/personas/${session.persona_id}`}
                  className="p-4 rounded-xl bg-surface-50 border border-surface-100 hover:border-brand-300 hover:bg-surface-100 transition-all cursor-pointer block"
                >
                  <div className="flex items-center gap-2.5 mb-2">
                    <div className="w-8 h-8 rounded-full gradient-bg flex items-center justify-center text-white text-xs font-bold">
                      {persona?.name.split(' ').map(n => n[0]).join('').slice(0, 2) || '??'}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-surface-800">{persona?.name || 'Unknown'}</p>
                      <p className="text-xs text-surface-400">{persona?.profession}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {session.status === 'completed' && <CheckCircle className="w-4 h-4 text-success" />}
                    {session.status === 'running' && <Loader2 className="w-4 h-4 text-brand-500 animate-spin" />}
                    {session.status === 'queued' && <Clock className="w-4 h-4 text-surface-400" />}
                    {session.status === 'failed' && <XCircle className="w-4 h-4 text-error" />}
                    <span className="text-xs text-surface-500 capitalize">{session.status}</span>
                    <span className="text-xs text-surface-400">• {session.step_count}/{session.step_budget} steps</span>
                  </div>
                  {/* Show error reason for failed sessions */}
                  {session.status === 'failed' && session.outcome_reason && (
                    <div className="mt-2 p-2 rounded-lg bg-red-50 border border-red-100">
                      <p className="text-xs text-red-600 font-medium">Error:</p>
                      <p className="text-xs text-red-500 mt-0.5 break-words whitespace-pre-wrap">
                        {session.outcome_reason.length > 300
                          ? session.outcome_reason.slice(0, 300) + '...'
                          : session.outcome_reason}
                      </p>
                    </div>
                  )}
                  <div className="mt-3">
                    <p className="text-[11px] text-surface-500 mb-1.5 truncate">
                      {session.current_phase || (session.status === 'queued' ? 'Waiting in queue...' : 'Initializing...')}
                    </p>
                    <div className="h-1.5 rounded-full bg-surface-200 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          session.status === 'queued' 
                            ? 'bg-surface-300 w-full opacity-50 animate-pulse' 
                            : 'bg-gradient-to-r from-brand-500 to-indigo-500'
                        }`}
                        style={{ 
                          width: session.status === 'queued' 
                            ? '100%' 
                            : `${Math.max(2, Math.min((session.step_count / session.step_budget) * 100, 100))}%` 
                        }}
                      />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Completed or Failed State: Metrics + Results */}
      {(study.status === 'completed' || study.status === 'failed') && (
        <>
          {/* Metric Cards */}
          {study.summary_metrics && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {study.summary_metrics.trust_score && (
                <div className="metric-card">
                  <div className="flex items-center gap-2 mb-3">
                    <Shield className="w-5 h-5 text-brand-500" />
                    <span className="text-xs font-medium text-surface-400 uppercase tracking-wider">Trust Score</span>
                  </div>
                  <p className="text-3xl font-bold text-surface-900">
                    {percentDisplay(study.summary_metrics.trust_score.value)}
                  </p>
                  <p className="text-xs text-surface-400 mt-1">
                    {(study.summary_metrics.trust_score as any).numerator != null
                      ? `${(study.summary_metrics.trust_score as any).numerator}/${(study.summary_metrics.trust_score as any).denominator} positive signals`
                      : (study.summary_metrics.trust_score as any).trust_count != null
                        ? `${(study.summary_metrics.trust_score as any).trust_count} trust / ${(study.summary_metrics.trust_score as any).distrust_count} distrust`
                        : 'Trust evaluation'}
                  </p>
                </div>
              )}
              {study.summary_metrics.task_completion_rate && (
                <div className="metric-card">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle className="w-5 h-5 text-success" />
                    <span className="text-xs font-medium text-surface-400 uppercase tracking-wider">Completion</span>
                  </div>
                  <p className="text-3xl font-bold text-surface-900">
                    {percentDisplay(study.summary_metrics.task_completion_rate.value)}
                  </p>
                  <p className="text-xs text-surface-400 mt-1">
                    {(study.summary_metrics.task_completion_rate as any).numerator != null
                      ? `${(study.summary_metrics.task_completion_rate as any).numerator}/${(study.summary_metrics.task_completion_rate as any).denominator} personas completed`
                      : (study.summary_metrics.task_completion_rate as any).completed != null
                        ? `${(study.summary_metrics.task_completion_rate as any).completed} / ${(study.summary_metrics.task_completion_rate as any).total} personas`
                        : 'Task completion'}
                  </p>
                </div>
              )}
              {study.summary_metrics.usability_score && (
                <div className="metric-card">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp className="w-5 h-5 text-info" />
                    <span className="text-xs font-medium text-surface-400 uppercase tracking-wider">Usability</span>
                  </div>
                  <p className="text-3xl font-bold text-surface-900">
                    {percentDisplay(study.summary_metrics.usability_score.value)}
                  </p>
                  <p className="text-xs text-surface-400 mt-1">
                    {(study.summary_metrics.usability_score as any).numerator != null
                      ? `${(study.summary_metrics.usability_score as any).numerator}/${(study.summary_metrics.usability_score as any).denominator} positive signals`
                      : (study.summary_metrics.usability_score as any).positive_count != null
                        ? `${(study.summary_metrics.usability_score as any).positive_count} positive / ${(study.summary_metrics.usability_score as any).negative_count} negative`
                        : 'Usability evaluation'}
                  </p>
                </div>
              )}
              {study.summary_metrics.value_prop_clarity && (
                <div className="metric-card">
                  <div className="flex items-center gap-2 mb-3">
                    <Lightbulb className="w-5 h-5 text-warning" />
                    <span className="text-xs font-medium text-surface-400 uppercase tracking-wider">Value Clarity</span>
                  </div>
                  <p className="text-3xl font-bold text-surface-900">
                    {percentDisplay(study.summary_metrics.value_prop_clarity.value)}
                  </p>
                  <p className="text-xs text-surface-400 mt-1">
                    Value proposition clarity score
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Tabs */}
          <div className="flex gap-1 mb-6 border-b border-surface-200">
            {[
              { id: 'overview' as const, label: 'Overview', icon: BarChart3 },
              { id: 'insights' as const, label: `Insights (${insights.length})`, icon: Lightbulb },
              { id: 'recommendations' as const, label: `Recommendations (${recommendations.length})`, icon: Target },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  activeTab === tab.id
                    ? 'border-brand-500 text-brand-600'
                    : 'border-transparent text-surface-400 hover:text-surface-600'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Key Findings */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Likes */}
                <div className="card p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <ThumbsUp className="w-5 h-5 text-success" />
                    <h3 className="font-semibold text-surface-800">What They Liked ({likes.length})</h3>
                  </div>
                  <div className="space-y-2.5">
                    {likes.slice(0, 5).map((f) => {
                      const persona = getPersonaForSession(f.session_id);
                      return (
                        <div key={f.id} className="p-3 rounded-lg bg-success-light/50 text-sm">
                          <p className="text-surface-700">{f.description}</p>
                          {persona && <p className="text-xs text-surface-400 mt-1">— {persona.name}</p>}
                        </div>
                      );
                    })}
                    {likes.length === 0 && <p className="text-sm text-surface-400">No likes recorded yet.</p>}
                  </div>
                </div>

                {/* Dislikes */}
                <div className="card p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <ThumbsDown className="w-5 h-5 text-error" />
                    <h3 className="font-semibold text-surface-800">What They Disliked ({dislikes.length})</h3>
                  </div>
                  <div className="space-y-2.5">
                    {dislikes.slice(0, 5).map((f) => {
                      const persona = getPersonaForSession(f.session_id);
                      return (
                        <div key={f.id} className="p-3 rounded-lg bg-error-light/50 text-sm">
                          <p className="text-surface-700">{f.description}</p>
                          {persona && <p className="text-xs text-surface-400 mt-1">— {persona.name}</p>}
                        </div>
                      );
                    })}
                    {dislikes.length === 0 && <p className="text-sm text-surface-400">No dislikes recorded yet.</p>}
                  </div>
                </div>
              </div>

              {/* Persona Cards */}
              <div>
                <h3 className="font-semibold text-surface-800 mb-4 flex items-center gap-2">
                  <Users className="w-5 h-5 text-brand-500" />
                  Persona Results
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {personas.map((persona) => {
                    const session = sessions.find(s => s.persona_id === persona.id);
                    const personaFindings = findings.filter(f => f.session_id === session?.id);
                    const personaLikes = personaFindings.filter(f => f.type === 'like').length;
                    const personaDislikes = personaFindings.filter(f => f.type === 'dislike').length;

                    return (
                      <Link
                        key={persona.id}
                        href={`/studies/${studyId}/personas/${persona.id}`}
                        className="card card-interactive p-5 group"
                      >
                        <div className="flex items-center gap-3 mb-3">
                          <div className="w-10 h-10 rounded-full gradient-bg flex items-center justify-center text-white font-bold text-sm">
                            {persona.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                          </div>
                          <div>
                            <p className="font-semibold text-surface-800 text-sm">{persona.name}</p>
                            <p className="text-xs text-surface-400">{persona.profession}</p>
                          </div>
                        </div>

                        {session && (
                          <div className="space-y-2 mb-3">
                            <div className="flex items-center gap-2">
                              {session.outcome === 'completed' && <CheckCircle className="w-4 h-4 text-success" />}
                              {session.outcome === 'abandoned' && <XCircle className="w-4 h-4 text-warning" />}
                              {session.outcome === 'error' && <AlertTriangle className="w-4 h-4 text-error" />}
                              <span className="text-sm text-surface-600 capitalize">{session.outcome || session.status}</span>
                            </div>
                            <div className="flex items-center gap-3 text-xs text-surface-400">
                              <span>{session.pages_visited} pages</span>
                              <span>{session.step_count} steps</span>
                              <span className="text-success">{personaLikes} 👍</span>
                              <span className="text-error">{personaDislikes} 👎</span>
                            </div>
                          </div>
                        )}

                        <div className="flex items-center justify-between pt-2 border-t border-surface-200 dark:border-surface-200 mt-2">
                          <span className="flex items-center gap-1 text-xs text-brand-600 dark:text-brand-400 font-semibold group-hover:translate-x-0.5 transition-transform">
                            Persona detail <ChevronRight className="w-3 h-3" />
                          </span>
                          <span className="text-[11px] font-mono text-surface-400">
                            Replay ready
                          </span>
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Insights Tab */}
          {activeTab === 'insights' && (
            <div className="space-y-3">
              {insights.map((insight) => (
                <div key={insight.id} className="card p-5">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center flex-shrink-0">
                      <Sparkles className="w-5 h-5 text-brand-600" />
                    </div>
                    <div className="flex-1">
                      <p className="text-surface-800 font-medium">{insight.statement}</p>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="badge badge-brand">
                          {insight.supporting_persona_count}/{insight.total_persona_count} personas
                        </span>
                        {insight.segment_filter && (
                          <span className="badge badge-info">{insight.segment_filter}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {insights.length === 0 && (
                <div className="card p-12 text-center">
                  <p className="text-surface-400">No cross-persona insights generated yet.</p>
                </div>
              )}
            </div>
          )}

          {/* Recommendations Tab */}
          {activeTab === 'recommendations' && (
            <div className="space-y-4">
              {recommendations.map((rec, i) => (
                <RecommendationCard key={rec.id} rec={rec} index={i} />
              ))}
              {recommendations.length === 0 && (
                <div className="card p-12 text-center">
                  <p className="text-surface-400">No recommendations generated yet.</p>
                </div>
              )}
              {recommendations.length > 0 && (
                <div className="text-center pt-4">
                  <Link href={`/studies/${studyId}/recommendations`} className="btn-secondary">
                    View All Recommendations
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Failed State - Move this up so it displays along with partial results */}
      {study.status === 'failed' && (
        <div className="card p-8 text-center bg-error-light/10 border-error/20 mb-8">
          <XCircle className="w-12 h-12 text-error mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-surface-800 mb-2">Study Failed</h3>
          <p className="text-surface-600 mb-4">{study.error_message || 'An error occurred during the study.'}</p>
          <button onClick={() => retryFailedSessions(studyId)} className="btn-primary mx-auto">
            <RefreshCw className="w-4 h-4" />
            Retry Failed Sessions
          </button>
        </div>
      )}
    </div>
  );
}

function RecommendationCard({ rec, index }: { rec: Recommendation; index: number }) {
  const supabase = createClient();
  const [status, setStatus] = useState(rec.status);

  const handleStatusChange = async (newStatus: Recommendation['status']) => {
    setStatus(newStatus);
    await supabase.from('recommendations').update({ status: newStatus }).eq('id', rec.id);
    track('recommendation_status_changed', { recommendation_id: rec.id, status: newStatus });
  };

  const priorityLabel = rec.priority_score >= 0.7 ? 'High' : rec.priority_score >= 0.4 ? 'Medium' : 'Low';
  const priorityBadge = rec.priority_score >= 0.7 ? 'badge-error' : rec.priority_score >= 0.4 ? 'badge-warning' : 'badge-info';

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center text-white text-sm font-bold">
            {index + 1}
          </div>
          <span className={`badge ${priorityBadge}`}>{priorityLabel} Impact</span>
        </div>
        <div className="flex gap-1">
          {(['useful', 'not_relevant', 'already_fixed'] as const).map((s) => (
            <button
              key={s}
              onClick={() => handleStatusChange(s)}
              className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-colors ${
                status === s
                  ? 'bg-brand-50 text-brand-700 border border-brand-200'
                  : 'text-surface-400 hover:text-surface-600 hover:bg-surface-50'
              }`}
            >
              {s === 'useful' ? '👍 Useful' : s === 'not_relevant' ? '🚫 Not Relevant' : '✅ Fixed'}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3 text-sm">
        <div>
          <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Problem</p>
          <p className="text-surface-800 font-medium">{rec.problem}</p>
        </div>
        <div>
          <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Evidence</p>
          <p className="text-surface-600">{rec.evidence}</p>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Affected Users</p>
            <p className="text-surface-600">{rec.affected_users}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-1">Why It Matters</p>
            <p className="text-surface-600">{rec.why_it_matters}</p>
          </div>
        </div>
        <div className="p-3 rounded-xl bg-success-light/50 border border-success/20">
          <p className="text-xs font-semibold text-success uppercase tracking-wider mb-1">Suggested Improvement</p>
          <p className="text-surface-700 font-medium">{rec.suggested_improvement}</p>
        </div>
      </div>
    </div>
  );
}
