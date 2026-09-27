import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: unknown[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map(part => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'mastered': return 'success';
    case 'remediating': return 'warning';
    case 'learning': return 'primary';
    case 'upcoming': return 'neutral';
    default: return 'neutral';
  }
}

export function getStatusLabel(status: string): string {
  switch (status) {
    case 'mastered': return 'Mastered';
    case 'remediating': return 'Needs Practice';
    case 'learning': return 'Learning';
    case 'upcoming': return 'Upcoming';
    default: return status;
  }
}

export function getDifficultyLabel(level: number): string {
  switch (level) {
    case 1: return 'Very Easy';
    case 2: return 'Easy';
    case 3: return 'Medium';
    case 4: return 'Hard';
    case 5: return 'Expert';
    default: return `Level ${level}`;
  }
}