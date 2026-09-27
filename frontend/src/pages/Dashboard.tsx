import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button, Card, CardContent, Badge, ProgressBar, CircularProgress, XPBadge, StreakBadge, SkeletonDashboard, EmptyState } from '../components';
import { useDashboard, useRoadmap } from '../hooks';
import { useAuth } from '../hooks';
import { cn } from '../utils/helpers';
import { 
  Target, Flame, Trophy, TrendingUp, 
  PlayCircle, ArrowRight, BookOpen, 
  Lightbulb, Zap, Award, Brain, CheckCircle
} from 'lucide-react';

const stageIcons = {
  teaching: Lightbulb,
  thinking: Brain,
  practical: Zap,
  quiz: Award,
  evaluation: Trophy,
  completed: CheckCircle,
};

const stageLabels = {
  teaching: 'Learn',
  thinking: 'Think',
  practical: 'Apply',
  quiz: 'Quiz',
  evaluation: 'Review',
  completed: 'Complete',
};

const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
};

export function DashboardPage() {
  const navigate = useNavigate();
  const { userId, profile, refreshProfile } = useAuth();
  const { dashboard, isLoading: dashboardLoading, error: dashboardError, refetch: refetchDashboard } = useDashboard(userId);
  const { roadmap } = useRoadmap(userId);
  const [showRoadmapPreview, setShowRoadmapPreview] = useState(true);

  useEffect(() => {
    if (userId) {
      refreshProfile();
    }
  }, [userId, refreshProfile]);

  const currentConcept = dashboard?.concept_breakdown.find(c => c.status === 'learning' || c.status === 'remediating');
  const masteredCount = dashboard?.concept_breakdown.filter(c => c.status === 'mastered').length || 0;
  const totalConcepts = dashboard?.concept_breakdown.length || 0;
  const overallProgress = totalConcepts > 0 ? (masteredCount / totalConcepts) * 100 : 0;

  const xp = profile?.initial_confidence ? profile.initial_confidence * 100 : 0;
  const streak = 7; // TODO: get from backend
  const dailyGoal = 50;

  const handleContinueLearning = () => {
    navigate('/learn/new');
  };

  if (dashboardLoading) {
    return <SkeletonDashboard />;
  }

  if (dashboardError) {
    return (
      <div className="page-container">
        <EmptyState
          title="Unable to load dashboard"
          message={dashboardError}
          action={{ label: 'Retry', onClick: refetchDashboard }}
        />
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="page-container">
        <EmptyState
          title="No learning data yet"
          message="Start a new learning session to build your first roadmap."
          action={{ label: 'New Learning', onClick: () => navigate('/learn/new') }}
        />
      </div>
    );
  }

  const nextAction = dashboard.recommended_action;
  const isRemediating = dashboard.weak_concepts.length > 0;

  return (
    <div className="page-container">
      {/* Header */}
      <div className="mb-8 animate-slide-up">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <p className="text-clario-primary-600 font-medium">{getGreeting()}, {dashboard.learner_name}</p>
            <h1 className="font-display font-bold text-3xl text-clario-surface-900 mt-1">Continue your journey</h1>
          </div>
          <div className="flex items-center gap-3">
            <XPBadge xp={xp} size="md" />
            <StreakBadge streak={streak} size="md" />
          </div>
        </div>

        {/* Current Goal */}
        <Card variant="hover" padding="lg" className="bg-gradient-to-br from-clario-primary-50 to-clario-secondary-50 border-clario-primary-100">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-white/80 backdrop-blur flex items-center justify-center shadow-soft">
                <Target className="w-8 h-8 text-clario-primary-600" />
              </div>
              <div>
                <p className="text-sm text-clario-primary-700 font-medium">Current Goal</p>
                <h2 className="font-display font-bold text-xl text-clario-surface-900">{dashboard.current_topic}</h2>
              </div>
            </div>
            
            <div className="flex items-center gap-4 sm:ml-auto">
              <div className="hidden sm:block text-right">
                <p className="text-sm text-clario-primary-700">Overall Progress</p>
                <p className="font-display font-bold text-2xl text-clario-primary-600">{Math.round(overallProgress)}%</p>
              </div>
              <CircularProgress value={overallProgress} size={80} strokeWidth={6} variant="primary" showValue={false} />
            </div>
          </div>
        </Card>

        {/* Continue Learning Button */}
        <Button 
          variant="primary" 
          size="lg" 
          fullWidth 
          className="mb-8 animate-slide-up animation-delay-100"
          leftIcon={<PlayCircle className="w-5 h-5" />}
          onClick={handleContinueLearning}
          disabled={!userId}
        >
          {currentConcept ? (
            <>
              New session · Continue: {currentConcept.concept}
              <ArrowRight className="w-5 h-5" />
            </>
          ) : (
            'Start a new learning session'
          )}
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column - Stats & Progress */}
        <div className="lg:col-span-2 space-y-6">
          {/* Daily Progress */}
          <Card padding="lg">
            <div className="flex items-center justify-between mb-6">
              <h2 className="section-title">Today's Progress</h2>
              <Badge variant="primary">Day {streak} Streak</Badge>
            </div>
            
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="text-center p-4 bg-clario-surface-50 rounded-2xl">
                <CircularProgress value={Math.min((xp % 1000) / 10, 100)} size={70} strokeWidth={5} variant="primary" />
                <p className="mt-2 text-sm text-clario-surface-600">XP Today</p>
                <p className="font-display font-bold text-xl text-clario-surface-900">{xp % 1000} / 1000</p>
              </div>
              
              <div className="text-center p-4 bg-clario-surface-50 rounded-2xl">
                <CircularProgress value={streak > 7 ? 100 : (streak / 7) * 100} size={70} strokeWidth={5} variant="warning" />
                <p className="mt-2 text-sm text-clario-surface-600">Weekly Streak</p>
                <p className="font-display font-bold text-xl text-clario-surface-900">{streak} / 7 days</p>
              </div>
              
              <div className="text-center p-4 bg-clario-surface-50 rounded-2xl">
                <CircularProgress value={masteredCount > 0 ? (masteredCount / Math.max(totalConcepts, 1)) * 100 : 0} size={70} strokeWidth={5} variant="success" />
                <p className="mt-2 text-sm text-clario-surface-600">Concepts Mastered</p>
                <p className="font-display font-bold text-xl text-clario-surface-900">{masteredCount} / {totalConcepts}</p>
              </div>
            </div>
          </Card>

          {/* Concept Breakdown */}
          <Card padding="lg">
            <h2 className="section-title mb-6">Concept Progress</h2>
            <div className="space-y-4">
              {dashboard.concept_breakdown.map((concept, index) => (
                <div key={concept.concept} className="animate-slide-up" style={{ animationDelay: `${index * 100}ms` }}>
                  <div className="flex items-center justify-between gap-4 mb-2">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <Badge status={concept.status} size="sm" />
                      <div className="min-w-0">
                        <p className="font-medium text-clario-surface-900 truncate">{concept.concept}</p>
                        <p className="text-sm text-clario-surface-500">Difficulty: {concept.difficulty}/5</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-display font-bold text-clario-surface-900">{Math.round(concept.mastery_score)}%</p>
                    </div>
                  </div>
                  <ProgressBar 
                    value={concept.mastery_score} 
                    max={100} 
                    size="md" 
                    variant={concept.status === 'mastered' ? 'success' : concept.status === 'remediating' ? 'warning' : 'primary'}
                  />
                </div>
              ))}
            </div>
          </Card>

          {/* Roadmap Preview */}
          {showRoadmapPreview && roadmap && (
            <Card padding="lg">
              <div className="flex items-center justify-between mb-6">
                <h2 className="section-title">Your Learning Path</h2>
                <Button variant="ghost" size="sm" onClick={() => setShowRoadmapPreview(false)}>
                  View Full Roadmap
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </div>
              <div className="space-y-4">
                {roadmap.roadmap.slice(0, 5).map((concept, index) => (
                  <div key={concept.concept_id} className="flex items-center gap-4 p-3 bg-clario-surface-50 rounded-xl">
                    <div className={cn('w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm', 
                      concept.status === 'mastered' ? 'bg-clario-success-500 text-white' :
                      concept.status === 'remediating' ? 'bg-clario-warning-500 text-white' :
                      concept.is_next ? 'bg-clario-primary-500 text-white ring-4 ring-clario-primary-500/20' :
                      concept.status === 'learning' ? 'bg-clario-secondary-500 text-white' :
                      'bg-clario-surface-200 text-clario-surface-500'
                    )}>
                      {concept.status === 'mastered' && <CheckCircle className="w-5 h-5" />}
                      {concept.status !== 'mastered' && <span>{index + 1}</span>}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-clario-surface-900 truncate">{concept.concept_title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge status={concept.status} size="sm" />
                        <span className="text-xs text-clario-surface-500">Level {concept.difficulty}</span>
                      </div>
                    </div>
                    {concept.is_next && (
                      <Badge variant="primary" size="sm">Next</Badge>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Right Column - Quick Stats & Actions */}
        <div className="space-y-6">
          {/* Quick Stats */}
          <Card padding="lg">
            <h2 className="section-title mb-6">Quick Stats</h2>
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 bg-clario-surface-50 rounded-xl">
                <div className="w-10 h-10 rounded-xl bg-clario-primary-100 text-clario-primary-600 flex items-center justify-center">
                  <Trophy className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm text-clario-surface-500">Concepts Mastered</p>
                  <p className="font-display font-bold text-xl text-clario-surface-900">{masteredCount}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-clario-surface-50 rounded-xl">
                <div className="w-10 h-10 rounded-xl bg-clario-success-100 text-clario-success-600 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm text-clario-surface-500">Current Difficulty</p>
                  <p className="font-display font-bold text-xl text-clario-surface-900">
                    {currentConcept ? currentConcept.difficulty : '—'}/5
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-clario-surface-50 rounded-xl">
                <div className="w-10 h-10 rounded-xl bg-clario-warning-100 text-clario-warning-600 flex items-center justify-center">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm text-clario-surface-500">Needs Practice</p>
                  <p className="font-display font-bold text-xl text-clario-surface-900">{dashboard.weak_concepts.length}</p>
                </div>
              </div>
            </div>
          </Card>

          {/* Needs Practice */}
          {dashboard.weak_concepts.length > 0 && (
            <Card padding="lg" className="border-clario-warning-200 bg-clario-warning-50">
              <div className="flex items-center gap-2 mb-4">
                <svg className="w-5 h-5 text-clario-warning-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <h2 className="section-title text-clario-warning-800">Needs Practice</h2>
              </div>
              <ul className="space-y-2">
                {dashboard.weak_concepts.map((concept, i) => (
                  <li key={concept} className="flex items-center justify-between p-3 bg-white rounded-xl border border-clario-warning-100 animate-slide-up" style={{ animationDelay: `${i * 100}ms` }}>
                    <span className="font-medium text-clario-surface-900">{concept}</span>
                    <Badge status="remediating" size="sm" />
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Recommended Action */}
          <Card padding="lg" className="bg-clario-primary-50 border-clario-primary-100">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-clario-primary-500/10 flex items-center justify-center flex-shrink-0">
                <Lightbulb className="w-5 h-5 text-clario-primary-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-clario-primary-800">Recommended Next Step</h3>
                <p className="text-clario-primary-700 mt-1">{nextAction}</p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}