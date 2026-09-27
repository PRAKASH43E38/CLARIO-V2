export type ConceptStatus = 'mastered' | 'remediating' | 'learning' | 'upcoming';

export interface ConceptNode {
  id: string;
  title: string;
  status: ConceptStatus;
  difficulty: number;
  isCurrent: boolean;
  isNext: boolean;
}

export interface LearningProgress {
  xp: number;
  streak: number;
  dailyGoal: number;
  conceptsMastered: number;
  conceptsTotal: number;
  level: number;
  levelProgress: number;
}

export interface SessionState {
  sessionId: string | null;
  currentConcept: string | null;
  currentStage: LearningStage;
  progress: number;
  xpEarned: number;
  isLoading: boolean;
}

export type LearningStage = 'teaching' | 'thinking' | 'practical' | 'quiz' | 'evaluation' | 'completed';

export interface QuizOption {
  id: string;
  text: string;
  isSelected: boolean;
  isCorrect: boolean | null;
}

export interface QuizState {
  questionId: string;
  questionText: string;
  options: QuizOption[];
  selectedOption: string | null;
  isSubmitted: boolean;
  isCorrect: boolean | null;
  progress: {
    current: number;
    total: number;
  };
  difficulty: number;
}

export interface EvaluationState {
  concept: string;
  status: ConceptStatus;
  reasoningScore: number;
  misconceptions: string[];
  strongAreas: string[];
  practiceAreas: string[];
  difficultyChange: {
    from: number;
    to: number;
  };
  nextAction: {
    action: 'advance' | 'remediate' | 'continue';
    companion: string;
    concept: string;
    instructions: string;
  };
}

export interface OnboardingState {
  step: number;
  totalSteps: number;
  data: Partial<{
    learning_goal: string;
    current_level: 'beginner' | 'intermediate' | 'advanced';
    learning_preference: 'step_by_step' | 'example_first' | 'practical_first';
    interests: string[];
    initial_confidence: number;
  }>;
  isSubmitting: boolean;
}

export interface NavigationItem {
  id: string;
  label: string;
  icon: string;
  href: string;
  badge?: number | string;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
}