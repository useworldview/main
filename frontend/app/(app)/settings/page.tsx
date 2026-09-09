'use client';

import { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { createClient } from '@/lib/supabase/client';
import { track } from '@/lib/analytics';
import {
  Sun, Moon, User, Mail, Trash2, Loader2, AlertTriangle
} from 'lucide-react';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [email, setEmail] = useState('');
  const [saving, setSaving] = useState(false);
  const [studies, setStudies] = useState<{ id: string; title: string | null; target_url: string }[]>([]);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    const supabase = createClient();

    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user) setEmail(user.email || '');
    });

    supabase.from('studies').select('id, title, target_url').order('created_at', { ascending: false }).then(({ data }) => {
      if (data) setStudies(data);
    });
  }, []);

  const handleThemeChange = async (newTheme: string) => {
    setTheme(newTheme);
    track('theme_toggled', { theme: newTheme });

    // Persist to profile
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      await supabase
        .from('profiles')
        .update({ theme_preference: newTheme })
        .eq('id', user.id);
    }
  };

  const handleDeleteStudy = async (studyId: string) => {
    setDeleting(studyId);
    const supabase = createClient();

    // Delete from Supabase (cascades to all child rows)
    await supabase.from('studies').delete().eq('id', studyId);

    // Also purge storage (best-effort)
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.access_token) {
        await fetch(`${backendUrl}/api/studies/${studyId}/purge-storage`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${session.access_token}` },
        }).catch(() => {}); // Best effort
      }
    } catch {}

    setStudies(prev => prev.filter(s => s.id !== studyId));
    setDeleteConfirm(null);
    setDeleting(null);
  };

  return (
    <div className="page-enter max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-surface-900 mb-8">Settings</h1>

      {/* Account Info */}
      <div className="card p-6 mb-6">
        <h2 className="font-semibold text-surface-800 mb-4 flex items-center gap-2">
          <User className="w-5 h-5 text-brand-500" />
          Account
        </h2>
        <div className="flex items-center gap-3">
          <Mail className="w-4 h-4 text-surface-400" />
          <span className="text-sm text-surface-600">{email}</span>
        </div>
      </div>

      {/* Theme Preference */}
      {mounted && (
        <div className="card p-6 mb-6">
          <h2 className="font-semibold text-surface-800 mb-4 flex items-center gap-2">
            {theme === 'light' ? <Sun className="w-5 h-5 text-warning" /> : <Moon className="w-5 h-5 text-brand-500" />}
            Appearance
          </h2>
          <div className="flex gap-3">
            <button
              onClick={() => handleThemeChange('light')}
              className={`flex-1 p-4 rounded-xl border-2 transition-all flex items-center gap-3 ${
                theme === 'light'
                  ? 'border-brand-500 bg-brand-50'
                  : 'border-surface-200 hover:border-surface-300'
              }`}
            >
              <Sun className="w-5 h-5 text-warning" />
              <div>
                <p className="text-sm font-medium text-surface-800">Light</p>
                <p className="text-xs text-surface-400">Clean and bright</p>
              </div>
            </button>
            <button
              onClick={() => handleThemeChange('dark')}
              className={`flex-1 p-4 rounded-xl border-2 transition-all flex items-center gap-3 ${
                theme === 'dark'
                  ? 'border-brand-500 bg-brand-50'
                  : 'border-surface-200 hover:border-surface-300'
              }`}
            >
              <Moon className="w-5 h-5 text-brand-500" />
              <div>
                <p className="text-sm font-medium text-surface-800">Dark</p>
                <p className="text-xs text-surface-400">Easy on the eyes</p>
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Study Management */}
      {studies.length > 0 && (
        <div className="card p-6">
          <h2 className="font-semibold text-surface-800 mb-4 flex items-center gap-2">
            <Trash2 className="w-5 h-5 text-error" />
            Manage Studies
          </h2>
          <p className="text-sm text-surface-400 mb-4">
            Deleting a study removes all associated data including personas, sessions, findings, and screenshots.
          </p>
          <div className="space-y-2">
            {studies.map((study) => (
              <div key={study.id} className="flex items-center justify-between p-3 rounded-xl hover:bg-surface-50 transition-colors">
                <div>
                  <p className="text-sm font-medium text-surface-700">
                    {study.title || new URL(study.target_url).hostname}
                  </p>
                  <p className="text-xs text-surface-400">{study.target_url}</p>
                </div>
                {deleteConfirm === study.id ? (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-error font-medium">Delete?</span>
                    <button
                      onClick={() => handleDeleteStudy(study.id)}
                      disabled={deleting === study.id}
                      className="text-xs px-3 py-1.5 rounded-lg bg-error text-white hover:bg-error/90 disabled:opacity-50"
                    >
                      {deleting === study.id ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Confirm'}
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="text-xs px-3 py-1.5 rounded-lg text-surface-500 hover:bg-surface-100"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setDeleteConfirm(study.id)}
                    className="p-2 rounded-lg text-surface-400 hover:text-error hover:bg-error-light transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
