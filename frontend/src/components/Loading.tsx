import { cn } from '../utils/helpers';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
  };

  return (
    <svg className={cn('animate-spin text-clario-primary-500', sizeClasses[size], className)} viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );
}

interface LoadingOverlayProps {
  isLoading: boolean;
  children: React.ReactNode;
  message?: string;
}

export function LoadingOverlay({ isLoading, children, message }: LoadingOverlayProps) {
  return (
    <div className="relative">
      {children}
      {isLoading && (
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-10 rounded-2xl">
          <div className="flex flex-col items-center gap-4 p-6">
            <LoadingSpinner size="lg" />
            {message && <p className="text-clario-surface-600 font-medium">{message}</p>}
          </div>
        </div>
      )}
    </div>
  );
}

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return <div className={cn('skeleton animate-pulse', className)} />;
}

export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className={cn('skeleton h-4 rounded', i === lines - 1 && 'w-3/4')} />
      ))}
    </div>
  );
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn('skeleton-card animate-pulse', className)} />
  );
}

export function SkeletonDashboard({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-6', className)}>
      <SkeletonText lines={2} className="max-w-xs" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }, (_, i) => (
          <SkeletonCard key={i} className="h-32" />
        ))}
      </div>
      <SkeletonCard className="h-48" />
      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: 4 }, (_, i) => (
          <SkeletonCard key={i} className="h-24" />
        ))}
      </div>
    </div>
  );
}

export function SkeletonRoadmap({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-8', className)}>
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="flex flex-col items-center gap-2">
          <div className="skeleton w-16 h-16 rounded-full" />
          <div className="skeleton w-24 h-4 rounded" />
          <div className="skeleton w-20 h-3 rounded" />
          {i < 4 && <div className="skeleton w-1 h-24" />}
        </div>
      ))}
    </div>
  );
}

export function SkeletonLearning({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-6', className)}>
      <SkeletonText lines={1} className="max-w-md" />
      <SkeletonText lines={5} />
      <div className="space-y-3">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="skeleton h-14 rounded-xl" />
        ))}
      </div>
    </div>
  );
}