import { Card, Badge, ProgressBar, CircularProgress, XPBadge, StreakBadge, LoadingSpinner, SkeletonDashboard } from '../components';
import { useDashboard, useRoadmap } from '../hooks';
import { useAuth } from '../hooks';
import { cn } from '../utils/helpers';
import { 
  Trophy, TrendingUp, Target, BookOpen, 
  Award, Flame, Calendar, Clock,
  BarChart2, LineChart, PieChart, CheckCircle, RotateCcw
} from 'lucide-react';

export function ProgressPage() {
  const { userId, profile } = useAuth();
  const { dashboard, isLoading: dashboardLoading, error: dashboardError } = useDashboard(userId);
  const { roadmap, isLoading: roadmapLoading } = useRoadmap(userId);

  if (dashboardLoading || roadmapLoading) {
    return <SkeletonDashboard />;
  }

  if (dashboardError) {
    return (
      <div className="page-container">
        <div className="text-center py-12">
          <p className="text-clario-attention-600">Unable to load progress data</p>
        </div>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="page-container">
        <div className="text-center py-12">
          <p className="text-clario-surface-500">Complete onboarding to see your progress</p>
        </div>
      </div>
    );
  }

  const masteredCount = dashboard.concept_breakdown.filter(c => c.status === 'mastered').length;
  const learningCount = dashboard.concept_breakdown.filter(c => c.status === 'learning').length;
  const remediatingCount = dashboard.concept_breakdown.filter(c => c.status === 'remediating').length;
  const totalConcepts = dashboard.concept_breakdown.length;
  const overallProgress = totalConcepts > 0 ? (masteredCount / totalConcepts) * 100 : 0;

  const xp = profile?.initial_confidence ? profile.initial_confidence * 100 + masteredCount * 50 : 0;
  const streak = 7;
  const level = Math.floor(xp / 500) + 1;
  const levelProgress = (xp % 500) / 500 * 100;

  return (
    <div className="page-container">
      {/* Header */}
      <div className="mb-8 animate-slide-up">
        <div>
          <p className="text-clario-primary-600 font-medium">Your Progress</p>
          <h1 className="font-display font-bold text-3xl text-clario-surface-900 mt-1">Track your learning journey</h1>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column - Overview */}
        <div className="lg:col-span-2 space-y-6">
          {/* XP & Level */}
          <Card padding="lg" className="bg-gradient-to-br from-clario-primary-50 to-clario-secondary-50 border-clario-primary-100">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-white/80 backdrop-blur flex items-center justify-center shadow-soft">
                  <Trophy className="w-8 h-8 text-clario-primary-600" />
                </div>
                <div>
                  <p className="text-sm text-clario-primary-700 font-medium">Current Level</p>
                  <h2 className="font-display font-bold text-3xl text-clario-surface-900">Level {level}</h2>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <XPBadge xp={xp} size="lg" />
                <div className="text-right">
                  <p className="text-sm text-clario-primary-700">XP to next level</p>
                  <p className="font-display font-bold text-xl text-clario-primary-600">{500 - (xp % 500)} XP</p>
                </div>
              </div>
            </div>
            <ProgressBar value={levelProgress} max={100} size="lg" variant="primary" showLabel label="Level Progress" className="mt-6" />
          </Card>

          {/* Streak & Daily Goal */}
          <div className="grid gap-4 sm:grid-cols-2">
            <Card padding="lg" variant="hover">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-clario-warning-100 text-clario-warning-600 flex items-center justify-center">
                  <Flame className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-clario-warning-600">Current Streak</p>
                  <p className="font-display font-bold text-3xl text-clario-surface-900">{streak} days</p>
                </div>
              </div>
              <ProgressBar value={Math.min((streak / 30) * 100, 100)} max={100} variant="warning" showLabel label="Monthly goal" className="mt-4" />
            </Card>

            <Card padding="lg" variant="hover">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-clario-success-100 text-clario-success-600 flex items-center justify-center">
                  <Target className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-clario-success-600">Daily Goal</p>
                  <p className="font-display font-bold text-3xl text-clario-surface-900">{masteredCount > 0 ? 'Achieved' : 'In Progress'}</p>
                </div>
              </div>
              <ProgressBar value={masteredCount > 0 ? 100 : 20} max={100} variant="success" showLabel label="Today's progress" className="mt-4" />
            </Card>
          </div>

          {/* Concept Mastery Distribution */}
          <Card padding="lg">
            <h2 className="section-title mb-6">Mastery Distribution</h2>
            <div className="space-y-4">
              {[
                { label: 'Mastered', count: masteredCount, color: 'success' as const },
                { label: 'Learning', count: learningCount, color: 'primary' as const },
                { label: 'Needs Practice', count: remediatingCount, color: 'warning' as const },
              ].map(({ label, count, color }) => (
                <div key={label} className="flex items-center gap-4">
                  <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', 
                    color === 'success' && 'bg-clario-success-100 text-clario-success-600',
                    color === 'primary' && 'bg-clario-primary-100 text-clario-primary-600',
                    color === 'warning' && 'bg-clario-warning-100 text-clario-warning-600'
                  )}>
                    {color === 'success' && <CheckCircle className="w-5 h-5" />}
                    {color === 'primary' && <BookOpen className="w-5 h-5" />}
                    {color === 'warning' && <Award className="w-5 h-5" />}
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-clario-surface-600">{label}</span>
                      <span className="font-semibold text-clario-surface-900">{count}</span>
                    </div>
                    <ProgressBar value={totalConcepts > 0 ? (count / totalConcepts) * 100 : 0} max={100} variant={color} size="sm" />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Detailed Concept Progress */}
          <Card padding="lg">
            <h2 className="section-title mb-6">Concept Details</h2>
            <div className="space-y-4">
              {dashboard.concept_breakdown.map((concept, index) => (
                <div key={concept.concept} className="animate-slide-up" style={{ animationDelay: `${index * 50}ms` }}>
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
        </div>

        {/* Right Column - Stats & Achievements */}
        <div className="space-y-6">
          {/* Learning Stats */}
          <Card padding="lg">
            <h2 className="section-title mb-6">Learning Statistics</h2>
            <div className="space-y-4">
              <div className="flex items-center gap-4 p-3 bg-clario-surface-50 rounded-xl">
                <div className="w-10 h-10 rounded-xl bg-clario-primary-100 text-clario-primary-600 flex items-center justify-center">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-clario-surface-500">Total Concepts</p>
                  <p className="font-display font-bold text-xl text-clario-surface-900">{totalConcepts}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-4 p-3 bg-clario-surface-50 rounded-xl">
                <div className="w-10 h-10 rounded-xl bg-clario-success-100 text-clario-success-600 flex items-center justify-center">
                  <CheckCircle className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-clario-surface-500">Mastered</p>
                  <p className="font-display font-bold text-xl text-clario-surface-900">{masteredCount}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-4 p-3 bg-clario-surface-50 rounded-xl">
                <div className="w-10 h-10 rounded-xl bg-clario-warning-100 text-clario-warning-600 flex items-center justify-center">
                  <RotateCcw className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-clario-surface-500">In Remediation</p>
                  <p className="font-display font-bold text-xl text-clario-surface-900">{remediatingCount}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-4 p-3 bg-clario-surface-50 rounded-xl">
                <div className="w-10 h-10 rounded-xl bg-clario-secondary-100 text-clario-secondary-600 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-clario-surface-500">Current Difficulty</p>
                  <p className="font-display font-bold text-xl text-clario-surface-900">
                    {dashboard.concept_breakdown.find(c => c.status === 'learning' || c.status === 'remediating')?.difficulty || '—'}/5
                  </p>
                </div>
              </div>
            </div>
          </Card>

          {/* Weekly Activity */}
          <Card padding="lg">
            <h2 className="section-title mb-6">Weekly Activity</h2>
            <div className="space-y-3">
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, i) => {
                const isActive = i < new Date().getDay() || (i === new Date().getDay() && Math.random() > 0.5);
                return (
                  <div key={day} className="flex items-center justify-between p-3 bg-clario-surface-50 rounded-xl">
                    <span className="text-sm font-medium text-clario-surface-700">{day}</span>
                    <div className="flex items-center gap-2">
                      <div className={cn('w-2 h-2 rounded-full', isActive ? 'bg-clario-primary-500' : 'bg-clario-surface-200')} />
                      <span className="text-sm text-clario-surface-500">{isActive ? 'Active' : '—'}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Achievements */}
          <Card padding="lg">
            <h2 className="section-title mb-6">Achievements</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                { id: 'first', label: 'First Steps', desc: 'Complete your first concept', icon: Target, earned: true },
                { id: 'streak3', label: '3-Day Streak', desc: 'Learn for 3 days in a row', icon: Flame, earned: streak >= 3 },
                { id: 'streak7', label: 'Week Warrior', desc: 'Learn for 7 days in a row', icon: Flame, earned: streak >= 7 },
                { id: 'master5', label: 'High Five', desc: 'Master 5 concepts', icon: Trophy, earned: masteredCount >= 5 },
                { id: 'master10', label: 'Deca Master', desc: 'Master 10 concepts', icon: Award, earned: masteredCount >= 10 },
                { id: 'remediate', label: 'Comeback King', desc: 'Complete a remediation session', icon: RotateCcw, earned: remediatingCount > 0 },
              ].map(({ label, desc, icon: Icon, earned }) => (
                <div key={label} className={cn('p-4 rounded-xl border-2 flex items-center gap-3', earned ? 'border-clario-primary-200 bg-clario-primary-50' : 'border-clario-surface-200 bg-clario-surface-50 opacity-60')}>
                  <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', earned ? 'bg-clario-primary-100 text-clario-primary-600' : 'bg-clario-surface-200 text-clario-surface-400')}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={cn('font-semibold truncate', earned ? 'text-clario-surface-900' : 'text-clario-surface-500')}>{label}</p>
                    <p className={cn('text-sm truncate', earned ? 'text-clario-surface-600' : 'text-clario-surface-400')}>{desc}</p>
                  </div>
                  {earned && <CheckCircle className="w-5 h-5 text-clario-success-500" />}
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}