import { cn } from '../utils/helpers';
import { Button, Card, ProgressBar, Badge } from './index';
import { 
  CheckCircle, XCircle, AlertCircle, MessageSquare, 
  Sparkles, Target, Trophy, TrendingUp, RotateCcw,
  BookOpen, Award, Flame, Calendar, Clock
} from 'lucide-react';

interface FeedbackCardProps {
  type: 'success' | 'error' | 'warning' | 'info' | 'celebration';
  title: string;
  message?: string;
  children?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary' | 'success';
  };
  className?: string;
}

const typeStyles = {
  success: 'bg-clario-success-50 border-clario-success-200 text-clario-success-800',
  error: 'bg-clario-attention-50 border-clario-attention-200 text-clario-attention-800',
  warning: 'bg-clario-warning-50 border-clario-warning-200 text-clario-warning-800',
  info: 'bg-clario-primary-50 border-clario-primary-200 text-clario-primary-800',
  celebration: 'bg-gradient-to-br from-clario-primary-50 to-clario-secondary-50 border-clario-primary-200 text-clario-primary-800',
};

const typeIcons = {
  success: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
    </svg>
  ),
  error: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  warning: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  info: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  celebration: (
    <svg className="w-6 h-6 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
};

export function FeedbackCard({ type, title, message, children, action, className }: FeedbackCardProps) {
  return (
    <div className={cn('border-2 rounded-2xl p-5 animate-slide-up', typeStyles[type], className)}>
      <div className="flex items-start gap-3">
        <div className={cn('flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center', 
          type === 'celebration' ? 'bg-clario-primary-500/20' : `${typeStyles[type].replace('bg-', 'bg-').replace('text-', 'bg-').replace('border-', 'bg-')} text-white`
        )}>
          {typeIcons[type]}
        </div>
        <div className="flex-1">
          <h3 className="font-display font-bold text-lg">{title}</h3>
          {message && <p className="mt-1 opacity-90">{message}</p>}
          {children && <div className="mt-3">{children}</div>}
          {action && (
            <Button
              variant={action.variant || 'primary'}
              className="mt-4"
              onClick={action.onClick}
            >
              {action.label}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

interface EvaluationFeedbackProps {
  concept: string;
  status: 'mastered' | 'remediating' | 'learning';
  reasoningScore: number;
  misconceptions: string[];
  strongAreas: string[];
  practiceAreas: string[];
  difficultyChange: { from: number; to: number };
  nextAction: {
    action: 'advance' | 'remediate' | 'continue';
    companion: string;
    concept: string;
    instructions: string;
  };
  onContinue: () => void;
}

export function EvaluationFeedback({
  concept,
  status,
  reasoningScore,
  misconceptions,
  strongAreas,
  practiceAreas,
  difficultyChange,
  nextAction,
  onContinue,
}: EvaluationFeedbackProps) {
  const isMastered = status === 'mastered';
  const isRemediating = status === 'remediating';

  return (
    <div className="space-y-6 animate-slide-up">
      <FeedbackCard
        type={isMastered ? 'celebration' : isRemediating ? 'warning' : 'info'}
        title={isMastered ? 'Concept Mastered!' : isRemediating ? 'Let\'s Practice More' : 'Good Progress'}
        message={isMastered 
          ? `You've mastered ${concept} with ${Math.round(reasoningScore)}% understanding!`
          : isRemediating
          ? `${concept} needs more practice. We'll approach it differently.`
          : `You're making progress on ${concept}. Keep going!`
        }
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Card variant="hover" padding="md">
          <div className="flex items-center gap-2 mb-3">
            <svg className="w-5 h-5 text-clario-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h4 className="font-semibold text-clario-surface-900">Strong Areas</h4>
          </div>
          <ul className="space-y-2">
            {strongAreas.length > 0 ? (
              strongAreas.map((area, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-clario-surface-600">
                  <svg className="w-4 h-4 text-clario-success-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {area}
                </li>
              ))
            ) : (
              <li className="text-sm text-clario-surface-500">Complete the lesson to see strong areas</li>
            )}
          </ul>
        </Card>

        <Card variant="hover" padding="md">
          <div className="flex items-center gap-2 mb-3">
            <svg className="w-5 h-5 text-clario-warning-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h4 className="font-semibold text-clario-surface-900">Practice Areas</h4>
          </div>
          <ul className="space-y-2">
            {practiceAreas.length > 0 ? (
              practiceAreas.map((area, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-clario-surface-600">
                  <svg className="w-4 h-4 text-clario-warning-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  {area}
                </li>
              ))
            ) : (
              <li className="text-sm text-clario-surface-500">No specific areas identified</li>
            )}
          </ul>
        </Card>
      </div>

      {misconceptions.length > 0 && (
        <Card variant="hover" padding="md" className="border-clario-attention-200 bg-clario-attention-50">
          <div className="flex items-center gap-2 mb-3">
            <svg className="w-5 h-5 text-clario-attention-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <h4 className="font-semibold text-clario-attention-800">Misconceptions to Address</h4>
          </div>
          <ul className="space-y-2">
            {misconceptions.map((m, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-clario-attention-700">
                <svg className="w-4 h-4 text-clario-attention-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {m}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card variant="hover" padding="md" className="bg-clario-primary-50 border-clario-primary-200">
        <div className="flex items-center gap-2 mb-3">
          <svg className="w-5 h-5 text-clario-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
          </svg>
          <h4 className="font-semibold text-clario-primary-800">Difficulty Adjustment</h4>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <span className="text-sm text-clario-surface-600">From Level {difficultyChange.from}</span>
            <div className="mt-1 flex items-center gap-2">
              <div className="flex-1 h-2 bg-clario-surface-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-clario-primary-500 rounded-full transition-all duration-1000 ease-out"
                  style={{ width: `${(difficultyChange.to / 5) * 100}%` }}
                />
              </div>
              <span className="text-sm font-medium text-clario-primary-600">Level {difficultyChange.to}</span>
            </div>
          </div>
        </div>
      </Card>

      <Button variant={isMastered ? 'success' : 'primary'} size="lg" fullWidth onClick={onContinue} className="animate-bounce-in">
        {nextAction.action === 'advance' ? 'Continue to Next Concept' : 
         nextAction.action === 'remediate' ? 'Start Practice Session' : 
         'Continue Learning'}
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
        </svg>
      </Button>
    </div>
  );
}