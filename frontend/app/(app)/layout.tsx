'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { createClient } from '@/lib/supabase/client';
import {
  Eye, Sun, Moon, LogOut, Settings, ChevronDown,
  LayoutDashboard, User, Plus, Compass, Sparkles, Activity
} from 'lucide-react';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [user, setUser] = useState<{ email?: string; id?: string } | null>(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const supabase = createClient();

    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user) {
        setUser({ email: user.email, id: user.id });
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setUser({ email: session.user.email, id: session.user.id });
      } else {
        setUser(null);
        router.push('/sign-in');
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push('/sign-in');
    router.refresh();
  };

  const userInitials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : 'U';

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-950 flex flex-col text-surface-800">
      {/* Top Navigation */}
      <header className="sticky top-0 z-40 glass border-b border-surface-200 dark:border-surface-200 backdrop-blur-xl">
        <div className="max-w-[1440px] mx-auto px-6 h-16 flex items-center justify-between">
          {/* Left: Logo + Breadcrumbs + Nav */}
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-xl gradient-bg flex items-center justify-center shadow-sm group-hover:shadow-glow transition-all">
                <Eye className="w-4.5 h-4.5 text-white" />
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="font-bold text-surface-900 hidden sm:inline text-base">
                  Use<span className="gradient-text">Worldview</span>
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-100 dark:bg-surface-100 text-surface-500 font-medium hidden md:inline">
                  STUDIO
                </span>
              </div>
            </Link>

            <div className="hidden sm:block h-4 w-px bg-surface-200 dark:bg-surface-200" />

            <nav className="flex items-center gap-1">
              <Link
                href="/dashboard"
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all ${
                  pathname === '/dashboard' || pathname.startsWith('/studies')
                    ? 'bg-brand-50 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300 border border-brand-200/50 dark:border-brand-800/40 shadow-sm'
                    : 'text-surface-600 hover:text-surface-900 hover:bg-surface-100 dark:hover:bg-surface-100'
                }`}
              >
                <LayoutDashboard className="w-4 h-4" />
                Dashboard
              </Link>
            </nav>
          </div>

          {/* Right: Engine status + Theme toggle + User menu */}
          <div className="flex items-center gap-3">
            {/* Live Engine Status indicator */}
            <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-full bg-surface-100/80 dark:bg-surface-100/60 border border-surface-200 dark:border-surface-200 text-[11px] font-mono text-surface-600 dark:text-surface-300">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Engine Ready</span>
            </div>

            <Link
              href="/studies/new"
              className="btn-primary text-xs py-1.5 px-3.5 shadow-sm"
              id="global-create-study-btn"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Study</span>
            </Link>

            {/* Theme toggle */}
            {mounted && (
              <button
                onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                className="p-2 rounded-xl hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors text-surface-600 dark:text-surface-300 border border-transparent hover:border-surface-200"
                aria-label="Toggle theme"
              >
                {theme === 'light' ? (
                  <Moon className="w-4.5 h-4.5" />
                ) : (
                  <Sun className="w-4.5 h-4.5" />
                )}
              </button>
            )}

            {/* User menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 p-1 pl-1.5 pr-2.5 rounded-xl hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors border border-surface-200 dark:border-surface-200"
                aria-label="User profile menu"
              >
                <div className="w-7 h-7 rounded-lg gradient-bg flex items-center justify-center text-white text-xs font-bold shadow-sm">
                  {userInitials}
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-surface-400" />
              </button>

              {showUserMenu && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowUserMenu(false)}
                  />
                  <div className="absolute right-0 top-full mt-2 w-64 card p-2 shadow-elevated z-50 animate-scale-in origin-top-right border border-surface-200 dark:border-surface-200">
                    <div className="px-3 py-2 mb-1">
                      <p className="text-xs text-surface-400 font-mono uppercase">Signed In As</p>
                      <p className="text-sm font-semibold text-surface-900 truncate">{user?.email}</p>
                      <span className="inline-block mt-1 badge badge-brand text-[10px]">Cloud Run Pro</span>
                    </div>
                    <hr className="border-surface-200 dark:border-surface-200 my-1" />
                    <Link
                      href="/settings"
                      className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
                      onClick={() => setShowUserMenu(false)}
                    >
                      <Settings className="w-4 h-4 text-surface-500" />
                      Settings & Keys
                    </Link>
                    <button
                      onClick={handleSignOut}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-error hover:bg-error-light transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      Sign Out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1">
        <div className="max-w-[1440px] mx-auto px-6 py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
