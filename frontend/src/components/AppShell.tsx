import { Home, BookOpen, Map, BarChart2, User, Menu, X, Target } from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import { cn } from '../utils/helpers';
import { Button } from '../components';

const navigation = [
  { name: 'Home', href: '/dashboard', icon: Home },
  { name: 'Learn', href: '/learn/new', icon: BookOpen },
  { name: 'Roadmap', href: '/roadmap', icon: Map },
  { name: 'Progress', href: '/progress', icon: BarChart2 },
  { name: 'Profile', href: '/profile', icon: User },
];

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex font-sans text-slate-900">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/20 backdrop-blur-sm lg:hidden transition-opacity duration-300"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar - Premium Floating Style */}
      <aside className={cn(
        'fixed lg:static z-50 w-72 bg-white border-r border-slate-200/60 flex flex-col transition-transform duration-300 ease-in-out lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        <div className="flex flex-col h-full">
          {/* Logo Area */}
          <div className="p-8">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-2xl bg-clario-green shadow-[0_4px_0_#46A302] flex items-center justify-center transition-transform group-hover:scale-105">
                <Target className="w-6 h-6 text-white" />
              </div>
              <span className="font-display font-black text-2xl tracking-tight text-slate-800">CLARIO</span>
            </Link>
          </div>

          {/* Navigation - Pill Style */}
          <nav className="flex-1 px-4 space-y-2" role="navigation">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href ||
                (item.href !== '/' && location.pathname.startsWith(item.href));
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group',
                    isActive
                      ? 'bg-clario-green text-white shadow-md shadow-clario-green/20'
                      : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
                  )}
                >
                  <item.icon className={cn('w-5 h-5 transition-colors', isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-600')} />
                  <span className="font-bold">{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* User Profile Bottom Section */}
          <div className="p-4 mt-auto">
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-clario-green-t flex items-center justify-center font-bold text-clario-green">
                  U
                </div>
                <div className="overflow-hidden">
                  <p className="text-sm font-bold text-slate-900 truncate">Learner</p>
                  <p className="text-xs text-slate-500 truncate">Premium Plan</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 flex flex-col">
        {/* Top Header - Floating glass effect */}
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200/60 px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4 lg:hidden">
            <button
              className="p-2 rounded-xl text-slate-600 hover:bg-slate-100"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>

          <div className="flex-1" />

          <div className="flex items-center gap-6">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-orange-100 text-orange-700 text-xs font-black uppercase tracking-widest">
              <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
              Live Session
            </div>
            <div className="w-10 h-10 rounded-full bg-slate-200 border-2 border-white shadow-sm" />
          </div>
        </header>

        {/* Page Content - Centered & Focused */}
        <div className="p-8 max-w-7xl mx-auto w-full">
          <Outlet />
        </div>
      </main>
    </div>
  );
}