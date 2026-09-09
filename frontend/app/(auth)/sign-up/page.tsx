'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Eye, ArrowRight, Mail, Lock, User, Loader2 } from 'lucide-react';

export default function SignUpPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleEmailSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const supabase = createClient();
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      setError(error.message);
      setLoading(false);
    } else {
      setSuccess(true);
      setLoading(false);
    }
  };

  const handleGoogleSignUp = async () => {
    const supabase = createClient();
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
  };

  return (
    <div className="min-h-screen flex gradient-bg-subtle">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-1/2 items-center justify-center p-12 relative overflow-hidden">
        <div className="absolute inset-0 gradient-bg opacity-5" />
        <div className="absolute top-1/4 right-1/4 w-96 h-96 rounded-full bg-brand-200/20 blur-3xl" />
        <div className="absolute bottom-1/3 left-1/3 w-72 h-72 rounded-full bg-indigo-200/20 blur-3xl" />

        <div className="relative max-w-md text-center">
          <div className="w-16 h-16 rounded-2xl gradient-bg flex items-center justify-center mx-auto mb-8 shadow-lg">
            <Eye className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-surface-900 mb-4">
            Start understanding your<br />
            <span className="gradient-text">users today</span>
          </h2>
          <p className="text-surface-500 leading-relaxed">
            Deploy AI personas into your product. Get evidence-backed insights in minutes, not weeks.
          </p>

          <div className="mt-10 grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold gradient-text">&lt; 15m</p>
              <p className="text-xs text-surface-400 mt-1">Time to first insight</p>
            </div>
            <div>
              <p className="text-2xl font-bold gradient-text">20+</p>
              <p className="text-xs text-surface-400 mt-1">Persona attributes</p>
            </div>
            <div>
              <p className="text-2xl font-bold gradient-text">100%</p>
              <p className="text-xs text-surface-400 mt-1">Evidence-backed</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center gap-2.5 mb-10">
            <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center shadow-md">
              <Eye className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl text-surface-800">
              Use<span className="gradient-text">Worldview</span>
            </span>
          </div>

          {success ? (
            <div className="text-center animate-scale-in">
              <div className="w-16 h-16 rounded-2xl bg-success-light flex items-center justify-center mx-auto mb-6">
                <Mail className="w-8 h-8 text-success" />
              </div>
              <h1 className="text-2xl font-bold text-surface-900 mb-2">Check your email</h1>
              <p className="text-surface-500 mb-6">
                We&apos;ve sent a confirmation link to <strong>{email}</strong>. Click it to activate your account.
              </p>
              <Link href="/sign-in" className="btn-secondary">
                Back to Sign In
              </Link>
            </div>
          ) : (
            <>
              <h1 className="text-2xl font-bold text-surface-900 mb-1">Create your account</h1>
              <p className="text-surface-500 mb-8">
                Already have an account?{' '}
                <Link href="/sign-in" className="text-brand-600 font-medium hover:text-brand-700 transition-colors">
                  Sign in
                </Link>
              </p>

              {/* Google OAuth */}
              <button
                onClick={handleGoogleSignUp}
                className="w-full btn-secondary py-3 mb-6"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Continue with Google
              </button>

              {/* Divider */}
              <div className="flex items-center gap-3 mb-6">
                <div className="flex-1 h-px bg-surface-200" />
                <span className="text-xs text-surface-400 font-medium">or sign up with email</span>
                <div className="flex-1 h-px bg-surface-200" />
              </div>

              {/* Email/Password form */}
              <form onSubmit={handleEmailSignUp} className="space-y-4">
                {error && (
                  <div className="p-3 rounded-xl bg-error-light text-error text-sm font-medium animate-slide-down">
                    {error}
                  </div>
                )}

                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-surface-700 mb-1.5">
                    Email
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
                    <input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="input pl-10"
                      placeholder="you@company.com"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-surface-700 mb-1.5">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
                    <input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="input pl-10"
                      placeholder="Minimum 6 characters"
                      required
                      minLength={6}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      Create Account
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>

              <p className="text-xs text-surface-400 text-center mt-6">
                By creating an account, you agree to our Terms of Service and Privacy Policy.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
