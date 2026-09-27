import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  Card, Button, Badge, ProgressBar, QuizOption, QuizProgress, 
  QuizFeedback, FeedbackCard, EvaluationFeedback, LoadingSpinner,
  LoadingOverlay, SkeletonLearning, EmptyState
} from '../components';
import { useLearningSession, useAuth } from '../hooks';
import { cn } from '../utils/helpers';
import { 
  Lightbulb, Brain, Zap, Award, Trophy, 
  CheckCircle, XCircle, ChevronRight, 
  RotateCcw, MessageSquare, BookOpen,
  Sparkles, Target
} from 'lucide-react';

const STAGE_ORDER = ['teaching', 'thinking', 'practical', 'quiz', 'evaluation', 'completed'] as const;

type Stage = typeof STAGE_ORDER[number];

const stageIcons: Record<Stage, any> = {
  teaching: Lightbulb,
  thinking: Brain,
  practical: Zap,
  quiz: Award,
  evaluation: Trophy,
  completed: CheckCircle,
};

const stageLabels: Record<Stage, string> = {
  teaching: 'Learn',
  thinking: 'Think',
  practical: 'Apply',
  quiz: 'Quiz',
  evaluation: 'Review',
  completed: 'Complete',
};

const stageDescriptions: Record<Stage, string> = {
  teaching: 'Understand the concept',
  thinking: 'Reason through the idea',
  practical: 'Apply in practice',
  quiz: 'Test your knowledge',
  evaluation: 'See your progress',
  completed: 'Concept mastered',
};

