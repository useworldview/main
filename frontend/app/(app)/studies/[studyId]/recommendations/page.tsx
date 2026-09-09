'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import { type Recommendation } from '@/lib/types';
import { track } from '@/lib/analytics';
import {
  ArrowLeft, ChevronRight, Target, Filter, SortDesc
} from 'lucide-react';

export default function RecommendationsPage() {
  const params = useParams();
  const studyId = params.studyId as string;
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    const supabase = createClient();
    async function fetch() {
      const { data } = await supabase
        .from('recommendations')
        .select('*')
        .eq('study_id', studyId)
        .order('priority_score', { ascending: false });
      if (data) setRecommendations(data as Recommendation[]);
      setLoading(false);
    }
    fetch();
  }, [studyId]);

  const handleStatusChange = async (recId: string, status: Recommendation['status']) => {
    const supabase = createClient();
    await supabase.from('recommendations').update({ status }).eq('id', recId);
    setRecommendations(prev => prev.map(r => r.id === recId ? { ...r, status } : r));
    track('recommendation_status_changed', { recommendation_id: recId, status });
  };

  const filtered = filter === 'all' ? recommendations : recommendations.filter(r => r.status === filter);

  if (loading) {
    return (
      <div className="page-enter max-w-4xl mx-auto">
        <div className="skeleton h-8 w-48 mb-8" />
        {[1,2,3].map(i => <div key={i} className="skeleton h-48 rounded-2xl mb-4" />)}
      </div>
    );
  }

  return (
    <div className="page-enter max-w-4xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-surface-400 mb-6">
        <Link href={`/studies/${studyId}`} className="hover:text-brand-600 transition-colors flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" />
          Study Results
        </Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-surface-700 font-medium">Recommendations</span>
      </div>

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Recommendations</h1>
          <p className="text-surface-500 mt-1">{recommendations.length} recommendations, prioritized by impact</p>
        </div>

        {/* Filter */}
        <div className="flex gap-1 bg-surface-100 rounded-xl p-1">
          {['all', 'new', 'useful', 'not_relevant', 'already_fixed'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors capitalize ${
                filter === f
                  ? 'bg-surface-0 text-surface-800 shadow-sm'
                  : 'text-surface-400 hover:text-surface-600'
              }`}
            >
              {f.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        {filtered.map((rec, i) => {
          const priorityLabel = rec.priority_score >= 0.7 ? 'High' : rec.priority_score >= 0.4 ? 'Medium' : 'Low';
          const priorityBadge = rec.priority_score >= 0.7 ? 'badge-error' : rec.priority_score >= 0.4 ? 'badge-warning' : 'badge-info';

          return (
            <div key={rec.id} className="card p-6 animate-fade-in" style={{ animationDelay: `${i * 0.05}s` }}>
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center text-white text-sm font-bold">
                    {i + 1}
                  </div>
                  <span className={`badge ${priorityBadge}`}>{priorityLabel} Impact</span>
                  {rec.status !== 'new' && (
                    <span className={`badge ${
                      rec.status === 'useful' ? 'badge-success' :
                      rec.status === 'already_fixed' ? 'badge-info' : 'badge'
                    } capitalize`}>
                      {rec.status.replace(/_/g, ' ')}
                    </span>
                  )}
                </div>
                <div className="flex gap-1">
                  {(['useful', 'not_relevant', 'already_fixed'] as const).map((s) => (
                    <button
                      key={s}
                      onClick={() => handleStatusChange(rec.id, s)}
                      className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-colors ${
                        rec.status === s
                          ? 'bg-brand-50 text-brand-700 border border-brand-200'
                          : 'text-surface-400 hover:text-surface-600 hover:bg-surface-50'
                      }`}
                    >
                      {s === 'useful' ? '👍 Useful' : s === 'not_relevant' ? '🚫 Skip' : '✅ Fixed'}
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
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
        })}

        {filtered.length === 0 && (
          <div className="card p-12 text-center">
            <Target className="w-10 h-10 text-surface-300 mx-auto mb-3" />
            <p className="text-surface-400">No recommendations match this filter.</p>
          </div>
        )}
      </div>
    </div>
  );
}
