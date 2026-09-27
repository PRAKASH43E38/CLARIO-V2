import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components';

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white bg-[radial-gradient(1200px_600px_at_80%_-10%,var(--clario-green-bg),transparent_60%)]">
      {/* Navigation */}
      <nav className="flex items-center gap-4 px-6 py-4 max-w-[1180px] mx-auto">
        <div className="flex items-center gap-2.5">
          <div className="w-[34px] h-[34px] rounded-[11px] bg-gradient-to-br from-clario-green-hi to-clario-green flex items-center justify-center text-white text-[19px] font-black shadow-[0_3px_0_var(--clario-green-sh),0_0_20px_rgba(88,204,2,0.35)]">
            C
          </div>
          <span className="text-[26px] font-black tracking-tighter text-clario-green">CLARIO</span>
        </div>
        <div className="flex-1" />
        <Button variant="ghost" size="sm" onClick={() => navigate('/auth')}>
          Log in
        </Button>
      </nav>

      {/* Hero Section */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center max-w-[1180px] mx-auto px-6 py-12 lg:py-24">
        <div className="text-left">
          <h1 className="text-[clamp(38px,5.4vw,62px)] font-black leading-[1.05] tracking-tighter text-clario-ink">
            Come confused.<br />
            <span className="bg-gradient-to-r from-clario-green to-clario-green-hi bg-clip-text text-transparent">
              Leave with clarity.
            </span>
          </h1>
          <p className="text-[19px] font-semibold text-clario-ink-2 mt-4 max-w-[520px] leading-relaxed">
            CLARIO turns anything you want to learn into a guided journey — with levels, streaks, XP and an AI that quietly adapts to how <em className="italic">you</em> think.
          </p>

          <div className="flex flex-wrap gap-3.5 mt-8">
            <Button variant="primary" size="lg" onClick={() => navigate('/auth')}>
              Get started — it's free
            </Button>
            <Button variant="ghost" size="lg" onClick={() => navigate('/auth')}>
              I already have an account
            </Button>
          </div>

          <div className="flex flex-wrap gap-7 mt-9">
            <div className="flex flex-col">
              <span className="text-[26px] font-black text-clario-green">Anything</span>
              <span className="text-[13px] font-black uppercase tracking-widest text-clario-ink-3">Any subject</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[26px] font-black text-clario-green">5 min</span>
              <span className="text-[13px] font-black uppercase tracking-widest text-clario-ink-3">A day is enough</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[26px] font-black text-clario-green">6</span>
              <span className="text-[13px] font-black uppercase tracking-widest text-clario-ink-3">Learning companions</span>
            </div>
          </div>
        </div>

        <div className="relative flex items-center justify-center min-h-[380px]">
          {/* Animated Blob Background */}
          <div className="absolute w-full max-w-[420px] aspect-square rounded-full bg-radial-gradient from-clario-green-t to-clario-green-bg opacity-50 blur-sm animate-aura-pulse" />

          {/* Floating Card Stack */}
          <div className="relative z-10 flex flex-col gap-3.5 w-full max-w-[340px]">
            <div className="bg-white border-2 border-clario-line rounded-[20px] p-4 shadow-[0_6px_0_var(--clario-line)] flex items-center gap-3.5 animate-floaty">
              <div className="w-11 h-11 rounded-[14px] bg-clario-blue-t flex items-center justify-center text-2xl">🔭</div>
              <div>
                <span className="block text-sm font-black">Nova researched it</span>
                <span className="text-[12.5px] font-bold text-clario-ink-3">14 sources → 3 key ideas</span>
              </div>
            </div>
            <div className="bg-white border-2 border-clario-line rounded-[20px] p-4 shadow-[0_6px_0_var(--clario-line)] flex items-center gap-3.5 animate-floaty [animation-delay:0.7s] ml-8">
              <div className="w-11 h-11 rounded-[14px] bg-clario-green-t flex items-center justify-center text-2xl">💡</div>
              <div>
                <span className="block text-sm font-black">Mira explained it</span>
                <span className="text-[12.5px] font-bold text-clario-ink-3">Adapted to how you learn</span>
              </div>
            </div>
            <div className="bg-white border-2 border-clario-line rounded-[20px] p-4 shadow-[0_6px_0_var(--clario-line)] flex items-center gap-3.5 animate-floaty [animation-delay:1.4s]">
              <div className="w-11 h-11 rounded-[14px] bg-clario-yellow-t flex items-center justify-center text-2xl">⚡</div>
              <div>
                <span className="block text-sm font-black">+120 XP earned</span>
                <span className="text-[12.5px] font-bold text-clario-ink-3">Level 3 · 72% complete</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-[1180px] mx-auto px-6 pb-[70px]">
        {[
          { icon: '🎮', color: 'green', title: 'Learning that feels like a game', text: 'Levels, streaks, XP and unlockable achievements. You always know what\'s next.' },
          { icon: '🧠', color: 'blue', title: 'An AI that adapts to you', text: 'Struggle with something? CLARIO notices and quietly teaches it a different way.' },
          { icon: '♾️', color: 'purple', title: 'Learn literally anything', text: 'Data science, guitar, Spanish, negotiating. Type it in — CLARIO builds the roadmap.' },
          { icon: '🌍', color: 'orange', title: 'Practice in the real world', text: 'Every level ends with a practical mission, not just a multiple-choice quiz.' },
        ].map((f, i) => (
          <div key={i} className="p-6 rounded-clario-xl border-2 border-clario-line bg-white shadow-[0_3px_0_var(--clario-line)] transition-transform hover:-translate-y-1">
            <div className={`w-13 h-13 rounded-clario-md flex items-center justify-center text-3xl mb-3 bg-clario-${f.color}-t`}>
              {f.icon}
            </div>
            <h3 className="text-lg font-black mb-1">{f.title}</h3>
            <p className="text-clario-ink-2 font-semibold text-sm leading-relaxed">{f.text}</p>
          </div>
        ))}
      </section>
    </div>
  );
}