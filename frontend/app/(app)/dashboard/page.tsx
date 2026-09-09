'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { Plus, Globe, Clock, Users, ArrowRight, Loader2, Search, Sparkles } from 'lucide-react';
import { type Study, STUDY_STATUS_CONFIG } from '@/lib/types';
import { formatRelativeTime, getDomainFromUrl } from '@/lib/utils';
import { track } from '@/lib/analytics';

export default function DashboardPage() {
  const [studies, setStudies] = useState<Study[]>([]);
  const [loading, setLoading] = useState(true);

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

  if (loading) {
    return (
      <div className="page-enter">
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="skeleton h-8 w-48 mb-2" />
            <div className="skeleton h-5 w-72" />
          </div>
          <div className="skeleton h-11 w-40 rounded-xl" />
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
    <div className="page-enter">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Studies</h1>
          <p className="text-surface-500 mt-1">
            {studies.length > 0
              ? `${studies.length} ${studies.length === 1 ? 'study' : 'studies'} created`
              : 'Deploy AI personas into your product to get real insights'
            }
          </p>
        </div>
        <Link href="/studies/new" className="btn-primary" id="create-study-btn">
          <Plus className="w-4 h-4" />
          Create New Study
        </Link>
      </div>

      {/* Empty State */}
      {studies.length === 0 ? (
        <div className="card p-12 md:p-16 text-center max-w-2xl mx-auto">
          <div className="w-20 h-20 rounded-3xl bg-brand-50 flex items-center justify-center mx-auto mb-6">
            <Sparkles className="w-10 h-10 text-brand-500" />
          </div>
          <h2 className="text-xl font-bold text-surface-900 mb-2">
            Your first study is waiting
          </h2>
          <p className="text-surface-500 mb-8 max-w-md mx-auto leading-relaxed">
            Submit a URL, define a research goal, and let AI personas explore your product. 
            You&apos;ll get evidence-backed insights in minutes.
          </p>
          <Link href="/studies/new" className="btn-primary text-base px-8 py-3">
            <Plus className="w-5 h-5" />
            Create Your First Study
          </Link>

          <div className="mt-10 grid grid-cols-3 gap-6 max-w-sm mx-auto">
            <div className="text-center">
              <p className="text-2xl font-bold gradient-text">&lt;15m</p>
              <p className="text-xs text-surface-400 mt-1">To insights</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold gradient-text">3-10</p>
              <p className="text-xs text-surface-400 mt-1">AI personas</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold gradient-text">100%</p>
              <p className="text-xs text-surface-400 mt-1">Traceable</p>
            </div>
          </div>
        </div>
      ) : (
        /* Study Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {studies.map((study) => {
            const statusConfig = STUDY_STATUS_CONFIG[study.status];
            const isRunning = ['analyzing_site', 'deploying', 'running', 'analyzing_results'].includes(study.status);

            return (
              <Link
                key={study.id}
                href={
                  study.status === 'draft' || study.status === 'audience_ready' || study.status === 'personas_ready'
                    ? `/studies/new?studyId=${study.id}`
                    : `/studies/${study.id}`
                }
                className="card card-interactive p-5 group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-9 h-9 rounded-xl bg-surface-100 flex items-center justify-center group-hover:bg-brand-50 transition-colors">
                      <Globe className="w-4.5 h-4.5 text-surface-500 group-hover:text-brand-600 transition-colors" />
                    </div>
                    <div>
                      <p className="font-semibold text-surface-800 text-sm truncate max-w-[180px]">
                        {study.title || getDomainFromUrl(study.target_url)}
                      </p>
                      <p className="text-xs text-surface-400 truncate max-w-[180px]">
                        {getDomainFromUrl(study.target_url)}
                      </p>
                    </div>
                  </div>
                  <span className={statusConfig.badgeClass}>
                    {isRunning && <Loader2 className="w-3 h-3 animate-spin" />}
                    {statusConfig.label}
                  </span>
                </div>

                {/* Research goals */}
                {study.research_goals && study.research_goals.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {study.research_goals.slice(0, 3).map((goal, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded-md bg-surface-100 text-surface-500 capitalize">
                        {goal.value.replace(/_/g, ' ')}
                      </span>
                    ))}
                    {study.research_goals.length > 3 && (
                      <span className="text-xs text-surface-400">+{study.research_goals.length - 3} more</span>
                    )}
                  </div>
                )}

                {/* Summary metrics (if completed) */}
                {study.status === 'completed' && study.summary_metrics && (
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    {study.summary_metrics.trust_score && (
                      <div className="text-center p-2 rounded-lg bg-surface-50">
                        <p className="text-lg font-bold text-surface-800">
                          {Math.round(study.summary_metrics.trust_score.value * 100)}%
                        </p>
                        <p className="text-xs text-surface-400">Trust</p>
                      </div>
                    )}
                    {study.summary_metrics.task_completion_rate && (
                      <div className="text-center p-2 rounded-lg bg-surface-50">
                        <p className="text-lg font-bold text-surface-800">
                          {Math.round(study.summary_metrics.task_completion_rate.value * 100)}%
                        </p>
                        <p className="text-xs text-surface-400">Completion</p>
                      </div>
                    )}
                    {study.summary_metrics.usability_score && (
                      <div className="text-center p-2 rounded-lg bg-surface-50">
                        <p className="text-lg font-bold text-surface-800">
                          {Math.round(study.summary_metrics.usability_score.value * 100)}%
                        </p>
                        <p className="text-xs text-surface-400">Usability</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Footer */}
                <div className="flex items-center justify-between text-xs text-surface-400 pt-3 border-t border-surface-100">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatRelativeTime(study.created_at)}
                  </span>
                  <span className="flex items-center gap-1 text-brand-500 opacity-0 group-hover:opacity-100 transition-opacity">
                    View <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
