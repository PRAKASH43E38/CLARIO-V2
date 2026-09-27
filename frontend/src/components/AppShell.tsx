import { Home, BookOpen, Map, BarChart2, User, Menu, X, ChevronLeft, Target } from 'lucide-react';
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
    <div className="min-h-screen bg-clario-bg-50 flex">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 lg:hidden" 
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside className={cn(
        'fixed lg:static z-50 w-64 bg-white border-r border-clario-surface-100 flex flex-col transition-transform duration-300 ease-in-out lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-clario-surface-100">
            <Link to="/" className="flex items-center gap-3" aria-label="CLARIO Home">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-clario-primary-500 to-clario-secondary-500 flex items-center justify-center">
                <Target className="w-6 h-6 text-white" />
              </div>
              <span className="font-display font-bold text-xl text-clario-surface-900">CLARIO</span>
            </Link>
            <p className="text-sm text-clario-surface-500 mt-2">Come confused. Leave with clarity.</p>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1" role="navigation" aria-label="Main navigation">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href || 
                (item.href !== '/' && location.pathname.startsWith(item.href));
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-200',
                    isActive
                      ? 'bg-clario-primary-50 text-clario-primary-700 font-semibold'
                      : 'text-clario-surface-600 hover:bg-clario-surface-100 hover:text-clario-surface-900'
                  )}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <item.icon className={cn('w-5 h-5 flex-shrink-0', isActive && 'text-clario-primary-600')} aria-hidden="true" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-clario-surface-100">
            <p className="text-xs text-clario-surface-500 text-center">
              CLARIO v0.1.0
            </p>
          </div>
        </div>
      </aside>

      {/* Mobile menu button */}
      <button
        className="lg:hidden fixed bottom-4 right-4 z-50 w-14 h-14 rounded-2xl bg-clario-primary-500 text-white shadow-lg flex items-center justify-center"
        onClick={() => setSidebarOpen(true)}
        aria-label="Open navigation menu"
      >
        <Menu className="w-6 h-6" />
      </button>

      {/* Main content */}
      <main className="flex-1 lg:ml-0 min-w-0">
        <header className="lg:hidden sticky top-0 z-30 bg-white border-b border-clario-surface-100 px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" aria-label="CLARIO Home">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-clario-primary-500 to-clario-secondary-500 flex items-center justify-center">
              <Target className="w-5 h-5 text-white" />
            </div>
            <span className="font-display font-bold text-lg text-clario-surface-900">CLARIO</span>
          </Link>
          <button
            className="p-2 rounded-xl text-clario-surface-600 hover:bg-clario-surface-100"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        </header>

        <div className="lg:pt-0">
          <Outlet />
        </div>
      </main>
    </div>
  );
}