import { createClient } from '@/lib/supabase/client';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

async function getAuthHeaders() {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new Error('Not authenticated');
  }
  return {
    'Authorization': `Bearer ${session.access_token}`,
    'Content-Type': 'application/json',
  };
}

// ─── The 4 backend action calls ───

export async function createStudy(data: {
  target_url: string;
  research_goals: { type: 'template' | 'custom'; value: string }[];
  confirmed_authorized?: boolean;
}) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/studies`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to create study' }));
    throw new Error(error.detail || 'Failed to create study');
  }
  return res.json();
}

export async function generatePersonas(studyId: string, data: {
  segment_ids: string[];
  personas_per_segment?: number;
}) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/studies/${studyId}/personas/generate`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to generate personas' }));
    throw new Error(error.detail || 'Failed to generate personas');
  }
  return res.json();
}

export async function regeneratePersona(personaId: string) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/personas/${personaId}/regenerate`, {
    method: 'POST',
    headers,
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to regenerate persona' }));
    throw new Error(error.detail || 'Failed to regenerate persona');
  }
  return res.json();
}

export async function deployStudy(studyId: string) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/studies/${studyId}/deploy`, {
    method: 'POST',
    headers,
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to deploy study' }));
    throw new Error(error.detail || 'Failed to deploy study');
  }
  return res.json();
}

export async function retryFailedSessions(studyId: string) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/studies/${studyId}/retry-failed-sessions`, {
    method: 'POST',
    headers,
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to retry sessions' }));
    throw new Error(error.detail || 'Failed to retry sessions');
  }
  return res.json();
}

export async function cancelStudy(studyId: string) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BACKEND_URL}/api/studies/${studyId}/cancel`, {
    method: 'POST',
    headers,
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to cancel study' }));
    throw new Error(error.detail || 'Failed to cancel study');
  }
  return res.json();
}
