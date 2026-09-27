import { cn } from '../utils/helpers';

interface ProgressBarProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'success' | 'warning' | 'attention' | 'blue' | 'purple' | 'orange';
  showLabel?: boolean;
  label?: string;
  animated?: boolean;
  className?: string;
}

export function ProgressBar({
  value,
  max = 100,
  size = 'md',
  variant = 'primary',
  showLabel = false,
  label,
  animated = true,
  className,
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const sizeClasses = {
    sm: 'h-2',
    md: 'h-4',
    lg: 'h-6',
  };

  const variantClasses = {
    primary: 'bg-gradient-to-r from-clario-green to-clario-green-hi',
    success: 'bg-gradient-to-r from-clario-green to-clario-green-hi',
    warning: 'bg-gradient-to-r from-clario-orange to-clario-orange-hi',
    attention: 'bg-gradient-to-r from-clario-red to-clario-red-hi',
    blue: 'bg-gradient-to-r from-clario-blue to-clario-blue-sh',
    purple: 'bg-gradient-to-r from-clario-purple to-clario-purple-sh',
    orange: 'bg-gradient-to-r from-clario-orange to-clario-orange-sh',
  };

  return (
    <div className={cn('w-full', className)}>
      {(showLabel || label) && (
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-black uppercase tracking-wider text-clario-ink-2">
            {label || `${Math.round(percentage)}%`}
          </span>
          {showLabel && (
            <span className="text-xs font-bold text-clario-ink-3">
              {value} / {max}
            </span>
          )}
        </div>
      )}
      <div className={cn('relative w-full bg-clario-line rounded-full overflow-hidden', sizeClasses[size])}>
        <div
          className={cn(
            'h-full rounded-full transition-all duration-700 ease-out',
            variantClasses[variant],
            animated ? 'progress-fill' : ''
          )}
          style={{ width: `${percentage}%`, '--progress-width': `${percentage}%` } as React.CSSProperties}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
          aria-label={label || 'Progress'}
        />
      </div >
    </div>
  );
}

interface CircularProgressProps {
  value: number;
  max?: number;
  size?: number;
  strokeWidth?: number;
  variant?: 'primary' | 'success' | 'warning' | 'attention';
  showValue?: boolean;
  className?: string;
}

export function CircularProgress({
  value,
  max = 100,
  size = 80,
  strokeWidth = 6,
  variant = 'primary',
  showValue = true,
  className,
}: CircularProgressProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  const variantClasses = {
    primary: 'text-clario-green',
    success: 'text-clario-green',
    warning: 'text-clario-orange',
    attention: 'text-clario-red',
  };

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)} style={{ width: size, height: size }}>
      <svg className="progress-ring" width={size} height={size}>
        <circle
          className="progress-ring-bg text-clario-line"
          strokeWidth={strokeWidth}
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        <circle
          className={cn('progress-ring-fill', variantClasses[variant])}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
          style={{ transition: 'stroke-dashoffset 1s ease-out' }}
        />
      </svg>
      {showValue && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-black text-clario-ink" style={{ fontSize: size * 0.25 }}>
            {Math.round(percentage)}%
          </span>
        </div>
      )}
    </div >
  );
}

interface StepProgressProps {
  currentStep: number;
  totalSteps: number;
  stepLabels?: string[];
  className?: string;
}

export function StepProgress({ currentStep, totalSteps, stepLabels, className }: StepProgressProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      {Array.from({ length: totalSteps }, (_, i) => {
        const step = i + 1;
        const isCompleted = step < currentStep;
        const isCurrent = step === currentStep;
        const isLast = step === totalSteps;

        return (
          <div key={step} className="flex items-center">
            <div className="relative flex items-center">
              <div className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center font-black text-sm transition-all duration-300',
                isCompleted ? 'bg-clario-green text-white' :
                isCurrent ? 'bg-clario-blue text-white ring-4 ring-clario-blue-t' :
                'bg-clario-line text-clario-ink-3'
              )}>
                {isCompleted ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  step
                )}
              </div >
              {stepLabels && stepLabels[i] && (
                <span className={cn(
                  'absolute -left-4 w-24 text-center text-[10px] font-black uppercase tracking-wider whitespace-nowrap',
                  isCurrent ? 'text-clario-blue-sh' : 'text-clario-ink-3'
                )}>
                  {stepLabels[i]}
                </span>
              )}
            </div >
            {!isLast && (
              <div className={cn(
                'w-16 h-0.5 mx-2',
                isCompleted ? 'bg-clario-green' : 'bg-clario-line'
              )} />
            )}
          </div >
        );
      })}
    </div >
  );
}