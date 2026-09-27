import { cn } from '../utils/helpers';
import { Badge, ProgressBar, Button } from './index';
import { CheckCircle, XCircle, Target, Award } from 'lucide-react';

interface QuizOptionProps {
  option: {
    id: string;
    text: string;
    isSelected: boolean;
    isCorrect: boolean | null;
  };
  onSelect: () => void;
  disabled?: boolean;
}

export function QuizOption({ option, onSelect, disabled }: QuizOptionProps) {
  const isSelected = option.isSelected;
  const isCorrect = option.isCorrect;
  const isIncorrect = option.isSelected && option.isCorrect === false;

  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled}
      className={cn(
        'quiz-option',
        isSelected && 'quiz-option-selected',
        isCorrect && 'quiz-option-correct',
        isIncorrect && 'quiz-option-incorrect',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
      aria-pressed={isSelected}
      aria-label={option.text}
    >
      <div className="flex items-center gap-4">
        <div className={cn(
          'flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center font-semibold transition-all duration-200',
          isCorrect ? 'bg-clario-success-500 text-white' :
          isIncorrect ? 'bg-clario-attention-500 text-white' :
          isSelected ? 'bg-clario-primary-500 text-white' :
          'bg-clario-surface-100 text-clario-surface-600 border-2 border-clario-surface-200'
        )}>
          {isCorrect ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          ) : isIncorrect ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            option.id
          )}
        </div>
        <span className="flex-1 text-left text-clario-surface-900">
          {option.text}
        </span>
      </div>
    </button>
  );
}

interface QuizProgressProps {
  current: number;
  total: number;
  difficulty: number;
}

export function QuizProgress({ current, total, difficulty }: QuizProgressProps) {
  const percentage = (current / total) * 100;

  const difficultyLabels = {
    1: 'Very Easy',
    2: 'Easy',
    3: 'Medium',
    4: 'Hard',
    5: 'Expert',
  };

  const difficultyColors = {
    1: 'success',
    2: 'success',
    3: 'warning',
    4: 'attention',
    5: 'attention',
  };

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-clario-surface-700">
          Question {current} of {total}
        </span>
        <Badge variant={difficultyColors[difficulty as keyof typeof difficultyColors] as 'success' | 'warning' | 'attention'} size="sm">
          {difficultyLabels[difficulty as keyof typeof difficultyLabels] || `Level ${difficulty}`}
        </Badge>
      </div>
      <ProgressBar value={percentage} max={100} size="md" variant="primary" animated />
    </div>
  );
}

interface QuizFeedbackProps {
  isCorrect: boolean;
  explanation?: string;
  onNext?: () => void;
  nextLabel?: string;
}

export function QuizFeedback({ isCorrect, explanation, onNext, nextLabel = 'Continue' }: QuizFeedbackProps) {
  return (
    <div className={cn('animate-scale-in', isCorrect ? 'bg-clario-success-50 border-clario-success-200' : 'bg-clario-attention-50 border-clario-attention-200')} style={{ borderWidth: '2px', borderStyle: 'solid', borderRadius: '1rem', padding: '1.5rem' }}>
      <div className="flex items-start gap-3">
        <div className={cn('flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center', isCorrect ? 'bg-clario-success-500' : 'bg-clario-attention-500')}>
          {isCorrect ? (
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          )}
        </div>
        <div className="flex-1">
          <h3 className={cn('font-display font-bold', isCorrect ? 'text-clario-success-700' : 'text-clario-attention-700')}>
            {isCorrect ? 'Correct!' : 'Not quite right'}
          </h3>
          {explanation && (
            <p className={cn('mt-2 text-clario-surface-600', isCorrect ? 'text-clario-success-600' : 'text-clario-attention-600')}>
              {explanation}
            </p>
          )}
        </div>
      </div>
      {onNext && (
        <Button variant={isCorrect ? 'success' : 'primary'} className="mt-4 w-full" onClick={onNext}>
          {nextLabel}
        </Button>
      )}
    </div>
  );
}