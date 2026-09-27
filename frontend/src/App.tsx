import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import { AppShell } from './components/AppShell';
import { OnboardingPage } from './pages/Onboarding';
import { DashboardPage } from './pages/Dashboard';
import { RoadmapPage } from './pages/Roadmap';
import { LearnPage } from './pages/Learn';
import { ProgressPage } from './pages/Progress';
import { ProfilePage } from './pages/Profile';
import { LandingPage } from './pages/Landing';
import { AuthPage } from './pages/Auth';
import { ProfileCreationPage } from './pages/ProfileCreation';
import { MindQuestionsPage } from './pages/MindQuestions';
import { useAuth } from './hooks/useAuth';

function ProtectedRoute({ children, requireSetup = false }: { children: React.ReactNode; requireSetup?: boolean }) {
  const { userId, isLoading, profileComplete, mindProfileComplete } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-clario-bg-50">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-clario-green border-t-transparent" />
      </div>
    );
  }

  if (!userId) {
    return <Navigate to="/auth" replace />;
  }
  if (requireSetup && !profileComplete) {
    return <Navigate to="/profile-setup" replace />;
  }
  if (requireSetup && !mindProfileComplete) {
    return <Navigate to="/mind-profile" replace />;
  }

  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { userId, isLoading, profileComplete, mindProfileComplete } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-clario-bg-50">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-clario-green border-t-transparent" />
      </div>
    );
  }

  if (userId) {
    return <Navigate to={!profileComplete ? '/profile-setup' : !mindProfileComplete ? '/mind-profile' : '/dashboard'} replace />;
  }

  return <>{children}</>;
}

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/auth" element={<PublicRoute><AuthPage /></PublicRoute>} />
        <Route path="/profile-setup" element={<ProtectedRoute><ProfileCreationPage /></ProtectedRoute>} />
        <Route path="/mind-profile" element={<ProtectedRoute><MindQuestionsPage /></ProtectedRoute>} />
        <Route path="/learn/new" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
        <Route element={
          <ProtectedRoute requireSetup>
            <AppShell />
          </ProtectedRoute>
        }>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/learn" element={<LearnPage />} />
          <Route path="/roadmap" element={<RoadmapPage />} />
          <Route path="/progress" element={<ProgressPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}