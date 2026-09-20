'use client';

import Link from 'next/link';
import { useEffect, useState, useMemo } from 'react';
import { createClient } from '@/lib/supabase/client';
import {
  Plus, Globe, Clock, Users, ArrowRight, Loader2, Search, Sparkles,
  StopCircle, Activity, BarChart3, CheckCircle2, AlertTriangle,
  Compass, ArrowUpRight, Filter, ShieldCheck, RefreshCw
} from 'lucide-react';
import { type Study, STUDY_STATUS_CONFIG } from '@/lib/types';
import { formatRelativeTime, getDomainFromUrl } from '@/lib/utils';
import { cancelStudy } from '@/lib/api';
import { track } from '@/lib/analytics';

export default function DashboardPage() {
  const [studies, setStudies] = useState<Study[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'running' | 'completed' | 'draft'>('all');
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  useEffect(() => {
    track('dashboard_viewed');
    const supabase = createClient();

    async function fetchStudies() {
      const { data, error } = await supabase
        .from('studies')
        .select('*')
        .order('created_at', { ascending: false });

      if (!error && data) {
        setStudies(data as Study[]);
      }
      setLoading(false);
    }

    fetchStudies();

    // Realtime subscription for study status updates
    const channel = supabase
      .channel('studies-changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'studies' },
        (payload) => {
          if (payload.eventType === 'INSERT') {
            setStudies(prev => [payload.new as Study, ...prev]);
          } else if (payload.eventType === 'UPDATE') {
            setStudies(prev => prev.map(s => s.id === (payload.new as Study).id ? payload.new as Study : s));
          } else if (payload.eventType === 'DELETE') {
            setStudies(prev => prev.filter(s => s.id !== (payload.old as Study).id));
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const handleCancelStudy = async (e: React.MouseEvent, studyId: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Are you sure you want to halt this study run?')) return;
    setCancellingId(studyId);
    try {
      await cancelStudy(studyId);
      setStudies(prev => prev.map(s => s.id === studyId ? { ...s, status: 'failed' as const } : s));
    } catch (err) {
      console.error('Failed to cancel study', err);
    } finally {
      setCancellingId(null);
    }
  };

  // Filtered studies
  const filteredStudies = useMemo(() => {
    return studies.filter(study => {
      const goalsText = Array.isArray(study.research_goals)
        ? study.research_goals.map(g => (typeof g === 'object' && g ? g.value : String(g))).join(' ')
        : '';
      const matchesSearch =
        study.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        study.target_url?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        goalsText.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      const isRunning = ['analyzing_site', 'deploying', 'running', 'analyzing_results'].includes(study.status);
      if (statusFilter === 'running') return isRunning;
      if (statusFilter === 'completed') return study.status === 'completed';
      if (statusFilter === 'draft') return ['draft', 'audience_ready', 'personas_ready'].includes(study.status);

      return true;
    });
  }, [studies, searchQuery, statusFilter]);

  // Executive Metrics
  const metrics = useMemo(() => {
    const total = studies.length;
    const completed = studies.filter(s => s.status === 'completed').length;
    const running = studies.filter(s => ['analyzing_site', 'deploying', 'running', 'analyzing_results'].includes(s.status)).length;
    return { total, completed, running };
  }, [studies]);

  if (loading) {
    return (
      <div className="page-enter space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <div className="skeleton h-8 w-48 mb-2" />
            <div className="skeleton h-5 w-72" />
          </div>
          <div className="skeleton h-11 w-40 rounded-xl" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton h-24 rounded-2xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton h-48 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="page-enter space-y-8">
      {/* ─── Executive Header ─── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-extrabold text-surface-900 tracking-tight">Studies & Telemetry</h1>
            <span className="badge badge-brand text-[11px] font-mono">Mission Control</span>
          </div>
          <p className="text-sm text-surface-500">
            Monitor autonomous AI persona traversals, sentiment friction, and evidence reports.
          </p>
        </div>
        <Link href="/studies/new" className="btn-primary shadow-elevated" id="create-study-btn">
          <Plus className="w-4 h-4" />
          <span>Launch New Study</span>
        </Link>
      </div>

      {/* ─── Executive KPI Cards ─── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="metric-card p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-surface-400">Total Studies</span>
            <div className="w-8 h-8 rounded-lg bg-surface-100 dark:bg-surface-100 flex items-center justify-center text-surface-600">
              <BarChart3 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black font-mono text-surface-900">{metrics.total}</p>
          <p className="text-xs text-surface-400 mt-1">Research campaigns configured</p>
        </div>

        <div className="metric-card p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-surface-400">Active Autonomous Runs</span>
            <div className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-950 flex items-center justify-center text-brand-600">
              <Activity className="w-4 h-4 animate-pulse" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <p className="text-2xl font-black font-mono text-brand-600 dark:text-brand-400">{metrics.running}</p>
            {metrics.running > 0 && (
              <span className="text-xs text-brand-600 font-medium animate-pulse">Running live</span>
            )}
          </div>
          <p className="text-xs text-surface-400 mt-1">Personas actively exploring sites</p>
        </div>

        <div className="metric-card p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-surface-400">Completed Reports</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 flex items-center justify-center text-emerald-600">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black font-mono text-surface-900">{metrics.completed}</p>
          <p className="text-xs text-surface-400 mt-1">Full evidence packages available</p>
        </div>
      </div>

      {/* ─── Search & Filter Toolbar ─── */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-surface-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by study name, target domain, or goal..."
            className="input pl-10 text-xs sm:text-sm py-2"
          />
        </div>

        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-surface-100 dark:bg-surface-100 border border-surface-200 dark:border-surface-200 text-xs font-semibold">
          {[
            { id: 'all', label: 'All' },
            { id: 'running', label: 'Active Runs' },
            { id: 'completed', label: 'Completed' },
            { id: 'draft', label: 'Drafts' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id as any)}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                statusFilter === tab.id
                  ? 'bg-surface-0 dark:bg-surface-0 text-surface-900 shadow-sm'
                  : 'text-surface-500 hover:text-surface-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ─── Studies Grid or Empty State ─── */}
      {filteredStudies.length === 0 ? (
        studies.length === 0 ? (
          /* Zero-state on initial setup */
          <div className="card p-12 md:p-16 text-center max-w-2xl mx-auto border-dashed border-2 border-brand-200 dark:border-brand-900/60">
            <div className="w-16 h-16 rounded-3xl bg-brand-50 dark:bg-brand-950 flex items-center justify-center mx-auto mb-6 shadow-glow">
              <Sparkles className="w-8 h-8 text-brand-600" />
            </div>
            <h2 className="text-xl font-bold text-surface-900 mb-2">
              Deploy your first synthetic user study
            </h2>
            <p className="text-surface-500 text-sm mb-8 max-w-md mx-auto leading-relaxed">
              Submit your target URL and define a goal. AI personas will navigate your live product, run end-to-end sessions, and report actionable evidence.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link href="/studies/new" className="btn-primary text-sm px-6 py-3 shadow-md">
                <Plus className="w-4 h-4" />
                Create First Study
              </Link>
            </div>
          </div>
        ) : (
          /* Filtered empty state */
          <div className="card p-12 text-center max-w-md mx-auto">
            <Search className="w-8 h-8 text-surface-400 mx-auto mb-3" />
            <h3 className="text-base font-bold text-surface-800 mb-1">No matching studies found</h3>
            <p className="text-xs text-surface-500 mb-4">Try clearing your search query or changing filters.</p>
            <button
              onClick={() => { setSearchQuery(''); setStatusFilter('all'); }}
              className="btn-secondary text-xs py-1.5 px-4"
            >
              Reset Filters
            </button>
          </div>
        )
      ) : (
        /* Studies Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredStudies.map((study) => {
            const statusConfig = STUDY_STATUS_CONFIG[study.status];
            const isRunning = ['analyzing_site', 'deploying', 'running', 'analyzing_results'].includes(study.status);
            const domain = study.target_url ? getDomainFromUrl(study.target_url) : 'Draft';

            return (
              <Link
                key={study.id}
                href={
                  study.status === 'draft' || study.status === 'audience_ready' || study.status === 'personas_ready'
                    ? `/studies/new?studyId=${study.id}`
                    : `/studies/${study.id}`
                }
                className={`card spotlight-card p-5 group flex flex-col justify-between ${
                  isRunning ? 'border-brand-400 dark:border-brand-600/70 shadow-glow' : ''
                }`}
              >
                <div>
                  {/* Top Bar: Target & Status */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-xl bg-surface-100 dark:bg-surface-100 flex items-center justify-center text-surface-600 group-hover:text-brand-600 transition-colors">
                        <Globe className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-xs font-mono font-semibold text-surface-500">{domain}</p>
                        <h3 className="font-bold text-sm text-surface-900 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors line-clamp-1">
                          {study.title || 'Untitled Research Study'}
                        </h3>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className={`badge ${statusConfig?.badgeClass || 'badge-brand'} text-[10px]`}>
                        {isRunning && <Loader2 className="w-3 h-3 animate-spin mr-1" />}
                        {statusConfig?.label || study.status}
                      </span>
                    </div>
                  </div>

                  {/* Research Goal summary */}
                  <p className="text-xs text-surface-600 dark:text-surface-400 line-clamp-2 mb-4 leading-relaxed">
                    {Array.isArray(study.research_goals) && study.research_goals.length > 0
                      ? study.research_goals.map(g => (typeof g === 'object' && g ? g.value : String(g))).join(', ')
                      : 'General exploratory usability test'}
                  </p>
                </div>

                {/* Card Footer: Metadata & Actions */}
                <div>
                  {/* Running animation bar if active */}
                  {isRunning && (
                    <div className="mb-3">
                      <div className="flex items-center justify-between text-[11px] font-mono text-brand-600 dark:text-brand-400 mb-1">
                        <span className="flex items-center gap-1">
                          <Activity className="w-3 h-3 animate-pulse" /> Exploring pages...
                        </span>
                        <button
                          onClick={(e) => handleCancelStudy(e, study.id)}
                          disabled={cancellingId === study.id}
                          className="text-[10px] text-error hover:underline flex items-center gap-1"
                        >
                          <StopCircle className="w-3 h-3" /> Stop
                        </button>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-surface-100 dark:bg-surface-100 overflow-hidden">
                        <div className="h-full rounded-full bg-brand-500 animate-shimmer" style={{ width: '65%' }} />
                      </div>
                    </div>
                  )}

                  <div className="pt-3 border-t border-surface-200 dark:border-surface-200 flex items-center justify-between text-xs text-surface-400 font-mono">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {study.created_at ? formatRelativeTime(study.created_at) : 'recently'}
                    </span>
                    <span className="flex items-center gap-1 font-semibold text-surface-600 dark:text-surface-300 group-hover:text-brand-600 transition-colors">
                      View Report <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
