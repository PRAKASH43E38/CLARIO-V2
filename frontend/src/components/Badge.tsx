import { cn } from '../utils/helpers';
import { getStatusColor, getStatusLabel } from '../utils/helpers';

interface BadgeProps {
  children?: React.ReactNode;
  variant?: 'primary' | 'success' | 'warning' | 'attention' | 'neutral' | 'status' | 'blue' | 'purple' | 'orange' | 'red' | 'yellow' | 'teal';
  status?: 'mastered' | 'remediating' | 'learning' | 'upcoming';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  icon?: React.ReactNode;
}

export function Badge({
  children,
  variant = 'neutral',
  status,
  size = 'md',
  className,
  icon,
}: BadgeProps) {
  const variantClasses = {
    primary: 'bg-clario-green-t text-clario-green-deep',
    success: 'bg-clario-green-t text-clario-green-deep',
    warning: 'bg-clario-orange-t text-clario-orange-sh',
    attention: 'bg-clario-red-t text-clario-red-sh',
    neutral: 'bg-clario-bg-2 text-clario-ink-2',
    status: '',
    blue: 'bg-clario-blue-t text-clario-blue-sh',
    purple: 'bg-clario-purple-t text-clario-purple-sh',
    orange: 'bg-clario-orange-t text-clario-orange-sh',
    red: 'bg-clario-red-t text-clario-red-sh',
    yellow: 'bg-clario-yellow-t text-clario-yellow-sh',
    teal: 'bg-clario-teal-t text-clario-teal-sh',
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-3 py-1 text-xs',
    lg: 'px-4 py-1.5 text-sm',
  };

  let statusVariant: any = 'neutral';
  if (status) {
    const color = getStatusColor(status);
    statusVariant = color;
  }

  const effectiveVariant = status ? statusVariant : variant;
  const effectiveLabel = status ? getStatusLabel(status) : children;

  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full font-black uppercase tracking-wider',
      variantClasses[effectiveVariant as keyof typeof variantClasses],
      sizeClasses[size],
      className
    )}>
      {icon && <span className="flex-shrink-0">{icon}</span>}
      {effectiveLabel}
    </span>
  );
}

interface XPBadgeProps {
  xp: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function XPBadge({ xp, size = 'md', showLabel = true }: XPBadgeProps) {
  const sizeClasses = {
    sm: 'px-3 py-1.5 rounded-clario-md',
    md: 'px-4 py-2 rounded-clario-lg',
    lg: 'px-6 py-3 rounded-clario-xl',
  };

  const textSizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-xl',
  };

  const labelSizeClasses = {
    sm: 'text-xs',
    md: 'text-xs',
    lg: 'text-sm',
  };

  return (
    <div className={cn('bg-clario-green text-white flex items-center gap-2 font-black shadow-clario-btn-green', sizeClasses[size])}>
      <span className={cn(textSizeClasses[size])}>
        {xp.toLocaleString()}
      </span>
      {showLabel && (
        <span className={cn('opacity-90', labelSizeClasses[size])}>
          XP
        </span>
      )}
    </div>
  );
}

interface StreakBadgeProps {
  streak: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function StreakBadge({ streak, size = 'md', showLabel = true }: StreakBadgeProps) {
  const sizeClasses = {
    sm: 'px-3 py-1.5 rounded-clario-md',
    md: 'px-4 py-2 rounded-clario-lg',
    lg: 'px-6 py-3 rounded-clario-xl',
  };

  const textSizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-xl',
  };

  const labelSizeClasses = {
    sm: 'text-xs',
    md: 'text-xs',
    lg: 'text-sm',
  };

  return (
    <div className={cn('bg-clario-orange text-white flex items-center gap-2 font-black shadow-clario-btn-orange', sizeClasses[size])}>
      <svg className={cn('w-5 h-5', size === 'sm' && 'w-4 h-4', size === 'lg' && 'w-6 h-6')} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 0 16.09 0.777 17.656 2.343A7.975 7.975 0 0120 6a7.975 7.975 0 01-2.343 5.657z" />
      </svg>
      <span className={cn(textSizeClasses[size])}>
        {streak}
      </span>
      {showLabel && (
        <span className={cn('opacity-90', labelSizeClasses[size])}>
          Day Streak
        </span>
      )}
    </div>
  );
}