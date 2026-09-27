import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components';
import { api } from '../services';
import { useAuth } from '../hooks';

export function AuthPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const auth = isRegistering
        ? await api.register({ email, password })
        : await api.login({ email, password });
      await login(auth);
      navigate(
        !auth.profile_complete ? '/profile-setup' :
        !auth.mind_profile_complete ? '/mind-profile' : '/dashboard',
        { replace: true },
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to authenticate.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen grid place-items-center p-6 bg-gradient-to-b from-clario-green-bg to-white">
      <div className="w-full max-w-[440px] bg-white border-2 border-clario-line rounded-clario-2xl p-8 shadow-[0_6px_0_var(--clario-line)]">
        <div className="flex items-center gap-2.5 mb-6">
          <div className="w-[34px] h-[34px] rounded-[11px] bg-gradient-to-br from-clario-green-hi to-clario-green flex items-center justify-center text-white text-[19px] font-black shadow-[0_3px_0_var(--clario-green-sh)]">
            C
          </div>
          <span className="text-[26px] font-black tracking-tighter text-clario-green">CLARIO</span>
        </div>

        <h1 className="text-[27px] font-black tracking-tight mb-1">{isRegistering ? 'Create your account' : 'Welcome back'}</h1>
        <p className="text-clario-ink-2 font-semibold mb-6">Come confused. Leave with clarity.</p>

        <Button
          variant="blue"
          fullWidth
          className="mb-3 py-4"
          disabled
          title="Google OAuth setup is not configured yet"
        >
          <svg className="w-5 h-5 mr-2" viewBox="0 0 48 48">
            <path fill="currentColor" d="M44.5 20H24v8.5h11.8C34.7 33.9 30.1 37 24 37c-7.2 0-13-5.8-13-13s5.8-13 13-13c3.1 0 6 1.1 8.2 2.9l6.4-6.4C34.6 4.1 29.6 2 24 2 11.8 2 2 11.8 2 24s9.8 22 22 22c11 0 21-8 21-22 0-1.3-.1-2.7-.5-4z"/>
          </svg>
          Google sign-in unavailable
        </Button>

        <div className="flex items-center gap-3 my-5 text-clario-ink-3 font-black text-[12px] uppercase tracking-widest">
          <div className="flex-1 h-px bg-clario-line-2" />
          <span>or</span>
          <div className="flex-1 h-px bg-clario-line-2" />
        </div>

        <form onSubmit={handleEmailLogin} className="space-y-4">
          <div className="space-y-1">
            <label className="block text-[12.5px] font-black uppercase tracking-widest text-clario-ink-2">Email</label>
            <input
              type="email"
              className="w-full p-3.5 border-2 border-clario-line rounded-clario-md bg-clario-bg-2 font-bold text-sm transition-all focus:outline-none focus:border-clario-green focus:bg-white focus:ring-4 focus:ring-clario-green-t"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="space-y-1">
            <label className="block text-[12.5px] font-black uppercase tracking-widest text-clario-ink-2">Password</label>
            <input
              type="password"
              className="w-full p-3.5 border-2 border-clario-line rounded-clario-md bg-clario-bg-2 font-bold text-sm transition-all focus:outline-none focus:border-clario-green focus:bg-white focus:ring-4 focus:ring-clario-green-t"
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </div>

          {error && (
            <div className="p-4 bg-clario-red-t border-2 border-clario-red-sh rounded-clario-md text-clario-red-sh font-bold text-sm animate-shake">
              <span className="mr-2">⚠️</span> {error}
            </div>
          )}

          <Button variant="primary" fullWidth className="mt-1.5" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Please wait...' : isRegistering ? 'Create account' : 'Log in with email'}
          </Button>
        </form>

        <p className="text-center mt-5 text-sm font-bold text-clario-ink-3">
          {isRegistering ? 'Already have an account?' : 'New here?'} <button
            className="text-clario-green font-black underline hover:text-clario-green-deep"
            onClick={() => {
              setIsRegistering(!isRegistering);
              setError(null);
            }}
          >
            {isRegistering ? 'Log in' : 'Create an account'}
          </button>
        </p>
      </div>
    </div>
  );
}