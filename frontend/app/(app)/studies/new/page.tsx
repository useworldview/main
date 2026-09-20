'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { createStudy, generatePersonas, deployStudy } from '@/lib/api';
import { RESEARCH_GOAL_TEMPLATES, type AudienceSegment, type Persona, type ResearchGoal } from '@/lib/types';
import { track } from '@/lib/analytics';
import {
  ArrowRight, ArrowLeft, Check, Globe, Target, Users, Brain,
  Rocket, Loader2, Plus, Trash2, Edit3, RefreshCw, AlertCircle,
  CheckCircle, X, Sparkles, Shield
} from 'lucide-react';

const STEPS = [
  { label: 'Research Goal', icon: Target },
  { label: 'Target URL', icon: Globe },
  { label: 'Audience', icon: Users },
  { label: 'Personas', icon: Brain },
  { label: 'Deploy', icon: Rocket },
];

export default function StudyWizardPage() {
  return (
    <Suspense fallback={
      <div className="page-enter max-w-4xl mx-auto">
        <div className="skeleton h-10 w-full mb-10 rounded-xl" />
        <div className="skeleton h-8 w-64 mb-4" />
        <div className="skeleton h-6 w-96 mb-8" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {[1,2,3,4,5,6].map(i => <div key={i} className="skeleton h-24 rounded-xl" />)}
        </div>
      </div>
    }>
      <StudyWizardInner />
    </Suspense>
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

function StudyWizardInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const existingStudyId = searchParams.get('studyId');

  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Step 1: Research Goals
  const [selectedGoals, setSelectedGoals] = useState<string[]>([]);
  const [customGoal, setCustomGoal] = useState('');

  // Step 2: URL
  const [targetUrl, setTargetUrl] = useState('');
  const [confirmedAuthorized, setConfirmedAuthorized] = useState(false);
  const [urlValidated, setUrlValidated] = useState(false);

  // Step 3: Audience Segments
  const [studyId, setStudyId] = useState<string | null>(existingStudyId);
  const [segments, setSegments] = useState<AudienceSegment[]>([]);
  const [waitingForSegments, setWaitingForSegments] = useState(false);
  const [newSegmentName, setNewSegmentName] = useState('');

  // Step 4: Personas
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [waitingForPersonas, setWaitingForPersonas] = useState(false);
  const [personasPerSegment, setPersonasPerSegment] = useState(1);

  // Step 5: Deploy
  const [deploying, setDeploying] = useState(false);

  // Load existing study data if resuming
  useEffect(() => {
    if (existingStudyId) {
      const supabase = createClient();

      async function loadStudy() {
        const { data: study } = await supabase
          .from('studies')
          .select('*')
          .eq('id', existingStudyId)
          .single();

        if (study) {
          setStudyId(study.id);
          setTargetUrl(study.target_url);
          if (study.research_goals) {
            const goals = study.research_goals as ResearchGoal[];
            setSelectedGoals(goals.filter(g => g.type === 'template').map(g => g.value));
            const custom = goals.find(g => g.type === 'custom');
            if (custom) setCustomGoal(custom.value);
          }

          // Set step based on status
          switch (study.status) {
            case 'audience_ready':
              setCurrentStep(2);
              break;
            case 'personas_ready':
              setCurrentStep(3);
              break;
            default:
              setCurrentStep(0);
          }
        }

        // Load segments
        const { data: segs } = await supabase
          .from('audience_segments')
          .select('*')
          .eq('study_id', existingStudyId);
        if (segs) setSegments(segs as AudienceSegment[]);

        // Load personas
        const { data: pers } = await supabase
          .from('personas')
          .select('*')
          .eq('study_id', existingStudyId);
        if (pers) setPersonas(pers as Persona[]);
      }

      loadStudy();
    }
  }, [existingStudyId]);

  // Realtime subscription + polling fallback for study status changes
  useEffect(() => {
    if (!studyId) return;
    const supabase = createClient();

    const checkStatus = async () => {
      try {
        const { data: study } = await supabase
          .from('studies')
          .select('*')
          .eq('id', studyId)
          .single();

        if (!study) return;

        if (study.status === 'audience_ready' || study.status === 'personas_ready' || study.status === 'running' || study.status === 'completed') {
          setWaitingForSegments(false);
          const { data: segs } = await supabase
            .from('audience_segments')
            .select('*')
            .eq('study_id', studyId);
          if (segs && segs.length > 0) {
            setSegments(segs as AudienceSegment[]);
          }
        }

        if (study.status === 'personas_ready' || study.status === 'running' || study.status === 'completed') {
          setWaitingForPersonas(false);
          const { data: pers } = await supabase
            .from('personas')
            .select('*')
            .eq('study_id', studyId);
          if (pers && pers.length > 0) {
            setPersonas(pers as Persona[]);
          }
        }

        if (study.status === 'failed') {
          setError(study.error_message || 'Something went wrong during analysis');
          setLoading(false);
          setWaitingForSegments(false);
          setWaitingForPersonas(false);
        }
      } catch (err) {
        console.error('Status check error:', err);
      }
    };

    // Check immediately upon studyId change
    checkStatus();

    // Poll every 2.5 seconds while waiting
    const interval = setInterval(checkStatus, 2500);

    const channel = supabase
      .channel(`study-${studyId}`)
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'studies', filter: `id=eq.${studyId}` },
        (payload) => {
          const study = payload.new;
          if (study.status === 'audience_ready') {
            setWaitingForSegments(false);
            supabase.from('audience_segments').select('*').eq('study_id', studyId).then(({ data }) => {
              if (data && data.length > 0) setSegments(data as AudienceSegment[]);
            });
          }
          if (study.status === 'personas_ready') {
            setWaitingForPersonas(false);
            supabase.from('personas').select('*').eq('study_id', studyId).then(({ data }) => {
              if (data && data.length > 0) setPersonas(data as Persona[]);
            });
          }
          if (study.status === 'failed') {
            setError(study.error_message || 'Something went wrong');
            setLoading(false);
            setWaitingForSegments(false);
            setWaitingForPersonas(false);
          }
        }
      )
      .subscribe();

    return () => {
      clearInterval(interval);
      supabase.removeChannel(channel);
    };
  }, [studyId]);

  // ─── Step Handlers ───

  const handleStep1Next = () => {
    if (selectedGoals.length === 0 && !customGoal.trim()) {
      setError('Please select at least one research goal or enter a custom goal.');
      return;
    }
    setError('');
    track('study_wizard_step_completed', { step: 1 });
    setCurrentStep(1);
  };

  const handleStep2Next = async () => {
    if (!targetUrl.trim()) {
      setError('Please enter a URL.');
      return;
    }
    if (!confirmedAuthorized) {
      setError('Please confirm you have permission to test this site.');
      return;
    }

    setError('');
    setLoading(true);

    try {
      // Validate URL format
      let url = targetUrl.trim();
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'https://' + url;
        setTargetUrl(url);
      }
      new URL(url);

      // Create study via backend
      const goals: { type: 'template' | 'custom'; value: string }[] = [
        ...selectedGoals.map(g => ({ type: 'template' as const, value: g })),
        ...(customGoal.trim() ? [{ type: 'custom' as const, value: customGoal.trim() }] : []),
      ];

      const study = await createStudy({
        target_url: url,
        research_goals: goals,
        confirmed_authorized: confirmedAuthorized,
      });

      setStudyId(study.id);
      setWaitingForSegments(true);
      track('study_wizard_step_completed', { step: 2 });
      setCurrentStep(2);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create study');
    } finally {
      setLoading(false);
    }
  };

  const handleAddSegment = async () => {
    if (!newSegmentName.trim() || !studyId) return;
    const supabase = createClient();
    const { data, error } = await supabase
      .from('audience_segments')
      .insert({ study_id: studyId, name: newSegmentName.trim(), source: 'manual', description: '' })
      .select()
      .single();

    if (!error && data) {
      setSegments(prev => [...prev, data as AudienceSegment]);
      setNewSegmentName('');
    }
  };

  const handleRemoveSegment = async (segmentId: string) => {
    const supabase = createClient();
    await supabase.from('audience_segments').delete().eq('id', segmentId);
    setSegments(prev => prev.filter(s => s.id !== segmentId));
  };

  const handleStep3Next = async () => {
    if (segments.length === 0) {
      setError('You need at least one audience segment.');
      return;
    }
    setError('');
    setLoading(true);

    try {
      await generatePersonas(studyId!, {
        segment_ids: segments.map(s => s.id),
        personas_per_segment: personasPerSegment,
      });
      setWaitingForPersonas(true);
      track('study_wizard_step_completed', { step: 3 });
      setCurrentStep(3);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate personas');
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePersona = async (personaId: string) => {
    const supabase = createClient();
    await supabase.from('personas').delete().eq('id', personaId);
    setPersonas(prev => prev.filter(p => p.id !== personaId));
  };

  const handleStep4Next = () => {
    if (personas.length === 0) {
      setError('You need at least one persona.');
      return;
    }
    setError('');
    track('study_wizard_step_completed', { step: 4 });
    setCurrentStep(4);
  };

  const handleDeploy = async () => {
    setDeploying(true);
    setError('');

    try {
      await deployStudy(studyId!);
      track('study_wizard_step_completed', { step: 5 });
      track('persona_deployed', { study_id: studyId, persona_count: personas.length });
      router.push(`/studies/${studyId}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to deploy study');
      setDeploying(false);
    }
  };

  return (
    <div className="page-enter max-w-4xl mx-auto">
      {/* Step Indicator */}
      <div className="mb-10">
        <div className="flex items-center justify-between mb-2">
          {STEPS.map((step, i) => (
            <div key={step.label} className="flex items-center flex-1 last:flex-initial">
              <div className="flex flex-col items-center">
                <div
                  className={`step-dot ${
                    i < currentStep ? 'completed' : i === currentStep ? 'active' : 'pending'
                  }`}
                >
                  {i < currentStep ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <step.icon className="w-4 h-4" />
                  )}
                </div>
                <span className={`text-xs mt-2 font-medium hidden sm:block ${
                  i === currentStep ? 'text-brand-600' : i < currentStep ? 'text-success' : 'text-surface-400'
                }`}>
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`step-line mx-2 ${i < currentStep ? 'completed' : ''}`} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-error-light border border-error/20 flex items-start gap-3 animate-slide-down">
          <AlertCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-error font-medium">{error}</p>
          </div>
          <button onClick={() => setError('')} className="ml-auto text-error/50 hover:text-error">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ─── Step 1: Research Goal ─── */}
      {currentStep === 0 && (
        <div className="animate-fade-in">
          <h2 className="text-2xl font-bold text-surface-900 mb-2">What do you want to learn?</h2>
          <p className="text-surface-500 mb-8">Select one or more research goals, or describe your own.</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-8">
            {RESEARCH_GOAL_TEMPLATES.map((goal) => {
              const isSelected = selectedGoals.includes(goal.value);
              return (
                <button
                  key={goal.value}
                  onClick={() => {
                    setSelectedGoals(prev =>
                      isSelected ? prev.filter(g => g !== goal.value) : [...prev, goal.value]
                    );
                  }}
                  className={`text-left p-4 rounded-xl border-2 transition-all ${
                    isSelected
                      ? 'border-brand-500 bg-brand-50/80 dark:bg-brand-950/50 dark:border-brand-500 shadow-sm ring-1 ring-brand-400/40'
                      : 'border-surface-200 dark:border-surface-200 hover:border-brand-300 dark:hover:border-brand-800 hover:bg-surface-50 dark:hover:bg-surface-100'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-xl">{goal.icon}</span>
                    <div>
                      <p className={`font-semibold text-sm ${isSelected ? 'text-brand-700 dark:text-brand-300' : 'text-surface-800 dark:text-surface-200'}`}>
                        {goal.label}
                      </p>
                      <p className="text-xs text-surface-500 mt-0.5">{goal.description}</p>
                    </div>
                    {isSelected && (
                      <CheckCircle className="w-5 h-5 text-brand-500 ml-auto flex-shrink-0" />
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Custom goal */}
          <div className="mb-8">
            <label className="block text-sm font-medium text-surface-700 mb-2">
              Or describe a custom research goal
            </label>
            <textarea
              value={customGoal}
              onChange={(e) => setCustomGoal(e.target.value)}
              className="input min-h-[100px] resize-y"
              placeholder="e.g., I want to understand why first-time visitors don't sign up for my SaaS product..."
            />
          </div>

          <div className="flex justify-end">
            <button onClick={handleStep1Next} className="btn-primary">
              Continue
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ─── Step 2: Target URL ─── */}
      {currentStep === 1 && (
        <div className="animate-fade-in">
          <h2 className="text-2xl font-bold text-surface-900 mb-2">Enter your website URL</h2>
          <p className="text-surface-500 mb-8">The URL where AI personas will start exploring your product.</p>

          <div className="card p-6 mb-6">
            <label className="block text-sm font-medium text-surface-700 mb-2">
              Website URL
            </label>
            <div className="relative mb-4">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
              <input
                type="url"
                value={targetUrl}
                onChange={(e) => { setTargetUrl(e.target.value); setUrlValidated(false); }}
                className="input pl-11 text-base py-3"
                placeholder="https://your-product.com"
              />
            </div>

            {/* Consent checkbox */}
            <label className="flex items-start gap-3 cursor-pointer group">
              <div className="mt-0.5">
                <input
                  type="checkbox"
                  checked={confirmedAuthorized}
                  onChange={(e) => setConfirmedAuthorized(e.target.checked)}
                  className="w-4 h-4 rounded border-surface-300 text-brand-600 focus:ring-brand-500"
                />
              </div>
              <div>
                <p className="text-sm text-surface-700 font-medium group-hover:text-surface-900 transition-colors">
                  I confirm I own this site or have permission to run automated testing against it
                </p>
                <p className="text-xs text-surface-400 mt-0.5">
                  Required per our Terms of Service. AI personas will interact with your public-facing pages.
                </p>
              </div>
            </label>
          </div>

          <div className="flex justify-between">
            <button onClick={() => setCurrentStep(0)} className="btn-ghost">
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>
            <button
              onClick={handleStep2Next}
              disabled={loading || !targetUrl.trim() || !confirmedAuthorized}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  Analyze Site
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ─── Step 3: Audience Segments ─── */}
      {currentStep === 2 && (
        <div className="animate-fade-in">
          <h2 className="text-2xl font-bold text-surface-900 mb-2">Target Audience</h2>
          <p className="text-surface-500 mb-8">
            {waitingForSegments
              ? 'Analyzing your site to detect the target audience...'
              : 'Review the detected audience segments. Add, edit, or remove as needed.'
            }
          </p>

          {waitingForSegments ? (
            <div className="card p-12 text-center">
              <Loader2 className="w-10 h-10 text-brand-500 animate-spin mx-auto mb-4" />
              <p className="text-surface-600 font-medium">Analyzing your site...</p>
              <p className="text-sm text-surface-400 mt-1">This usually takes 30–60 seconds.</p>
            </div>
          ) : (
            <>
              <div className="space-y-3 mb-6">
                {segments.map((segment) => (
                  <div key={segment.id} className="card p-4 flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center flex-shrink-0">
                      <Users className="w-5 h-5 text-brand-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-surface-800 text-sm">{segment.name}</p>
                      {segment.description && (
                        <p className="text-xs text-surface-400 mt-0.5 truncate">{segment.description}</p>
                      )}
                    </div>
                    <span className={`badge ${segment.source === 'detected' ? 'badge-info' : segment.source === 'manual' ? 'badge-brand' : 'badge-warning'}`}>
                      {segment.source}
                    </span>
                    <button
                      onClick={() => handleRemoveSegment(segment.id)}
                      className="p-2 rounded-lg hover:bg-error-light text-surface-400 hover:text-error transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Add segment */}
              <div className="flex gap-2 mb-8">
                <input
                  type="text"
                  value={newSegmentName}
                  onChange={(e) => setNewSegmentName(e.target.value)}
                  className="input flex-1"
                  placeholder="Add a custom audience segment..."
                  onKeyDown={(e) => e.key === 'Enter' && handleAddSegment()}
                />
                <button
                  onClick={handleAddSegment}
                  disabled={!newSegmentName.trim()}
                  className="btn-secondary disabled:opacity-50"
                >
                  <Plus className="w-4 h-4" />
                  Add
                </button>
              </div>

              <div className="flex justify-between">
                <button onClick={() => setCurrentStep(1)} className="btn-ghost">
                  <ArrowLeft className="w-4 h-4" />
                  Back
                </button>
                <button
                  onClick={handleStep3Next}
                  disabled={loading || segments.length === 0}
                  className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      Generate Personas
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ─── Step 4: Personas ─── */}
      {currentStep === 3 && (
        <div className="animate-fade-in">
          <h2 className="text-2xl font-bold text-surface-900 mb-2">AI Personas</h2>
          <p className="text-surface-500 mb-8">
            {waitingForPersonas
              ? 'Generating personas with complete worldviews...'
              : 'Review your AI personas. Each has a unique worldview that shapes how they experience your product.'
            }
          </p>

          {waitingForPersonas ? (
            <div className="card p-12 text-center">
              <Brain className="w-10 h-10 text-brand-500 mx-auto mb-4 animate-pulse" />
              <p className="text-surface-600 font-medium">Building persona worldviews...</p>
              <p className="text-sm text-surface-400 mt-1">Creating realistic, internally consistent personalities.</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                {personas.map((persona) => (
                  <div key={persona.id} className="card p-5">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-11 h-11 rounded-full gradient-bg flex items-center justify-center text-white font-bold text-sm">
                          {persona.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                        </div>
                        <div>
                          <p className="font-semibold text-surface-800">{persona.name}</p>
                          <p className="text-xs text-surface-400">
                            {persona.age && `${persona.age} • `}
                            {persona.profession || 'Unknown role'}
                            {persona.location && ` • ${persona.location}`}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeletePersona(persona.id)}
                        className="p-1.5 rounded-lg hover:bg-error-light text-surface-400 hover:text-error transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Worldview summary */}
                    <div className="space-y-2 text-xs">
                      {persona.worldview?.trust_level && (
                        <div className="flex items-center gap-2">
                          <Shield className="w-3.5 h-3.5 text-surface-400 flex-shrink-0" />
                          <span className="text-surface-500">Trust: <strong className="text-surface-700">{formatTraitValue(persona.worldview.trust_level)}</strong></span>
                        </div>
                      )}
                      {persona.worldview?.digital_literacy && (
                        <div className="flex items-center gap-2">
                          <Sparkles className="w-3.5 h-3.5 text-surface-400 flex-shrink-0" />
                          <span className="text-surface-500">Digital literacy: <strong className="text-surface-700">{formatTraitValue(persona.worldview.digital_literacy)}</strong></span>
                        </div>
                      )}
                      {persona.worldview?.price_sensitivity && (
                        <div className="flex items-center gap-2">
                          <Target className="w-3.5 h-3.5 text-surface-400 flex-shrink-0" />
                          <span className="text-surface-500">Price sensitivity: <strong className="text-surface-700">{formatTraitValue(persona.worldview.price_sensitivity)}</strong></span>
                        </div>
                      )}
                      {persona.situational_context?.reason_for_visiting && (
                        <p className="text-surface-500 mt-2 italic border-l-2 border-brand-200 pl-3 py-1">
                          &quot;{typeof persona.situational_context.reason_for_visiting === 'object' ? formatTraitValue(persona.situational_context.reason_for_visiting) : String(persona.situational_context.reason_for_visiting)}&quot;
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex justify-between">
                <button onClick={() => setCurrentStep(2)} className="btn-ghost">
                  <ArrowLeft className="w-4 h-4" />
                  Back
                </button>
                <button
                  onClick={handleStep4Next}
                  disabled={personas.length === 0}
                  className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Review & Deploy
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ─── Step 5: Review & Deploy ─── */}
      {currentStep === 4 && (
        <div className="animate-fade-in">
          <h2 className="text-2xl font-bold text-surface-900 mb-2">Review & Deploy</h2>
          <p className="text-surface-500 mb-8">Everything looks good? Let&apos;s deploy your AI personas.</p>

          <div className="space-y-4 mb-8">
            {/* Summary card */}
            <div className="card p-6">
              <h3 className="font-semibold text-surface-800 mb-4">Study Summary</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-surface-400 uppercase tracking-wider mb-1">Target URL</p>
                  <p className="text-sm text-surface-700 font-medium break-all">{targetUrl}</p>
                </div>
                <div>
                  <p className="text-xs text-surface-400 uppercase tracking-wider mb-1">Research Goals</p>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedGoals.map(g => (
                      <span key={g} className="badge badge-brand capitalize">{g.replace(/_/g, ' ')}</span>
                    ))}
                    {customGoal && <span className="badge badge-info">Custom goal</span>}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-surface-400 uppercase tracking-wider mb-1">Audience Segments</p>
                  <p className="text-sm text-surface-700">{segments.length} segments</p>
                </div>
                <div>
                  <p className="text-xs text-surface-400 uppercase tracking-wider mb-1">AI Personas</p>
                  <p className="text-sm text-surface-700">{personas.length} personas will explore your site</p>
                </div>
              </div>
            </div>

            {/* Persona list */}
            <div className="card p-6">
              <h3 className="font-semibold text-surface-800 mb-4">Deploying {personas.length} Personas</h3>
              <div className="space-y-2">
                {personas.map((p) => (
                  <div key={p.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-50 transition-colors">
                    <div className="w-8 h-8 rounded-full gradient-bg flex items-center justify-center text-white text-xs font-bold">
                      {p.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-surface-800">{p.name}</p>
                      <p className="text-xs text-surface-400">{p.profession} • {p.location}</p>
                    </div>
                    <CheckCircle className="w-4 h-4 text-success" />
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="flex justify-between">
            <button onClick={() => setCurrentStep(3)} className="btn-ghost">
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>
            <button
              onClick={handleDeploy}
              disabled={deploying}
              className="btn-primary text-base px-8 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {deploying ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Deploying...
                </>
              ) : (
                <>
                  <Rocket className="w-5 h-5" />
                  Deploy AI Personas
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
