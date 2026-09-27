import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { cn } from '../utils/helpers';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'success' | 'attention' | 'blue' | 'purple' | 'orange' | 'red';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    variant = 'primary',
    size = 'md',
    isLoading = false,
    leftIcon,
    rightIcon,
    fullWidth = false,
    className,
    disabled,
    children,
    ...props
  }, ref) => {
    const variantClasses = {
      primary: 'bg-clario-green text-white shadow-clario-btn-green hover:brightness-110 active:translate-y-1 active:shadow-none',
      secondary: 'bg-clario-blue text-white shadow-clario-btn-blue hover:brightness-110 active:translate-y-1 active:shadow-none',
      ghost: 'bg-white text-clario-green border-2 border-clario-line shadow-clario-btn-line hover:bg-clario-bg-2 active:translate-y-1 active:shadow-none',
      success: 'bg-clario-green text-white shadow-clario-btn-green hover:brightness-110 active:translate-y-1 active:shadow-none',
      attention: 'bg-clario-red text-white shadow-clario-btn-red hover:brightness-110 active:translate-y-1 active:shadow-none',
      blue: 'bg-clario-blue text-white shadow-clario-btn-blue hover:brightness-110 active:translate-y-1 active:shadow-none',
      purple: 'bg-clario-purple text-white shadow-clario-btn-purple hover:brightness-110 active:translate-y-1 active:shadow-none',
      orange: 'bg-clario-orange text-white shadow-clario-btn-orange hover:brightness-110 active:translate-y-1 active:shadow-none',
      red: 'bg-clario-red text-white shadow-clario-btn-red hover:brightness-110 active:translate-y-1 active:shadow-none',
    };

    const sizeClasses = {
      sm: 'px-4 py-2 text-xs rounded-clario-sm',
      md: 'px-6 py-3 text-sm rounded-clario-md',
      lg: 'px-8 py-4 text-base rounded-clario-lg',
      icon: 'w-10 h-10 p-0 rounded-clario-md',
    };

    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2 font-extrabold uppercase tracking-wider transition-all duration-75 select-none whitespace-nowrap',
          variantClasses[variant],
          sizeClasses[size],
          fullWidth && 'w-full',
          disabled && 'bg-clario-line text-clario-ink-3 shadow-none cursor-not-allowed transform-none pointer-events-none',
          className
        )}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && (
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )}
        {!isLoading && leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
        {children}
        {!isLoading && rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';