export function LearnPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const { userId, profile } = useAuth();
  const { 
    session, 
    isLoading: sessionLoading, 
    error: sessionError,
    startSession,
    submitThinking,
    submitPractical,
    generateQuiz,
    submitQuiz,
    triggerRemediation,
    fetchSession,
    clearError,
    resetSession,
  } = useLearningSession();

  const [currentStage, setCurrentStage] = useState<Stage | 'completed'>('teaching');
  const [teachingData, setTeachingData] = useState<any>(null);
  const [thinkingData, setThinkingData] = useState<any>(null);
  const [practicalData, setPracticalData] = useState<any>(null);
  const [quizData, setQuizData] = useState<any>(null);
  const [evaluationData, setEvaluationData] = useState<any>(null);
  const [quizState, setQuizState] = useState<{
    questionId: string;
    questionText: string;
    options: any[];
    selectedOption: string | null;
    isSubmitted: boolean;
    isCorrect: boolean | null;
    progress: { current: number; total: number };
    difficulty: number;
  } | null>(null);
  const [thinkingResponse, setThinkingResponse] = useState('');
  const [practicalResponse, setPracticalResponse] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRemediation, setShowRemediation] = useState(false);
  const [remediationData, setRemediationData] = useState<any>(null);

  // Sync stage from session
  useEffect(() => {
    if (sessionId) {
      void fetchSession(sessionId).catch((error: unknown) => {
        console.error('Failed to load learning session:', error);
      });
    }
  }, [fetchSession, sessionId]);

  useEffect(() => {
    if (session?.current_step) {
      const stage = session.current_step as Stage | 'completed';
      if (STAGE_ORDER.includes(stage) || stage === 'completed') {
        setCurrentStage(stage);
      }
    }
  }, [session?.current_step]);

  useEffect(() => {
    if (session?.current_step === 'teaching') {
      setTeachingData(session.current_content);
    }
  }, [session?.current_content, session?.current_step]);

  // Load thinking question when entering thinking stage
  useEffect(() => {
    if (currentStage === 'thinking' && session && !thinkingData) {
      setThinkingData({
        question: `Why does ${session.current_concept_title || 'this concept'} work the way it does? What would happen if we changed a key assumption?`,
        probing_type: 'why',
      });
    }
  }, [currentStage, session, thinkingData]);

  // Load practical exercise when entering practical stage
  useEffect(() => {
    if (currentStage === 'practical' && session && !practicalData) {
      setPracticalData({
        scenario_title: `${session.current_concept_title || 'Concept'} in Action`,
        practical_type: 'case_study',
        scenario_description: `Imagine you're working on a real project where you need to apply ${session.current_concept_title || 'this concept'}. Here's a scenario...`,
        task_prompt: `How would you apply what you've learned to solve this problem?`,
        hints: ['Break down the problem', 'Apply the key principles', 'Check your results'],
      });
    }
  }, [currentStage, session, practicalData]);

  // Load quiz when entering quiz stage
  useEffect(() => {
    if (currentStage === 'quiz' && session && !quizData) {
      loadQuiz();
    }
  }, [currentStage, session, quizData]);

  const loadQuiz = async () => {
    if (!session) return;
    setIsSubmitting(true);
    try {
      const result = await generateQuiz(session.session_id);
      if (result.question) {
        setQuizData(result.question);
        setQuizState({
          questionId: result.question.question_id,
          questionText: result.question.question_text,
          options: result.question.options?.map((opt: string, i: number) => ({
            id: String.fromCharCode(65 + i),
            text: opt,
            isSelected: false,
            isCorrect: null,
          })) || [],
          selectedOption: null,
          isSubmitted: false,
          isCorrect: null,
          progress: { current: 1, total: 1 },
          difficulty: result.question.difficulty,
        });
      }
    } catch (err) {
      console.error('Failed to load quiz:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleThinkingSubmit = async () => {
    if (!session || !thinkingResponse.trim()) return;
    setIsSubmitting(true);
    try {
      const result = await submitThinking(session.session_id, thinkingResponse);
      setThinkingData(result.thinking_assessment);
      setPracticalData(result.practical_exercise);
      setCurrentStage('practical');
      setThinkingResponse('');
    } catch (err) {
      console.error('Failed to submit thinking:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePracticalSubmit = async () => {
    if (!session || !practicalResponse.trim()) return;
    setIsSubmitting(true);
    try {
      const result = await submitPractical(session.session_id, practicalResponse);
      if (result.question) {
        setQuizData(result.question);
        setQuizState({
          questionId: result.question.question_id,
          questionText: result.question.question_text,
          options: result.question.options?.map((opt: string, i: number) => ({
            id: String.fromCharCode(65 + i),
            text: opt,
            isSelected: false,
            isCorrect: null,
          })) || [],
          selectedOption: null,
          isSubmitted: false,
          isCorrect: null,
          progress: { current: 1, total: 1 },
          difficulty: result.question.difficulty,
        });
        setCurrentStage('quiz');
      }
    } catch (err) {
      console.error('Failed to submit practical:', err);
    } finally {
      setIsSubmitting(false);
      setPracticalResponse('');
    }
  };

  const handleQuizOptionSelect = (optionId: string) => {
    if (quizState?.isSubmitted) return;
    setQuizState(prev => prev ? {
      ...prev,
      options: prev.options.map(opt => ({
        ...opt,
        isSelected: opt.id === optionId,
      })),
      selectedOption: optionId,
    } : null);
  };

  const handleQuizSubmit = async () => {
    if (!session || !quizState?.selectedOption) return;
    setIsSubmitting(true);
    try {
      const selectedOpt = quizState.options.find(o => o.id === quizState.selectedOption);
      const result = await submitQuiz(session.session_id, selectedOpt?.text || '');
      
      setEvaluationData({
        concept: result.evaluation.concept,
        status: result.evaluation.status,
        reasoningScore: result.evaluation.reasoning_score,
        misconceptions: result.evaluation.misconceptions,
        strongAreas: result.evaluation.status === 'mastered' ? ['Core concept understanding', 'Application skills'] : [],
        practiceAreas: result.evaluation.misconceptions || ['Review key principles'],
        difficultyChange: { from: session.difficulty_level, to: session.difficulty_level },
        nextAction: result.next_step,
      });
      
      setQuizState(prev => prev ? {
        ...prev,
        isSubmitted: true,
        isCorrect: result.evaluation.status === 'mastered',
        options: prev.options.map(opt => ({
          ...opt,
          isCorrect: opt.id === quizState.selectedOption ? (result.evaluation.status === 'mastered') : 
                      opt.text === result.evaluation.concept ? true : null,
        })),
      } : null);
      
      if (result.next_step.action === 'advance' || result.next_step.action === 'topic_completed') {
        setCurrentStage('evaluation');
      } else if (result.next_step.action === 'remediate') {
        setShowRemediation(true);
      }
    } catch (err) {
      console.error('Failed to submit quiz:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemediationStart = async () => {
    if (!session) return;
    setIsSubmitting(true);
    try {
      const result = await triggerRemediation(session.session_id);
      setRemediationData(result.teaching_explanation);
      setShowRemediation(true);
      setCurrentStage('teaching');
    } catch (err) {
      console.error('Failed to trigger remediation:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleContinue = () => {
    if (evaluationData?.nextAction.action === 'topic_completed') {
      navigate('/dashboard');
    } else {
      // Reset for next concept
      setTeachingData(null);
      setThinkingData(null);
      setPracticalData(null);
      setQuizData(null);
      setQuizState(null);
      setEvaluationData(null);
      setShowRemediation(false);
      setRemediationData(null);
      setCurrentStage('teaching');
    }
  };

  const renderStageIndicator = () => (
    <div className="flex items-center justify-between mb-6">
      {STAGE_ORDER.map((stage, index) => {
        const isCompleted = STAGE_ORDER.indexOf(currentStage) > index;
        const isCurrent = STAGE_ORDER.indexOf(currentStage) === index;
        const isFuture = STAGE_ORDER.indexOf(currentStage) < index;
        
        const Icon = stageIcons[stage] || BookOpen;
        
        return (
          <div key={stage} className="flex items-center">
            <div className={cn(
              'w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300',
              isCompleted ? 'bg-clario-success-500 text-white' :
              isCurrent ? 'bg-clario-primary-500 text-white ring-4 ring-clario-primary-500/20' :
              'bg-clario-surface-200 text-clario-surface-500'
            )}>
              {isCompleted ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <Icon className="w-5 h-5" />
              )}
            </div>
            {index < STAGE_ORDER.length - 1 && (
              <div className={cn(
                'w-16 h-0.5 mx-2',
                isCompleted ? 'bg-clario-success-500' : 'bg-clario-surface-200'
              )} />
            )}
          </div>
        );
      })}
    </div>
  );

  const renderTeaching = () => (
    <div className="learning-stage space-y-6">
      {!teachingData && (
        <FeedbackCard
          type="warning"
          title="Lesson content unavailable"
          message="This session has no teaching content to display. Return to the dashboard and start a new session."
        />
      )}
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-xl bg-clario-primary-100 text-clario-primary-600 flex items-center justify-center flex-shrink-0">
          <Lightbulb className="w-6 h-6" />
        </div>
        <div>
          <h3 className="font-display font-bold text-xl text-clario-surface-900">
            {teachingData?.concept || session?.current_concept_title || 'Concept'}
          </h3>
          <p className="text-clario-surface-500 text-sm mt-1">Understand the core idea</p>
        </div>
      </div>

      <div className="prose max-w-none text-clario-surface-700">
        <p className="mb-4">{teachingData?.explanation}</p>
        
        {teachingData?.analogy && (
          <div className="bg-clario-primary-50 border-l-4 border-clario-primary-500 p-4 rounded-r-xl my-4">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-5 h-5 text-clario-primary-600" />
              <span className="font-semibold text-clario-primary-800">Analogy</span>
            </div>
            <p className="text-clario-primary-700">{teachingData.analogy}</p>
          </div>
        )}

        {teachingData?.intuitive_example && (
          <div className="bg-clario-surface-50 rounded-xl p-4 my-4">
            <div className="flex items-center gap-2 mb-2">
              <BookOpen className="w-5 h-5 text-clario-surface-500" />
              <span className="font-semibold text-clario-surface-700">Example</span>
            </div>
            <p className="text-clario-surface-600">{teachingData.intuitive_example}</p>
          </div>
        )}

        {teachingData?.step_by_step_breakdown && teachingData.step_by_step_breakdown.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-semibold text-clario-surface-900">Step by Step</h4>
            {teachingData.step_by_step_breakdown.map((step: string, i: number) => (
              <div key={i} className="flex gap-3 p-3 bg-clario-surface-50 rounded-xl">
                <span className="flex-shrink-0 w-8 h-8 rounded-full bg-clario-primary-100 text-clario-primary-600 flex items-center justify-center font-bold text-sm">
                  {i + 1}
                </span>
                <p className="text-clario-surface-700 mt-1">{step}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {teachingData?.check_for_understanding_prompt && (
        <div className="bg-clario-secondary-50 border-l-4 border-clario-secondary-500 p-4 rounded-r-xl">
          <div className="flex items-center gap-2 mb-2">
            <MessageSquare className="w-5 h-5 text-clario-secondary-600" />
            <span className="font-semibold text-clario-secondary-800">Check Your Understanding</span>
          </div>
          <p className="text-clario-secondary-700">{teachingData.check_for_understanding_prompt}</p>
        </div>
      )}

      <Button 
        variant="primary" 
        size="lg" 
        fullWidth 
        onClick={() => setCurrentStage('thinking')}
        rightIcon={<ChevronRight className="w-4 h-4" />}
      >
        I Understand - Continue
      </Button>
    </div>
  );

  const renderThinking = () => (
    <div className="learning-stage space-y-6">
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-xl bg-clario-secondary-100 text-clario-secondary-600 flex items-center justify-center flex-shrink-0">
          <Brain className="w-6 h-6" />
        </div>
        <div>
          <h3 className="font-display font-bold text-xl text-clario-surface-900">Critical Thinking</h3>
          <p className="text-clario-surface-500 text-sm mt-1">Reason through the concept</p>
        </div>
      </div>

      <div className="bg-clario-secondary-50 border-l-4 border-clario-secondary-500 p-5 rounded-r-xl">
        <p className="text-clario-secondary-800 text-lg font-medium">{thinkingData?.question}</p>
      </div>

      <div>
        <label className="label">Your Explanation</label>
        <textarea
          value={thinkingResponse}
          onChange={(e) => setThinkingResponse(e.target.value)}
          placeholder="Explain your reasoning... Why does this work? What would happen if...?"
          className="input min-h-[120px] resize-y"
          rows={6}
        />
        <p className="text-sm text-clario-surface-500 mt-2">
          Take your time. There's no wrong answer here - we want to understand your thinking.
        </p>
      </div>

      <Button 
        variant="primary" 
        size="lg" 
        fullWidth 
        onClick={handleThinkingSubmit}
        disabled={isSubmitting || !thinkingResponse.trim()}
        rightIcon={isSubmitting ? <LoadingSpinner size="sm" /> : <ChevronRight className="w-4 h-4" />}
      >
        {isSubmitting ? 'Analyzing...' : 'Submit Reasoning'}
      </Button>
    </div>
  );

  const renderPractical = () => (
    <div className="learning-stage space-y-6">
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-xl bg-clario-warning-100 text-clario-warning-600 flex items-center justify-center flex-shrink-0">
          <Zap className="w-6 h-6" />
        </div>
        <div>
          <h3 className="font-display font-bold text-xl text-clario-surface-900">{practicalData?.scenario_title || 'Practical Application'}</h3>
          <p className="text-clario-surface-500 text-sm mt-1">Apply what you've learned</p>
        </div>
      </div>

      <div className="prose max-w-none text-clario-surface-700">
        <p className="mb-4">{practicalData?.scenario_description}</p>
        
        <div className="bg-clario-warning-50 border-l-4 border-clario-warning-500 p-4 rounded-r-xl my-4">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-5 h-5 text-clario-warning-600" />
            <span className="font-semibold text-clario-warning-800">Your Task</span>
          </div>
          <p className="text-clario-warning-700 font-medium">{practicalData?.task_prompt}</p>
        </div>

        {practicalData?.hints && practicalData.hints.length > 0 && (
          <div className="space-y-2">
            <h4 className="font-semibold text-clario-surface-900">Hints</h4>
            {practicalData.hints.map((hint: string, i: number) => (
              <div key={i} className="flex gap-3 p-3 bg-clario-surface-50 rounded-xl">
                <span className="flex-shrink-0 w-8 h-8 rounded-full bg-clario-warning-100 text-clario-warning-600 flex items-center justify-center font-bold text-sm">
                  {i + 1}
                </span>
                <p className="text-clario-surface-700 mt-1">{hint}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="label">Your Solution</label>
        <textarea
          value={practicalResponse}
          onChange={(e) => setPracticalResponse(e.target.value)}
          placeholder="Describe how you'd apply this concept to solve the problem..."
          className="input min-h-[120px] resize-y"
          rows={6}
        />
      </div>

      <Button 
        variant="primary" 
        size="lg" 
        fullWidth 
        onClick={handlePracticalSubmit}
        disabled={isSubmitting || !practicalResponse.trim()}
        rightIcon={isSubmitting ? <LoadingSpinner size="sm" /> : <ChevronRight className="w-4 h-4" />}
      >
        {isSubmitting ? 'Generating Quiz...' : 'Submit & Continue to Quiz'}
      </Button>
    </div>
  );

  const renderQuiz = () => {
    if (!quizState || isSubmitting) {
      return (
        <div className="learning-stage flex flex-col items-center justify-center py-12">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-clario-surface-500">Loading quiz...</p>
        </div>
      );
    }

    const selectedOption = quizState.options.find(o => o.id === quizState.selectedOption);

    return (
      <div className="learning-stage space-y-6">
        <QuizProgress 
          current={quizState.progress.current} 
          total={quizState.progress.total} 
          difficulty={quizState.difficulty} 
        />

        <div className="text-center mb-4">
          <Badge variant="primary" size="sm">Question {quizState.progress.current} of {quizState.progress.total}</Badge>
        </div>

        <h3 className="font-display font-bold text-xl text-clario-surface-900 text-center mb-6">
          {quizState.questionText}
        </h3>

        <div className="space-y-3">
          {quizState.options.map((option) => (
            <QuizOption
              key={option.id}
              option={option}
              onSelect={() => handleQuizOptionSelect(option.id)}
              disabled={quizState.isSubmitted}
            />
          ))}
        </div>

        {quizState.isSubmitted && selectedOption && (
          <QuizFeedback
            isCorrect={quizState.isCorrect || false}
            explanation={quizState.isCorrect ? 'Great job! You understood the concept correctly.' : 'Review the concept and try again.'}
            onNext={quizState.isCorrect ? handleContinue : undefined}
            nextLabel={quizState.isCorrect ? 'Continue' : 'Try Again'}
          />
        )}

        {!quizState.isSubmitted && (
          <Button 
            variant="primary" 
            size="lg" 
            fullWidth 
            onClick={handleQuizSubmit}
            disabled={!quizState.selectedOption || isSubmitting}
            rightIcon={isSubmitting ? <LoadingSpinner size="sm" /> : <ChevronRight className="w-4 h-4" />}
          >
            {isSubmitting ? 'Submitting...' : 'Check Answer'}
          </Button>
        )}
      </div>
    );
  };

  const renderEvaluation = () => {
    if (!evaluationData) return null;
    
    return (
      <EvaluationFeedback
        {...evaluationData}
        onContinue={handleContinue}
      />
    );
  };

  const renderRemediation = () => {
    if (!remediationData) return null;

    return (
      <div className="learning-stage space-y-6 animate-slide-up">
        <FeedbackCard
          type="warning"
          title="Let's Practice More"
          message={`We're going to revisit ${remediationData.concept} with a different approach to help you master it.`}
        />

        <div className="prose max-w-none text-clario-surface-700">
          <h3 className="font-display font-bold text-xl text-clario-surface-900 mb-4">
            {remediationData.concept} - Alternative Explanation
          </h3>
          <p className="mb-4">{remediationData.explanation}</p>

          {remediationData.analogy && (
            <div className="bg-clario-warning-50 border-l-4 border-clario-warning-500 p-4 rounded-r-xl my-4">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-5 h-5 text-clario-warning-600" />
                <span className="font-semibold text-clario-warning-800">New Analogy</span>
              </div>
              <p className="text-clario-warning-700">{remediationData.analogy}</p>
            </div>
          )}

          {remediationData.intuitive_example && (
            <div className="bg-clario-surface-50 rounded-xl p-4 my-4">
              <div className="flex items-center gap-2 mb-2">
                <BookOpen className="w-5 h-5 text-clario-surface-500" />
                <span className="font-semibold text-clario-surface-700">New Example</span>
              </div>
              <p className="text-clario-surface-600">{remediationData.intuitive_example}</p>
            </div>
          )}

          {remediationData.step_by_step_breakdown && remediationData.step_by_step_breakdown.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-semibold text-clario-surface-900">Step by Step</h4>
              {remediationData.step_by_step_breakdown.map((step: string, i: number) => (
                <div key={i} className="flex gap-3 p-3 bg-clario-surface-50 rounded-xl">
                  <span className="flex-shrink-0 w-8 h-8 rounded-full bg-clario-warning-100 text-clario-warning-600 flex items-center justify-center font-bold text-sm">
                    {i + 1}
                  </span>
                  <p className="text-clario-surface-700 mt-1">{step}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <Button 
          variant="primary" 
          size="lg" 
          fullWidth 
          onClick={() => { setShowRemediation(false); setCurrentStage('thinking'); }}
          rightIcon={<ChevronRight className="w-4 h-4" />}
        >
          Continue to Practice
        </Button>
      </div>
    );
  };

  const renderCompleted = () => (
    <div className="learning-stage text-center py-12">
      <div className="w-24 h-24 rounded-full bg-clario-success-100 flex items-center justify-center mx-auto mb-6 animate-bounce-in">
        <CheckCircle className="w-12 h-12 text-clario-success-500" />
      </div>
      <h2 className="font-display font-bold text-3xl text-clario-surface-900 mb-2">Concept Complete!</h2>
      <p className="text-clario-surface-500 text-lg mb-8">You've mastered {session?.current_concept_title || 'this concept'}</p>
      
      <Button 
        variant="success" 
        size="lg" 
        onClick={() => navigate('/dashboard')}
        rightIcon={<ChevronRight className="w-4 h-4" />}
      >
        Back to Dashboard
      </Button>
    </div>
  );

  // Check if we need to start a session
  if (sessionError && !session) {
    return (
      <div className="page-container max-w-3xl">
        <EmptyState
          title="Unable to load learning session"
          message={sessionError}
          action={{ label: 'Go to Dashboard', onClick: () => navigate('/dashboard') }}
        />
      </div>
    );
  }

  if (!session && !sessionLoading && !sessionId) {
    return (
      <div className="page-container max-w-3xl">
        <EmptyState
          title="No learning session selected"
          message="Start a learning session from onboarding or the dashboard."
          action={{ label: 'Go to Dashboard', onClick: () => navigate('/dashboard') }}
        />
      </div>
    );
  }

  if (sessionLoading || !session) {
    return (
      <div className="page-container max-w-3xl">
        <SkeletonLearning />
      </div>
    );
  }

  const currentStageIndex = STAGE_ORDER.indexOf(currentStage as Stage);
  const learningProgress = currentStageIndex < 0 ? 0 : ((currentStageIndex + 1) / STAGE_ORDER.length) * 100;

  return (
    <div className="page-container max-w-3xl">
      <LoadingOverlay isLoading={isSubmitting} message="Processing...">
        {/* Header */}
        <div className="mb-6 animate-slide-up">
          <Card padding="md" className="mb-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-clario-ink-2">Topic</p>
                <p className="font-black text-clario-ink">{session.topic_title}</p>
                <p className="mt-1 text-sm text-clario-ink-2">
                  Current concept: <span className="font-bold text-clario-ink">{session.current_concept_title || 'Not selected'}</span>
                </p>
              </div>
              <div className="sm:min-w-56">
                <div className="mb-1 flex justify-between text-sm">
                  <span className="font-bold text-clario-ink">{stageLabels[currentStage as Stage] || session.current_step}</span>
                  <span className="text-clario-ink-2">{Math.round(learningProgress)}%</span>
                </div>
                <ProgressBar value={learningProgress} max={100} size="sm" />
              </div>
            </div>
            <p className="mt-3 border-t border-clario-line-2 pt-3 text-sm text-clario-ink-2">
              <span className="font-bold text-clario-ink">Current action:</span> {session.current_action}
            </p>
          </Card>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
            <div>
              <p className="text-clario-primary-600 font-medium">{stageLabels[currentStage as Stage] || 'Learning'}</p>
              <h1 className="font-display font-bold text-2xl text-clario-surface-900 mt-1">
                {session?.current_concept_title || 'Learning Session'}
              </h1>
            </div>
            <div className="flex items-center gap-3">
              <Badge status={session?.is_remediating ? 'remediating' : 'learning'} size="md">
                {session?.is_remediating ? 'Practice Mode' : `Level ${session?.difficulty_level}`}
              </Badge>
              <ProgressBar value={STAGE_ORDER.indexOf(currentStage as Stage) + 1} max={STAGE_ORDER.length} size="sm" className="w-32" />
            </div>
          </div>

          {sessionError && (
            <div className="mb-4 p-4 bg-clario-attention-50 border border-clario-attention-200 rounded-xl flex items-center justify-between">
              <p className="text-clario-attention-700">{sessionError}</p>
              <Button variant="ghost" size="sm" onClick={clearError}>Dismiss</Button>
            </div>
          )}

          {renderStageIndicator()}
        </div>

        {/* Main Content */}
        <Card padding="lg" className="animate-slide-up">
          {currentStage === 'teaching' && renderTeaching()}
          {currentStage === 'thinking' && renderThinking()}
          {currentStage === 'practical' && renderPractical()}
          {currentStage === 'quiz' && renderQuiz()}
          {currentStage === 'evaluation' && renderEvaluation()}
          {currentStage === 'completed' && renderCompleted()}
          {showRemediation && renderRemediation()}
        </Card>
      </LoadingOverlay>
    </div>
  );
}