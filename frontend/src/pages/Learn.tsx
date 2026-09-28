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
    <div className="flex items-center justify-between mb-12 px-4 sm:px-0">
      {STAGE_ORDER.map((stage, index) => {
        const isCompleted = STAGE_ORDER.indexOf(currentStage) > index;
        const isCurrent = STAGE_ORDER.indexOf(currentStage) === index;

        const Icon = stageIcons[stage] || BookOpen;

        return (
          <div key={stage} className="flex items-center flex-1">
            <div className="relative flex flex-col items-center group">
              <div className={cn(
                'w-12 h-12 rounded-2xl flex items-center justify-center font-bold text-sm transition-all duration-300 z-10 shadow-soft',
                isCompleted ? 'bg-clario-green text-white' :
                isCurrent ? 'bg-white text-clario-green ring-4 ring-clario-green-t shadow-xl scale-110' :
                'bg-slate-200 text-slate-400'
              )}>
                {isCompleted ? (
                  <CheckCircle className="w-6 h-6" />
                ) : (
                  <Icon className="w-6 h-6" />
                )}
              </div>
              <span className={cn(
                'absolute -bottom-6 text-[10px] font-black uppercase tracking-tighter transition-opacity duration-300',
                isCurrent ? 'opacity-100 text-clario-green' : 'opacity-0 group-hover:opacity-100 text-slate-400'
              )}>
                {stageLabels[stage]}
              </span>
            </div>
            {index < STAGE_ORDER.length - 1 && (
              <div className={cn(
                'h-1 flex-1 mx-2 rounded-full transition-colors duration-500',
                isCompleted ? 'bg-clario-green' : 'bg-slate-200'
              )} />
            )}
          </div>
        );
      })}
    </div>
  );

  const renderTeaching = () => (
    <div className="learning-stage space-y-8 animate-slide-up">
      {!teachingData && (
        <FeedbackCard
          type="warning"
          title="Lesson content unavailable"
          message="This session has no teaching content to display. Return to the dashboard and start a new session."
        />
      )}

      <div className="flex items-center gap-4 mb-8">
        <div className="w-14 h-14 rounded-2xl bg-clario-green-t text-clario-green flex items-center justify-center shadow-soft">
          <Lightbulb className="w-8 h-8" />
        </div>
        <div>
          <h3 className="font-display font-black text-3xl text-slate-900 tracking-tight">
            {teachingData?.concept || session?.current_concept_title || 'Concept'}
          </h3>
          <p className="text-slate-500 font-bold text-sm uppercase tracking-widest">Master the fundamentals</p>
        </div>
      </div>

      <div className="space-y-8 text-lg leading-relaxed text-slate-700">
        <p className="font-medium">{teachingData?.explanation}</p>

        {teachingData?.analogy && (
          <div className="bg-clario-green-t/30 border-l-8 border-clario-green p-6 rounded-r-2xl relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
              <Sparkles className="w-24 h-24 text-clario-green" />
            </div>
            <div className="relative z-10">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-5 h-5 text-clario-green" />
                <span className="font-black uppercase tracking-widest text-xs text-clario-green-deep">Mental Model</span>
              </div>
              <p className="text-clario-green-deep font-bold">{teachingData.analogy}</p>
            </div>
          </div>
        )}

        {teachingData?.intuitive_example && (
          <div className="bg-slate-100 p-6 rounded-2xl border-2 border-slate-200 relative">
            <div className="flex items-center gap-2 mb-3">
              <BookOpen className="w-5 h-5 text-slate-500" />
              <span className="font-black uppercase tracking-widest text-xs text-slate-500">Real-World Example</span>
            </div>
            <p className="text-slate-600 italic">{teachingData.intuitive_example}</p>
          </div>
        )}

        {teachingData?.step_by_step_breakdown && teachingData.step_by_step_breakdown.length > 0 && (
          <div className="space-y-4">
            <h4 className="font-display font-black text-xl text-slate-900">The Breakdown</h4>
            <div className="grid gap-4">
              {teachingData.step_by_step_breakdown.map((step: string, i: number) => (
                <div key={i} className="flex gap-4 p-5 bg-white rounded-2xl border-2 border-slate-100 shadow-sm hover:border-clario-green transition-colors group">
                  <span className="flex-shrink-0 w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center font-black text-sm group-hover:bg-clario-green transition-colors">
                    {i + 1}
                  </span>
                  <p className="text-slate-700 font-medium">{step}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {teachingData?.check_for_understanding_prompt && (
        <div className="bg-clario-blue-t/30 border-l-8 border-clario-blue p-6 rounded-r-2xl">
          <div className="flex items-center gap-2 mb-2">
            <MessageSquare className="w-5 h-5 text-clario-blue" />
            <span className="font-black uppercase tracking-widest text-xs text-clario-blue-deep">Think About This</span>
          </div>
          <p className="text-clario-blue-deep font-bold text-lg">{teachingData.check_for_understanding_prompt}</p>
        </div>
      )}

      <Button
        variant="primary"
        size="lg"
        fullWidth
        className="py-6 text-xl shadow-clario-btn-green transition-transform hover:scale-[1.01] active:scale-95"
        onClick={() => setCurrentStage('thinking')}
        rightIcon={<ChevronRight className="w-6 h-6" />}
      >
        Got it! Let's Think →
      </Button>
    </div>
  );

  const renderThinking = () => (
    <div className="learning-stage space-y-8 animate-slide-up">
      <div className="flex items-center gap-4 mb-8">
        <div className="w-14 h-14 rounded-2xl bg-clario-blue-t text-clario-blue flex items-center justify-center shadow-soft">
          <Brain className="w-8 h-8" />
        </div>
        <div>
          <h3 className="font-display font-black text-3xl text-slate-900 tracking-tight">Critical Thinking</h3>
          <p className="text-slate-500 font-bold text-sm uppercase tracking-widest">Deep dive into the logic</p>
        </div>
      </div>

      <div className="bg-white p-8 rounded-3xl border-4 border-clario-blue-t shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-clario-blue/5 rounded-full -mr-16 -mt-16 blur-3xl" />
        <p className="text-2xl font-bold text-slate-800 leading-snug relative z-10">
          {thinkingData?.question}
        </p>
      </div>

      <div className="space-y-4">
        <label className="font-black uppercase tracking-widest text-xs text-slate-400 ml-1">Your Reasoning</label>
        <textarea
          value={thinkingResponse}
          onChange={(e) => setThinkingResponse(e.target.value)}
          placeholder="Don't just give a short answer. Explain your logic, why you think this is the case, and what would happen if conditions changed..."
          className="input min-h-[200px] p-6 text-lg rounded-3xl border-2 border-slate-200 focus:border-clario-blue transition-all resize-none shadow-inner"
          rows={8}
        />
        <p className="text-sm text-slate-500 font-medium px-2">
          💡 Tip: Try to connect this to the analogy we used in the teaching stage.
        </p>
      </div>

      <Button
        variant="primary"
        size="lg"
        fullWidth
        className="py-6 text-xl shadow-clario-btn-green transition-transform hover:scale-[1.01] active:scale-95"
        onClick={handleThinkingSubmit}
        disabled={isSubmitting || !thinkingResponse.trim()}
        rightIcon={isSubmitting ? <LoadingSpinner size="sm" /> : <ChevronRight className="w-6 h-6" />}
      >
        {isSubmitting ? 'Analyzing Thinking...' : 'Submit Reasoning →'}
      </Button>
    </div>
  );

  const renderPractical = () => (
    <div className="learning-stage space-y-8 animate-slide-up">
      <div className="flex items-center gap-4 mb-8">
        <div className="w-14 h-14 rounded-2xl bg-orange-100 text-orange-600 flex items-center justify-center shadow-soft">
          <Zap className="w-8 h-8" />
        </div>
        <div>
          <h3 className="font-display font-black text-3xl text-slate-900 tracking-tight">{practicalData?.scenario_title || 'Practical Application'}</h3>
          <p className="text-slate-500 font-bold text-sm uppercase tracking-widest">Real-world scenario</p>
        </div>
      </div>

      <div className="space-y-8 text-lg leading-relaxed text-slate-700">
        <div className="bg-slate-50 p-8 rounded-3xl border-2 border-slate-200">
          <p className="font-medium">{practicalData?.scenario_description}</p>
        </div>

        <div className="bg-orange-50 border-l-8 border-orange-500 p-6 rounded-r-2xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Target className="w-24 h-24 text-orange-500" />
          </div>
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-5 h-5 text-orange-600" />
              <span className="font-black uppercase tracking-widest text-xs text-orange-700">The Mission</span>
            </div>
            <p className="text-orange-800 font-bold text-xl">{practicalData?.task_prompt}</p>
          </div>
        </div>

        {practicalData?.hints && practicalData.hints.length > 0 && (
          <div className="space-y-4">
            <h4 className="font-display font-black text-xl text-slate-900">Strategize with Hints</h4>
            <div className="grid gap-3">
              {practicalData.hints.map((hint: string, i: number) => (
                <div key={i} className="flex gap-4 p-4 bg-white rounded-2xl border-2 border-slate-100 shadow-sm hover:border-orange-200 transition-colors group">
                  <span className="flex-shrink-0 w-7 h-7 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center font-black text-xs">
                    {i + 1}
                  </span>
                  <p className="text-slate-600 font-medium">{hint}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="space-y-4">
        <label className="font-black uppercase tracking-widest text-xs text-slate-400 ml-1">Your Solution</label>
        <textarea
          value={practicalResponse}
          onChange={(e) => setPracticalResponse(e.target.value)}
          placeholder="Describe your solution step-by-step. How exactly does the concept apply here?"
          className="input min-h-[200px] p-6 text-lg rounded-3xl border-2 border-slate-200 focus:border-orange-500 transition-all resize-none shadow-inner"
          rows={8}
        />
      </div>

      <Button
        variant="primary"
        size="lg"
        fullWidth
        className="py-6 text-xl shadow-clario-btn-green transition-transform hover:scale-[1.01] active:scale-95"
        onClick={handlePracticalSubmit}
        disabled={isSubmitting || !practicalResponse.trim()}
        rightIcon={isSubmitting ? <LoadingSpinner size="sm" /> : <ChevronRight className="w-6 h-6" />}
      >
        {isSubmitting ? 'Generating Quiz...' : 'Verify Application →'}
      </Button>
    </div>
  );

  const renderQuiz = () => {
    if (!quizState || isSubmitting) {
      return (
        <div className="learning-stage flex flex-col items-center justify-center py-24">
          <LoadingSpinner size="lg" />
          <p className="mt-6 text-slate-500 font-bold uppercase tracking-widest animate-pulse">Preparing Challenge...</p>
        </div>
      );
    }

    const selectedOption = quizState.options.find(o => o.id === quizState.selectedOption);

    return (
      <div className="learning-stage space-y-8 animate-slide-up">
        <div className="flex items-center justify-between mb-4">
          <QuizProgress
            current={quizState.progress.current}
            total={quizState.progress.total}
            difficulty={quizState.difficulty}
          />
          <Badge variant="primary" size="sm">Quest {quizState.progress.current}/{quizState.progress.total}</Badge>
        </div>

        <div className="text-center mb-10">
          <h3 className="font-display font-black text-3xl text-slate-900 tracking-tight leading-tight">
            {quizState.questionText}
          </h3>
        </div>

        <div className="grid gap-4">
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
            explanation={quizState.isCorrect ? "Perfect! You've internalized the core logic of this concept." : "Not quite. Let's review the mistake and try to reconcile it with the lesson."}
            onNext={quizState.isCorrect ? handleContinue : undefined}
            nextLabel={quizState.isCorrect ? 'See Evaluation' : 'Try Again'}
          />
        )}

        {!quizState.isSubmitted && (
          <Button
            variant="primary"
            size="lg"
            fullWidth
            className="py-6 text-xl shadow-clario-btn-green transition-transform hover:scale-[1.01] active:scale-95"
            onClick={handleQuizSubmit}
            disabled={!quizState.selectedOption || isSubmitting}
            rightIcon={isSubmitting ? <LoadingSpinner size="sm" /> : <ChevronRight className="w-6 h-6" />}
          >
            {isSubmitting ? 'Evaluating...' : 'Check My Answer →'}
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
      <div className="learning-stage space-y-8 animate-slide-up">
        <FeedbackCard
          type="warning"
          title="Precision Tuning"
          message={`We've spotted a small gap in ${remediationData.concept}. Let's fix it with a different angle before we move on.`}
        />

        <div className="space-y-8 text-lg leading-relaxed text-slate-700">
          <h3 className="font-display font-black text-3xl text-slate-900 tracking-tight mb-4">
            {remediationData.concept} <span className="text-slate-400 font-medium">/ Alternative View</span>
          </h3>
          <p className="font-medium">{remediationData.explanation}</p>

          {remediationData.analogy && (
            <div className="bg-orange-50 border-l-8 border-orange-500 p-6 rounded-r-2xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <Sparkles className="w-24 h-24 text-orange-500" />
              </div>
              <div className="relative z-10">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-5 h-5 text-orange-600" />
                  <span className="font-black uppercase tracking-widest text-xs text-orange-700">Fresh Analogy</span>
                </div>
                <p className="text-orange-800 font-bold">{remediationData.analogy}</p>
              </div>
            </div>
          )}

          {remediationData.intuitive_example && (
            <div className="bg-slate-100 p-6 rounded-2xl border-2 border-slate-200">
              <div className="flex items-center gap-2 mb-3">
                <BookOpen className="w-5 h-5 text-slate-500" />
                <span className="font-black uppercase tracking-widest text-xs text-slate-500">New Perspective Example</span>
              </div>
              <p className="text-slate-600 italic">{remediationData.intuitive_example}</p>
            </div>
          )}

          {remediationData.step_by_step_breakdown && remediationData.step_by_step_breakdown.length > 0 && (
            <div className="space-y-4">
              <h4 className="font-display font-black text-xl text-slate-900">Refined Breakdown</h4>
              <div className="grid gap-4">
                {remediationData.step_by_step_breakdown.map((step: string, i: number) => (
                  <div key={i} className="flex gap-4 p-5 bg-white rounded-2xl border-2 border-slate-100 shadow-sm hover:border-orange-200 transition-colors group">
                    <span className="flex-shrink-0 w-8 h-8 rounded-lg bg-orange-100 text-orange-600 flex items-center justify-center font-black text-sm">
                      {i + 1}
                    </span>
                    <p className="text-slate-700 font-medium">{step}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <Button
          variant="primary"
          size="lg"
          fullWidth
          className="py-6 text-xl shadow-clario-btn-green transition-transform hover:scale-[1.01] active:scale-95"
          onClick={() => { setShowRemediation(false); setCurrentStage('thinking'); }}
          rightIcon={<ChevronRight className="w-6 h-6" />}
        >
          Try Again →
        </Button>
      </div>
    );
  };

  const renderCompleted = () => (
    <div className="learning-stage text-center py-24 animate-slide-up">
      <div className="w-32 h-32 rounded-full bg-clario-green/20 flex items-center justify-center mx-auto mb-8 animate-bounce-in relative">
        <div className="absolute inset-0 rounded-full bg-clario-green/10 animate-ping" />
        <CheckCircle className="w-16 h-16 text-clario-green relative z-10" />
      </div>
      <h2 className="font-display font-black text-5xl text-slate-900 mb-4 tracking-tight">Concept Mastered!</h2>
      <p className="text-slate-500 text-xl mb-12 max-w-md mx-auto font-medium">
        You've successfully conquered {session?.current_concept_title || 'this concept'}. Your neural pathways are now wired for success.
      </p>

      <Button
        variant="primary"
        size="lg"
        className="px-12 py-6 text-xl shadow-clario-btn-green transition-transform hover:scale-105"
        onClick={() => navigate('/dashboard')}
        rightIcon={<ChevronRight className="w-6 h-6" />}
      >
        Return to Journey
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
    <div className="page-container max-w-4xl">
      <LoadingOverlay isLoading={isSubmitting} message="Processing your brilliance...">
        {/* Top Navigation & Context */}
        <div className="mb-10 animate-slide-up">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6 mb-8">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-white shadow-soft flex items-center justify-center text-slate-400">
                <Target className="w-6 h-6" />
              </div>
              <div>
                <p className="text-slate-400 font-black uppercase tracking-widest text-[10px]">Current Path</p>
                <h1 className="font-display font-black text-2xl text-slate-900 tracking-tight">
                  {session.topic_title}
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-4 bg-white p-2 rounded-2xl shadow-sm border border-slate-100">
              <div className="px-3 py-1 rounded-lg bg-slate-50 text-slate-500 text-xs font-bold">
                Concept: {session.current_concept_title || 'Loading...'}
              </div>
              <div className="w-32 h-3 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-clario-green transition-all duration-500"
                  style={{ width: `${learningProgress}%` }}
                />
              </div>
              <span className="text-xs font-black text-slate-900 w-8 text-right">
                {Math.round(learningProgress)}%
              </span>
            </div>
          </div>

          {renderStageIndicator()}
        </div>

        {/* Main Learning Canvas */}
        <div className="relative">
          <Card padding="lg" className="animate-slide-up border-none shadow-xl bg-white rounded-3xl overflow-hidden">
            {currentStage === 'teaching' && renderTeaching()}
            {currentStage === 'thinking' && renderThinking()}
            {currentStage === 'practical' && renderPractical()}
            {currentStage === 'quiz' && renderQuiz()}
            {currentStage === 'evaluation' && renderEvaluation()}
            {currentStage === 'completed' && renderCompleted()}
            {showRemediation && renderRemediation()}
          </Card>
        </div>
      </LoadingOverlay>
    </div>
  );
}
