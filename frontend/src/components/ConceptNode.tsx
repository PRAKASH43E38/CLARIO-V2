import { cn } from '../utils/helpers';
import { getDifficultyLabel } from '../utils/helpers';
import { Badge } from './Badge';

interface ConceptNodeProps {
  concept: {
    id: string;
    title: string;
    status: 'mastered' | 'remediating' | 'learning' | 'upcoming';
    difficulty: number;
    isCurrent: boolean;
    isNext: boolean;
  };
  showConnector?: boolean;
  onClick?: () => void;
  className?: string;
}

const statusIcons = {
  mastered: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
    </svg>
  ),
  remediating: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  learning: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  upcoming: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
};

export function ConceptNode({ concept, showConnector = true, onClick, className }: ConceptNodeProps) {
  const statusClasses = {
    mastered: 'concept-node-completed',
    remediating: 'concept-node-remediating',
    learning: 'concept-node-learning',
    upcoming: 'concept-node-upcoming',
  };

  const isActive = concept.isCurrent || concept.isNext;

  return (
    <div className={cn('concept-node flex flex-col items-center gap-2', className)} onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      <div className="relative flex flex-col items-center gap-2">
        <div className={cn(
          'concept-node-circle flex items-center justify-center font-bold text-lg transition-all duration-300',
          statusClasses[concept.status],
          concept.isCurrent && 'concept-node-current',
          concept.isNext && 'concept-node-current',
        )}>
          {statusIcons[concept.status]}
        </div>
        
        <div className="text-center min-w-[100px]">
          <p className={cn(
            'font-medium text-sm transition-colors duration-200',
            concept.isCurrent ? 'text-clario-primary-600' :
            concept.status === 'mastered' ? 'text-clario-success-600' :
            concept.status === 'remediating' ? 'text-clario-warning-600' :
            'text-clario-surface-700'
          )}>
            {concept.title}
          </p>
          <Badge status={concept.status} size="sm" />
          <div className="flex items-center justify-center gap-1 mt-1">
            <svg className="w-3 h-3 text-clario-surface-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <span className="text-xs text-clario-surface-500">{getDifficultyLabel(concept.difficulty)}</span>
          </div>
        </div>
      </div>

      {showConnector && (
        <div className={cn(
          'concept-node-connector',
          (concept.isCurrent || concept.isNext || concept.status === 'mastered') && 'concept-node-connector-active'
        )} />
      )}
    </div>
  );
}

interface ConceptPathProps {
  concepts: Array<{
    id: string;
    title: string;
    status: 'mastered' | 'remediating' | 'learning' | 'upcoming';
    difficulty: number;
    isCurrent: boolean;
    isNext: boolean;
  }>;
  onConceptClick?: (conceptId: string) => void;
  className?: string;
}

export function ConceptPath({ concepts, onConceptClick, className }: ConceptPathProps) {
  return (
    <div className={cn('flex flex-col items-center', className)}>
      {concepts.map((concept, index) => (
        <ConceptNode
          key={concept.id}
          concept={concept}
          showConnector={index < concepts.length - 1}
          onClick={() => onConceptClick?.(concept.id)}
        />
      ))}
    </div>
  );
}