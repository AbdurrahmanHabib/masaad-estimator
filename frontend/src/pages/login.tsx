import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '../store/useAuthStore';
import { Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type Tab = 'login' | 'register';

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated } = useAuthStore();

  const [tab, setTab] = useState<Tab>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace('/');
    }
  }, [isAuthenticated, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch(`${BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail || data?.message || 'Invalid credentials. Please try again.');
      }

      const data = await res.json();
      const token: string = data.access_token ?? data.token;
      const user = data.user ?? {
        user_id: data.user_id,
        email: data.email,
        role: data.role,
        tenant_id: data.tenant_id,
        full_name: data.full_name,
      };

      if (!token) throw new Error('No authentication token received from server.');

      login(token, user);
      router.replace('/');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      const res = await fetch(`${BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail || data?.message || 'Registration failed. Please try again.');
      }

      setSuccess('Account created successfully. Please log in.');
      setTab('login');
      setPassword('');
      setFullName('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#002147] flex items-center justify-center px-4">
      {/* Background grid decoration */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative w-full max-w-md">
        {/* Card */}
        <div className="bg-white rounded-md shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="bg-[#002147] px-10 pt-10 pb-8 flex flex-col items-center gap-4">
            <img
              src="/logo.png"
              alt="Madinat Al Saada Logo"
              className="w-16 h-16 object-contain"
            />
            <div className="text-center">
              <h1 className="text-base font-bold text-[#d4a017] uppercase tracking-wider">
                Madinat Al Saada
              </h1>
              <p className="text-[10px] text-white/70 font-medium uppercase tracking-[0.25em] mt-0.5">
                Aluminium & Glass Works
              </p>
            </div>

            {/* Tabs */}
            <div className="flex w-full mt-2 bg-[#1e3a5f]/60 rounded-md p-1 gap-1">
              <button
                onClick={() => { setTab('login'); setError(null); setSuccess(null); }}
                className={`flex-1 py-2 text-[11px] font-bold uppercase tracking-widest rounded-md transition-all ${
                  tab === 'login'
                    ? 'bg-[#d4a017] text-[#002147]'
                    : 'text-white/60 hover:text-white'
                }`}
              >
                Sign In
              </button>
              <button
                onClick={() => { setTab('register'); setError(null); setSuccess(null); }}
                className={`flex-1 py-2 text-[11px] font-bold uppercase tracking-widest rounded-md transition-all ${
                  tab === 'register'
                    ? 'bg-[#d4a017] text-[#002147]'
                    : 'text-white/60 hover:text-white'
                }`}
              >
                Register
              </button>
            </div>
          </div>

          {/* Form Body */}
          <div className="px-10 py-8">
            {/* Success banner */}
            {success && (
              <div className="mb-6 flex items-center gap-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-md px-4 py-3 text-xs font-semibold">
                <span>{success}</span>
              </div>
            )}

            {/* Error banner */}
            {error && (
              <div className="mb-6 flex items-start gap-3 bg-red-50 border border-red-200 text-red-700 rounded-md px-4 py-3 text-xs font-semibold">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {tab === 'login' ? (
              <form onSubmit={handleLogin} className="space-y-5">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-[#64748b] mb-2">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    placeholder="you@example.com"
                    className="w-full bg-slate-50 border border-[#e2e8f0] rounded-md py-3 px-4 text-sm font-medium text-[#1e293b] focus:ring-2 focus:ring-[#d4a017]/30 focus:border-[#002147] transition-all outline-none placeholder:text-slate-300"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-[#64748b] mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      autoComplete="current-password"
                      placeholder="--------"
                      className="w-full bg-slate-50 border border-[#e2e8f0] rounded-md py-3 px-4 pr-12 text-sm font-medium text-[#1e293b] focus:ring-2 focus:ring-[#d4a017]/30 focus:border-[#002147] transition-all outline-none placeholder:text-slate-300"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-[#64748b] hover:text-[#1e293b] transition-colors"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-[#002147] hover:bg-[#1e3a5f] disabled:bg-slate-300 text-white py-3.5 rounded-md text-xs font-bold uppercase tracking-widest transition-all flex items-center justify-center gap-2 mt-2"
                >
                  {loading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      Authenticating...
                    </>
                  ) : (
                    'Sign In'
                  )}
                </button>

                {/* Demo Login shortcut for development */}
                <button
                  type="button"
                  disabled={loading}
                  onClick={async () => {
                    setEmail('admin@masaad.ae');
                    setPassword('admin1234');
                    setError(null);
                    setLoading(true);
                    try {
                      const res = await fetch(`${BASE_URL}/api/auth/login`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email: 'admin@masaad.ae', password: 'admin1234' }),
                      });
                      if (!res.ok) {
                        const data = await res.json().catch(() => ({}));
                        throw new Error(data?.detail || data?.message || 'Demo login failed.');
                      }
                      const data = await res.json();
                      const token: string = data.access_token ?? data.token;
                      const user = data.user ?? {
                        user_id: data.user_id,
                        email: data.email,
                        role: data.role,
                        tenant_id: data.tenant_id,
                        full_name: data.full_name,
                      };
                      if (!token) throw new Error('No token received.');
                      login(token, user);
                      router.replace('/');
                    } catch (err: unknown) {
                      setError(err instanceof Error ? err.message : 'Demo login failed.');
                    } finally {
                      setLoading(false);
                    }
                  }}
                  className="w-full mt-3 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-[#64748b] py-3 rounded-md text-xs font-bold uppercase tracking-widest transition-all flex items-center justify-center gap-2 border border-[#e2e8f0]"
                >
                  {loading ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <>
                      <span className="text-[10px] font-bold text-[#64748b]">DEV</span>
                      Demo Login
                    </>
                  )}
                </button>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="space-y-5">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-[#64748b] mb-2">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    autoComplete="name"
                    placeholder="Your full name"
                    className="w-full bg-slate-50 border border-[#e2e8f0] rounded-md py-3 px-4 text-sm font-medium text-[#1e293b] focus:ring-2 focus:ring-[#d4a017]/30 focus:border-[#002147] transition-all outline-none placeholder:text-slate-300"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-[#64748b] mb-2">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    placeholder="you@example.com"
                    className="w-full bg-slate-50 border border-[#e2e8f0] rounded-md py-3 px-4 text-sm font-medium text-[#1e293b] focus:ring-2 focus:ring-[#d4a017]/30 focus:border-[#002147] transition-all outline-none placeholder:text-slate-300"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-[#64748b] mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      autoComplete="new-password"
                      placeholder="Min 8 characters"
                      minLength={8}
                      className="w-full bg-slate-50 border border-[#e2e8f0] rounded-md py-3 px-4 pr-12 text-sm font-medium text-[#1e293b] focus:ring-2 focus:ring-[#d4a017]/30 focus:border-[#002147] transition-all outline-none placeholder:text-slate-300"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-[#64748b] hover:text-[#1e293b] transition-colors"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-[#002147] hover:bg-[#1e3a5f] disabled:bg-slate-300 text-white py-3.5 rounded-md text-xs font-bold uppercase tracking-widest transition-all flex items-center justify-center gap-2 mt-2"
                >
                  {loading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      Creating Account...
                    </>
                  ) : (
                    'Create Account'
                  )}
                </button>
              </form>
            )}

            <p className="mt-6 text-center text-[10px] text-[#64748b] font-medium uppercase tracking-widest">
              Secure -- Encrypted -- Enterprise Grade
            </p>
          </div>
        </div>

        <p className="mt-6 text-center text-[10px] text-white/50 font-medium">
          &copy; {new Date().getFullYear()} Madinat Al Saada Group. All rights reserved.
        </p>
      </div>
    </div>
  );
}
