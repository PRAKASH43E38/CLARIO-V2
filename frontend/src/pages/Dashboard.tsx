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
    <div className="animate-slide-up space-y-8">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-slate-500 font-bold text-sm uppercase tracking-widest">{getGreeting()}, {dashboard.learner_name}</p>
          <h1 className="font-display font-black text-4xl text-slate-900 tracking-tight mt-1">Your Journey</h1>
        </div>
        <div className="flex items-center gap-3">
          <XPBadge xp={xp} size="md" />
          <StreakBadge streak={streak} size="md" />
        </div>
      </div>

      {/* Hero Card - Premium Glass Style */}
      <Card variant="green" padding="lg" className="relative overflow-hidden border-none shadow-xl bg-gradient-to-br from-clario-green to-clario-green-deep text-white">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-20 -mt-20 blur-3xl" />
        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="w-20 h-20 rounded-3xl bg-white/20 backdrop-blur-md flex items-center justify-center shadow-inner">
              <Target className="w-10 h-10 text-white" />
            </div>
            <div>
              <p className="text-clario-green-t font-black uppercase tracking-widest text-xs">Current Goal</p>
              <h2 className="font-display font-black text-3xl tracking-tight">{dashboard.current_topic}</h2>
            </div>
          </div>

          <div className="flex items-center gap-6 bg-white/10 backdrop-blur-sm p-4 rounded-2xl border border-white/20">
            <div className="text-right">
              <p className="text-clario-green-t text-xs font-black uppercase tracking-widest">Overall Progress</p>
              <p className="font-display font-black text-3xl">{Math.round(overallProgress)}%</p>
            </div>
            <CircularProgress value={overallProgress} size={60} strokeWidth={8} variant="primary" showValue={false} />
          </div>
        </div>
      </Card>

      {/* Primary Action */}
      <Button
        variant="primary"
        size="lg"
        fullWidth
        className="py-6 text-xl shadow-clario-btn-green transition-transform hover:scale-[1.01] active:scale-95"
        leftIcon={<PlayCircle className="w-6 h-6" />}
        onClick={handleContinueLearning}
        disabled={!userId}
      >
        {currentConcept ? (
          <>
            Continue: {currentConcept.concept}
            <ArrowRight className="w-6 h-6" />
          </>
        ) : (
          'Start a new learning session'
        )}
      </Button>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Progress Area */}
        <div className="lg:col-span-2 space-y-8">
          {/* Stats Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { label: 'XP Today', value: `${xp % 1000} / 1000`, icon: Flame, color: 'orange' },
              { label: 'Weekly Streak', value: `${streak} / 7 days`, icon: TrendingUp, color: 'blue' },
              { label: 'Mastered', value: `${masteredCount} / ${totalConcepts}`, icon: Award, color: 'green' },
            ].map((stat, i) => (
              <Card key={i} padding="lg" className="text-center hover:shadow-md transition-all">
                <div className="flex justify-center mb-3">
                  <div className={`w-12 h-12 rounded-2xl bg-clario-${stat.color}-t flex items-center justify-center text-clario-${stat.color}-600 shadow-soft`}>
                    <stat.icon className="w-6 h-6" />
                  </div>
                </div>
                <p className="text-slate-500 font-bold text-xs uppercase tracking-wider mb-1">{stat.label}</p>
                <p className="font-display font-black text-2xl text-slate-900">{stat.value}</p>
              </Card>
            ))}
          </div>

          {/* Concept Mastery - Premium List */}
          <Card padding="lg" className="border-none shadow-sm bg-white">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display font-black text-xl text-slate-900">Concept Mastery</h2>
              <Badge variant="primary" size="sm">Your Level</Badge>
            </div>
            <div className="space-y-5">
              {dashboard.concept_breakdown.map((concept, index) => (
                <div key={concept.concept} className="group animate-slide-up" style={{ animationDelay: `${index * 50}ms` }}>
                  <div className="flex items-center justify-between gap-4 mb-2">
                    <div className="flex items-center gap-3 overflow-hidden">
                      <Badge status={concept.status} size="sm" />
                      <span className="font-bold text-slate-700 truncate group-hover:text-slate-900 transition-colors">{concept.concept}</span>
                    </div>
                    <span className="font-display font-black text-slate-900">{Math.round(concept.mastery_score)}%</span>
                  </div>
                  <ProgressBar
                    value={concept.mastery_score}
                    max={100}
                    size="sm"
                    variant={concept.status === 'mastered' ? 'success' : concept.status === 'remediating' ? 'warning' : 'primary'}
                  />
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right Side - Intelligence & Actions */}
        <div className="space-y-6">
          {/* Weak Concepts - Urgent Action */}
          {dashboard.weak_concepts.length > 0 && (
            <Card padding="lg" className="bg-orange-50 border-2 border-orange-100 shadow-none">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-orange-200 flex items-center justify-center text-orange-600">
                  <Zap className="w-4 h-4" />
                </div>
                <h2 className="font-display font-black text-orange-800">Needs Practice</h2>
              </div>
              <ul className="space-y-3">
                {dashboard.weak_concepts.map((concept, i) => (
                  <li key={concept} className="flex items-center justify-between p-3 bg-white rounded-xl border border-orange-100 shadow-sm animate-slide-up" style={{ animationDelay: `${i * 50}ms` }}>
                    <span className="font-bold text-slate-700 text-sm">{concept}</span>
                    <Badge status="remediating" size="sm" />
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* AI Recommendation */}
          <Card padding="lg" className="bg-slate-900 text-white border-none shadow-xl overflow-hidden relative">
            <div className="absolute top-0 right-0 w-32 h-32 bg-clario-green/20 rounded-full -mr-16 -mt-16 blur-3xl" />
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-clario-green text-white flex items-center justify-center shadow-clario-btn-green">
                  <Lightbulb className="w-5 h-5" />
                </div>
                <h3 className="font-black uppercase tracking-widest text-xs text-slate-400">CLARIO AI Insight</h3>
              </div>
              <p className="text-lg font-medium leading-relaxed text-slate-200">
                {nextAction}
              </p>
            </div>
          </Card>

          {/* Roadmap Mini-Preview */}
          {showRoadmapPreview && roadmap && (
            <Card padding="lg" className="border-none shadow-sm">
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-display font-black text-lg text-slate-900">Learning Path</h2>
                <Button variant="ghost" size="sm" onClick={() => navigate('/roadmap')}>
                  Full Map <ArrowRight className="w-4 h-4" />
                </Button>
              </div>
              <div className="space-y-3">
                {roadmap.roadmap.slice(0, 4).map((concept, index) => (
                  <div key={concept.concept_id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <div className={cn('w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs transition-colors',
                      concept.status === 'mastered' ? 'bg-clario-green text-white' :
                      concept.is_next ? 'bg-clario-blue text-white ring-4 ring-clario-blue-t' :
                      'bg-slate-200 text-slate-500'
                    )}>
                      {concept.status === 'mastered' ? <CheckCircle className="w-4 h-4" /> : index + 1}
                    </div>
                    <span className="font-bold text-slate-700 text-sm truncate flex-1">{concept.concept_title}</span>
                    {concept.is_next && <Badge variant="primary" size="sm">Next</Badge>}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}div>
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