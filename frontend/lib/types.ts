// UseWorldview TypeScript types — mirrors the Supabase DB schema

export interface Profile {
  id: string;
  email: string;
  theme_preference: 'light' | 'dark';
  created_at: string;
}

export interface Study {
  id: string;
  user_id: string;
  title: string | null;
  research_goals: ResearchGoal[];
  target_url: string;
  status: StudyStatus;
  step_budget_per_session: number;
  max_pages: number;
  site_context: Record<string, unknown> | null;
  summary_metrics: SummaryMetrics | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export type StudyStatus =
  | 'draft'
  | 'analyzing_site'
  | 'audience_ready'
  | 'personas_ready'
  | 'deploying'
  | 'running'
  | 'analyzing_results'
  | 'completed'
  | 'failed';

export interface ResearchGoal {
  type: 'template' | 'custom';
  value: string;
}

export interface SummaryMetrics {
  trust_score?: { value: number; trust_count: number; distrust_count: number };
  value_prop_clarity?: { value: number; clear_count: number; unclear_count: number };
  usability_score?: { value: number; positive_count: number; negative_count: number };
  task_completion_rate?: { value: number; completed: number; total: number };
  conversion_intent?: { value: number; converted: number; total: number };
  overall_sentiment?: string;
}

export interface AudienceSegment {
  id: string;
  study_id: string;
  name: string;
  description: string | null;
  source: 'detected' | 'edited' | 'manual';
  created_at: string;
}

export interface Persona {
  id: string;
  study_id: string;
  audience_segment_id: string | null;
  name: string;
  age: number | null;
  location: string | null;
  profession: string | null;
  education: string | null;
  income_level: string | null;
  worldview: PersonaWorldview;
  situational_context: PersonaSituationalContext;
  status: 'draft' | 'active' | 'archived';
  created_at: string;
}

export interface PersonaWorldview {
  technical_ability?: string;
  digital_literacy?: string;
  goals?: string[];
  motivations?: string[];
  prior_experience?: string;
  personality_traits?: string[];
  habits?: string[];
  preferences?: string[];
  fears?: string[];
  frustrations?: string[];
  expectations?: string[];
  trust_level?: string;
  price_sensitivity?: string;
  decision_making_style?: string;
  risk_tolerance?: string;
  attention_span?: string;
  patience_level?: string;
  familiarity_with_similar_products?: string;
}

export interface PersonaSituationalContext {
  current_situation?: string;
  reason_for_visiting?: string;
  objective?: string;
  influences?: string[];
}

export interface AgentSession {
  id: string;
  study_id: string;
  persona_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'aborted';
  start_time: string | null;
  end_time: string | null;
  step_count: number;
  step_budget: number;
  outcome: 'completed' | 'abandoned' | 'error' | null;
  outcome_reason: string | null;
  pages_visited: number;
  created_at: string;
  // Joined fields
  persona?: Persona;
}

export interface InteractionEvent {
  id: string;
  session_id: string;
  sequence_no: number;
  event_type: 'click' | 'scroll' | 'type' | 'navigate' | 'search' | 'back' | 'forward' | 'wait' | 'screenshot' | 'form_submit' | 'page_error' | 'dead_end';
  target_element: string | null;
  page_url: string | null;
  details: Record<string, unknown>;
  screenshot_ref: string | null;
  occurred_at: string;
}

export interface Finding {
  id: string;
  session_id: string;
  type: 'like' | 'dislike' | 'feeling' | 'trust' | 'distrust';
  feeling_label: FeelingLabel | null;
  description: string;
  linked_event_ids: string[];
  created_at: string;
}

export type FeelingLabel =
  | 'confused'
  | 'interested'
  | 'excited'
  | 'frustrated'
  | 'suspicious'
  | 'confident'
  | 'overwhelmed'
  | 'curious'
  | 'uncertain'
  | 'satisfied';

export interface DecisionExplanation {
  id: string;
  session_id: string;
  decision_type: 'signup' | 'purchase' | 'feature_use' | 'abandon' | 'other';
  rationale_text: string;
  linked_event_ids: string[];
  created_at: string;
}

export interface CrossPersonaInsight {
  id: string;
  study_id: string;
  statement: string;
  supporting_persona_count: number;
  total_persona_count: number;
  segment_filter: string | null;
  created_at: string;
}

export interface Recommendation {
  id: string;
  study_id: string;
  problem: string;
  evidence: string;
  affected_users: string;
  why_it_matters: string;
  suggested_improvement: string;
  priority_score: number;
  status: 'new' | 'useful' | 'not_relevant' | 'already_fixed';
  created_at: string;
}

// ─── Research goal templates ───
export const RESEARCH_GOAL_TEMPLATES = [
  { value: 'trust', label: 'Trust & Credibility', icon: '🛡️', description: 'How much do users trust your product?' },
  { value: 'value_proposition', label: 'Value Proposition', icon: '💎', description: 'Is your value proposition clear and compelling?' },
  { value: 'first_impression', label: 'First Impression', icon: '👀', description: 'What do users think within seconds of landing?' },
  { value: 'usability', label: 'Usability', icon: '🎯', description: 'Can users accomplish tasks easily?' },
  { value: 'navigation', label: 'Navigation', icon: '🧭', description: 'Can users find what they need?' },
  { value: 'onboarding', label: 'Onboarding', icon: '🚀', description: 'How smooth is the getting-started experience?' },
  { value: 'feature_discoverability', label: 'Feature Discoverability', icon: '🔍', description: 'Can users find and understand key features?' },
  { value: 'pricing_perception', label: 'Pricing Perception', icon: '💰', description: 'How do users perceive your pricing?' },
  { value: 'conversion_experience', label: 'Conversion Experience', icon: '📈', description: 'What stops or convinces users to convert?' },
  { value: 'purchase_intent', label: 'Purchase Intent', icon: '🛒', description: 'Would users actually buy this?' },
  { value: 'signup_experience', label: 'Signup Experience', icon: '📝', description: 'How frictionless is the signup flow?' },
  { value: 'overall_experience', label: 'Overall Experience', icon: '✨', description: 'End-to-end product experience evaluation' },
  { value: 'specific_journey', label: 'Specific User Journey', icon: '🗺️', description: 'Test a specific path through your product' },
] as const;

// ─── Feeling colors/icons ───
export const FEELING_CONFIG: Record<FeelingLabel, { color: string; emoji: string }> = {
  confused: { color: '#f59e0b', emoji: '😕' },
  interested: { color: '#3b82f6', emoji: '🤔' },
  excited: { color: '#10b981', emoji: '🤩' },
  frustrated: { color: '#ef4444', emoji: '😤' },
  suspicious: { color: '#f97316', emoji: '🤨' },
  confident: { color: '#22c55e', emoji: '😊' },
  overwhelmed: { color: '#a855f7', emoji: '😰' },
  curious: { color: '#6366f1', emoji: '🧐' },
  uncertain: { color: '#eab308', emoji: '🤷' },
  satisfied: { color: '#14b8a6', emoji: '😌' },
};

// ─── Study status display config ───
export const STUDY_STATUS_CONFIG: Record<StudyStatus, { label: string; color: string; badgeClass: string }> = {
  draft: { label: 'Draft', color: '#94a3b8', badgeClass: 'badge' },
  analyzing_site: { label: 'Analyzing Site', color: '#3b82f6', badgeClass: 'badge badge-info' },
  audience_ready: { label: 'Audience Ready', color: '#8b5cf6', badgeClass: 'badge badge-brand' },
  personas_ready: { label: 'Personas Ready', color: '#8b5cf6', badgeClass: 'badge badge-brand' },
  deploying: { label: 'Deploying', color: '#f59e0b', badgeClass: 'badge badge-warning' },
  running: { label: 'Running', color: '#f59e0b', badgeClass: 'badge badge-warning' },
  analyzing_results: { label: 'Analyzing', color: '#3b82f6', badgeClass: 'badge badge-info' },
  completed: { label: 'Completed', color: '#10b981', badgeClass: 'badge badge-success' },
  failed: { label: 'Failed', color: '#ef4444', badgeClass: 'badge badge-error' },
};
