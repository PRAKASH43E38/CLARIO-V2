import { FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../components';
import { useAuth } from '../hooks';
import { api } from '../services';
import type {
  CalaResult,
  ClarioOrchestrationContext,
  ElaraEvaluation,
  ClarioAdaptiveDecision,
  SessionInputsRequest,
  ZaynQuizPresentation,
} from '../types';

const EMPTY_INPUTS: SessionInputsRequest = {
  task: '',
  goal: '',
  learner_state: '',
  interest: '',
};

export function OnboardingPage() {
  const navigate = useNavigate();
  const { userId, profileComplete, mindProfileComplete } = useAuth();
  const [inputs, setInputs] = useState(EMPTY_INPUTS);
  const [isStarting, setIsStarting] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [calaPlan, setCalaPlan] = useState<CalaResult | null>(null);
  const [orchestration, setOrchestration] = useState<ClarioOrchestrationContext | null>(null);
  const [isResearching, setIsResearching] = useState(false);
  const [isTeaching, setIsTeaching] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [thinkingError, setThinkingError] = useState<string | null>(null);
  const [isPracticing, setIsPracticing] = useState(false);
  const [practicalError, setPracticalError] = useState<string | null>(null);
  const [quiz, setQuiz] = useState<ZaynQuizPresentation | null>(null);
  const [quizError, setQuizError] = useState<string | null>(null);
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState(false);
  const [isSubmittingQuiz, setIsSubmittingQuiz] = useState(false);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, string>>({});
  const [quizRemainingSeconds, setQuizRemainingSeconds] = useState(0);
  const [evaluation, setEvaluation] = useState<ElaraEvaluation | null>(null);
  const [evaluationError, setEvaluationError] = useState<string | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [decision, setDecision] = useState<ClarioAdaptiveDecision | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [isDeciding, setIsDeciding] = useState(false);
  const [researchError, setResearchError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!userId) return null;
  if (!profileComplete) {
    navigate('/profile-setup', { replace: true });
    return null;
  }
  if (!mindProfileComplete) {
    navigate('/mind-profile', { replace: true });
    return null;
  }

  const updateInput = (key: keyof SessionInputsRequest, value: string) => {
    setInputs(previous => ({ ...previous, [key]: value }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsStarting(true);
    setError(null);
    try {
      const session = await api.createLearningSession(userId, inputs);
      setSessionId(session.session_id);
      await createPlan(session.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to start your learning session.');
    } finally {
      setIsStarting(false);
    }
  };

  const createPlan = async (id: string) => {
    setIsPlanning(true);
    setError(null);
    try {
      const plan = await api.createCalaPlan(userId, id);
      setCalaPlan(plan);
      setIsPlanning(false);
      await coordinateResearch(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to prepare your learning plan.');
    } finally {
      setIsPlanning(false);
    }
  };

  const coordinateResearch = async (id: string) => {
    setIsResearching(true);
    setResearchError(null);
    try {
      let state = await api.initializeOrchestration(userId, id);
      setOrchestration(state);
      if (!state.research_package) {
        state = await api.requestOrchestrationResearch(userId, id);
        setOrchestration(state);
      }
      if (state.current_state === 'RESEARCH_READY' || state.current_state === 'TEACHING_FAILED') {
        setIsResearching(false);
        setIsTeaching(true);
        state = await api.requestOrchestrationTeaching(userId, id);
        setOrchestration(state);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to retrieve learning sources.';
      setResearchError(message);
      try {
        setOrchestration(await api.getOrchestrationState(userId, id));
      } catch (stateError) {
        const stateMessage = stateError instanceof Error
          ? stateError.message
          : 'Unable to reload orchestration state.';
        setResearchError(`${message} ${stateMessage}`);
      }
    } finally {
      setIsResearching(false);
      setIsTeaching(false);
    }
  };
  const requestThinking = async (id: string) => {
    setIsThinking(true);
    setThinkingError(null);
    try {
      setOrchestration(await api.requestOrchestrationThinking(userId, id));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to prepare the thinking activity.';
      setThinkingError(message);
      try {
        setOrchestration(await api.getOrchestrationState(userId, id));
      } catch (stateError) {
        const stateMessage = stateError instanceof Error
          ? stateError.message
          : 'Unable to reload orchestration state.';
        setThinkingError(`${message} ${stateMessage}`);
      }
    } finally {
      setIsThinking(false);
    }
  };
  const requestPractical = async (id: string) => {
    setIsPracticing(true);
    setPracticalError(null);
    try {
      setOrchestration(await api.requestOrchestrationPractical(userId, id));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to prepare the practical activity.';
      setPracticalError(message);
      try {
        setOrchestration(await api.getOrchestrationState(userId, id));
      } catch (stateError) {
        const stateMessage = stateError instanceof Error
          ? stateError.message
          : 'Unable to reload orchestration state.';
        setPracticalError(`${message} ${stateMessage}`);
      }
    } finally {
      setIsPracticing(false);
    }
  };
  const startQuiz = async (id: string) => {
    setIsGeneratingQuiz(true);
    setQuizError(null);
    try {
      const generated = await api.requestOrchestrationQuiz(userId, id);
      setQuiz(generated);
      setQuizAnswers({});
      setQuizRemainingSeconds(generated.time_limit_seconds * generated.questions.length);
      setOrchestration(await api.getOrchestrationState(userId, id));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to prepare the quiz.';
      setQuizError(message);
      try {
        setOrchestration(await api.getOrchestrationState(userId, id));
      } catch (stateError) {
        const stateMessage = stateError instanceof Error
          ? stateError.message
          : 'Unable to reload orchestration state.';
        setQuizError(`${message} ${stateMessage}`);
      }
    } finally {
      setIsGeneratingQuiz(false);
    }
  };
  const submitQuiz = async (id: string) => {
    if (!quiz) return;
    setIsSubmittingQuiz(true);
    setQuizError(null);
    try {
      await api.submitZaynQuiz(userId, id, {
        quiz_id: quiz.quiz_id,
        answers: quizAnswers,
      });
      setQuiz(previous => previous ? { ...previous, status: 'SUBMITTED' } : previous);
      setOrchestration(await api.getOrchestrationState(userId, id));
    } catch (err) {
      setQuizError(err instanceof Error ? err.message : 'Unable to submit your answers.');
      try {
        setOrchestration(await api.getOrchestrationState(userId, id));
      } catch (stateError) {
        const stateMessage = stateError instanceof Error
          ? stateError.message
          : 'Unable to reload orchestration state.';
        setQuizError(previous => `${previous ?? 'Quiz submission failed.'} ${stateMessage}`);
      }
    } finally {
      setIsSubmittingQuiz(false);
    }
  };
  const evaluateLearning = async (id: string) => {
    setIsEvaluating(true);
    setEvaluationError(null);
    try {
      const result = await api.requestOrchestrationEvaluation(userId, id);
      setEvaluation(result);
      setOrchestration(await api.getOrchestrationState(userId, id));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to evaluate this learning cycle.';
      setEvaluationError(message);
      try {
        setOrchestration(await api.getOrchestrationState(userId, id));
      } catch (stateError) {
        const stateMessage = stateError instanceof Error
          ? stateError.message
          : 'Unable to reload orchestration state.';
        setEvaluationError(`${message} ${stateMessage}`);
      }
    } finally {
      setIsEvaluating(false);
    }
  };
  const requestDecision = async (id: string) => {
    setIsDeciding(true);
    setDecisionError(null);
    try {
      const result = await api.requestOrchestrationDecision(userId, id);
      setDecision(result);
      setOrchestration(await api.getOrchestrationState(userId, id));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to continue learning.';
      setDecisionError(message);
      try {
        setOrchestration(await api.getOrchestrationState(userId, id));
      } catch (stateError) {
        const stateMessage = stateError instanceof Error
          ? stateError.message
          : 'Unable to reload orchestration state.';
        setDecisionError(`${message} ${stateMessage}`);
      }
    } finally {
      setIsDeciding(false);
    }
  };

  useEffect(() => {
    if (!quiz || quiz.status !== 'IN_PROGRESS') return undefined;
    const timer = window.setInterval(() => {
      setQuizRemainingSeconds(remaining => Math.max(remaining - 1, 0));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [quiz?.quiz_id, quiz?.status]);

  const researchPackage = orchestration?.research_package ?? null;

  return (
    <div className="page-container max-w-3xl">
      <Card padding="lg">
        <p className="font-bold text-clario-primary-600">New learning session</p>
        {!sessionId && !calaPlan && (
          <>
            <h1 className="mt-2 text-3xl font-black text-clario-surface-900">What would you like to work on?</h1>
            <p className="mt-2 text-clario-surface-600">Indha session-ku mattum indha naalu inputs use panni learning plan prepare pannuvom.</p>
            <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <div>
            <label className="label" htmlFor="session-task">Task</label>
            <textarea id="session-task" className="input min-h-24" maxLength={1000} required value={inputs.task} onChange={event => updateInput('task', event.target.value)} placeholder="What do you want help doing?" />
          </div>
          <div>
            <label className="label" htmlFor="session-goal">Goal</label>
            <textarea id="session-goal" className="input min-h-24" maxLength={1000} required value={inputs.goal} onChange={event => updateInput('goal', event.target.value)} placeholder="What should you be able to do by the end?" />
          </div>
          <div>
            <label className="label" htmlFor="session-learner-state">Learner State</label>
            <textarea id="session-learner-state" className="input min-h-24" maxLength={1000} required value={inputs.learner_state} onChange={event => updateInput('learner_state', event.target.value)} placeholder="What have you tried or learned so far? Where are you currently getting stuck?" />
          </div>
          <div>
            <label className="label" htmlFor="session-interest">Interest</label>
            <textarea id="session-interest" className="input min-h-20" maxLength={500} required value={inputs.interest} onChange={event => updateInput('interest', event.target.value)} placeholder="What interests or real-world context should examples use?" />
          </div>
          {error && <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">{error}</p>}
          <Button type="submit" variant="primary" fullWidth disabled={isStarting || isPlanning}>
            {isStarting ? 'Creating your session...' : 'Prepare my learning plan'}
          </Button>
            </form>
          </>
        )}
        {isPlanning && (
          <div role="status" className="mt-6 rounded-2xl bg-clario-primary-50 p-5 text-clario-primary-800">
            <p className="font-bold">CALA is preparing your starting roadmap...</p>
            <p className="mt-1 text-sm">Your level estimate uses available evidence; unknown information stays unknown.</p>
          </div>
        )}
        {error && sessionId && !isPlanning && (
          <div className="mt-5 space-y-3">
            <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">{error}</p>
            <Button type="button" variant="primary" disabled={isPlanning} onClick={() => void createPlan(sessionId)}>
              Retry CALA planning
            </Button>
          </div>
        )}
        {calaPlan && (
          <section aria-labelledby="cala-roadmap-title" className="mt-8 space-y-5">
            <div>
              <p className="font-bold text-clario-primary-600">CALA learning plan</p>
              <h2 id="cala-roadmap-title" className="mt-1 text-2xl font-black text-clario-surface-900">
                Your starting roadmap
              </h2>
            </div>
            <Card padding="md" className="border-clario-primary-200 bg-clario-primary-50">
              <p><strong>Initial learner estimate:</strong> <span className="capitalize">{calaPlan.learner_level}</span></p>
              <p className="mt-1 text-sm text-clario-surface-700">{calaPlan.learner_level_reason}</p>
              <p className="mt-3"><strong>Recommended starting level:</strong> Level 1 · Beginner</p>
              <p className="mt-1 text-sm text-clario-surface-700">{calaPlan.recommended_starting_level_reason}</p>
              <p className="mt-3"><strong>Confidence:</strong> {calaPlan.confidence_state.level}</p>
              <p className="mt-1"><strong>Weakness:</strong> {calaPlan.weakness_type}</p>
            </Card>
            <div className="space-y-3">
              {calaPlan.roadmap.map(level => (
                <Card key={level.level_id} padding="md" className={level.is_unlocked ? 'border-clario-primary-300' : 'opacity-70'}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wide text-clario-surface-500">Level {level.order}</p>
                      <h3 className="text-lg font-black text-clario-surface-900">{level.title}</h3>
                      <p className="mt-1 text-sm text-clario-surface-600">{level.description}</p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-bold ${level.is_unlocked ? 'bg-clario-primary-100 text-clario-primary-800' : 'bg-clario-surface-100 text-clario-surface-600'}`}>
                      {level.is_unlocked ? 'Unlocked' : 'Locked'}
                    </span>
                  </div>
                  {level.topics.map(topic => (
                    <div key={topic.topic_id} className="mt-4 border-t border-clario-surface-200 pt-3">
                      <p className="font-bold text-clario-surface-900">{topic.title}</p>
                      {topic.description && <p className="mt-1 text-sm text-clario-surface-600">{topic.description}</p>}
                      <ol className="mt-3 list-inside list-decimal space-y-1 text-sm text-clario-surface-700">
                        {topic.concepts.map(concept => <li key={concept.concept_id}>{concept.title}</li>)}
                      </ol>
                    </div>
                  ))}
                </Card>
              ))}
            </div>
          </section>
        )}
        {calaPlan && sessionId && (
          <section aria-labelledby="research-title" className="mt-8 space-y-4">
            <div>
              <p className="font-bold text-clario-primary-600">CLARIO-AI · Research coordination</p>
              <h2 id="research-title" className="mt-1 text-2xl font-black text-clario-surface-900">
                Learning sources
              </h2>
            </div>
            {orchestration && (
              <p className="text-sm text-clario-surface-600">
                Workflow state: <strong>{orchestration.current_state}</strong>
              </p>
            )}
            {isResearching && (
              <div role="status" className="rounded-2xl bg-clario-primary-50 p-5 text-clario-primary-800">
                <p className="font-bold">CLARIO-AI is coordinating research for this session...</p>
              </div>
            )}
            {researchError && !isResearching && orchestration?.current_state !== 'TEACHING_FAILED' && (
              <div className="space-y-3">
                <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">{researchError}</p>
                <Button type="button" variant="primary" disabled={isResearching} onClick={() => void coordinateResearch(sessionId)}>
                  Retry research coordination
                </Button>
              </div>
            )}
            {researchPackage && (
              <div className="space-y-4">
                <Card padding="md" className="border-clario-primary-200 bg-clario-primary-50">
                  <p className="font-bold text-clario-surface-900">Research summary</p>
                  <p className="mt-2 text-sm text-clario-surface-700">{researchPackage.research_summary}</p>
                  <p className="mt-3 text-xs text-clario-surface-600">
                    {researchPackage.validation_information.sources_validated} validated · {researchPackage.validation_information.candidates_received} candidates
                  </p>
                </Card>
                {researchPackage.selected_sources.length === 0 ? (
                  <p className="rounded-xl bg-clario-surface-50 p-4 text-sm text-clario-surface-600">
                    No sources passed the relevance checks for this plan.
                  </p>
                ) : (
                  <ol className="space-y-3">
                    {researchPackage.selected_sources.map(source => (
                      <li key={source.source_id}>
                        <Card padding="md">
                          <h3 className="font-bold text-clario-surface-900">{source.title}</h3>
                          <p className="mt-1 text-xs text-clario-surface-500">{source.domain}</p>
                          <p className="mt-2 text-sm text-clario-surface-700">{source.snippet}</p>
                          <a
                            className="mt-3 inline-block text-sm font-bold text-clario-primary-700 underline"
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Open source
                          </a>
                        </Card>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            )}
            {isTeaching && (
              <div role="status" className="rounded-2xl bg-clario-primary-50 p-5 text-clario-primary-800">
                <p className="font-bold">Mira is preparing a lesson from your learning plan and research...</p>
              </div>
            )}
            {orchestration?.current_state === 'TEACHING_FAILED' && !isTeaching && (
              <div className="space-y-3">
                <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">
                  {researchError ?? 'Mira could not prepare the teaching response.'}
                </p>
                <Button type="button" variant="primary" onClick={() => void coordinateResearch(sessionId)}>
                  Retry teaching
                </Button>
              </div>
            )}
            {orchestration?.teaching_result && (
              <Card padding="lg" className="border-clario-primary-200">
                <p className="font-bold text-clario-primary-600">Mira · Teaching</p>
                <h3 className="mt-1 text-xl font-black text-clario-surface-900">
                  {orchestration.teaching_result.concept}
                </h3>
                <p className="mt-3 text-clario-surface-700">
                  {orchestration.teaching_result.explanation}
                </p>
                <h4 className="mt-5 font-bold text-clario-surface-900">Key points</h4>
                <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-clario-surface-700">
                  {orchestration.teaching_result.key_points.map((point, index) => (
                    <li key={`${index}-${point}`}>{point}</li>
                  ))}
                </ul>
                <h4 className="mt-5 font-bold text-clario-surface-900">Examples</h4>
                <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-clario-surface-700">
                  {orchestration.teaching_result.examples.map((example, index) => (
                    <li key={`${index}-${example}`}>{example}</li>
                  ))}
                </ul>
                {orchestration.teaching_result.source_references.length > 0 && (
                  <>
                    <h4 className="mt-5 font-bold text-clario-surface-900">Sources used</h4>
                    <ul className="mt-2 space-y-1 text-sm">
                      {orchestration.teaching_result.source_references.map(source => (
                        <li key={source.source_id}>
                          <a className="font-bold text-clario-primary-700 underline" href={source.url} target="_blank" rel="noopener noreferrer">
                            {source.title}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                <p className="mt-4 text-xs text-clario-surface-500">
                  {orchestration.teaching_result.learner_level} · {orchestration.teaching_result.teaching_style}
                </p>
              </Card>
            )}
            {orchestration?.current_state === 'TEACHING_READY' && !orchestration.thinking_result && (
              <div className="space-y-3">
                {thinkingError && <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">{thinkingError}</p>}
                <Button
                  type="button"
                  variant="primary"
                  disabled={isThinking}
                  onClick={() => void requestThinking(sessionId)}
                >
                  {isThinking ? 'Preparing Think activity...' : 'Continue to Think'}
                </Button>
              </div>
            )}
            {isThinking && (
              <div role="status" className="rounded-2xl bg-clario-primary-50 p-5 text-clario-primary-800">
                <p className="font-bold">CLARIO-AI is asking Ayan to prepare a reasoning prompt...</p>
              </div>
            )}
            {orchestration?.current_state === 'THINKING_FAILED' && !isThinking && (
              <div className="space-y-3">
                <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">
                  {thinkingError ?? 'Ayan could not prepare the thinking activity.'}
                </p>
                <Button type="button" variant="primary" onClick={() => void requestThinking(sessionId)}>
                  Retry Think activity
                </Button>
              </div>
            )}
            {orchestration?.thinking_result && (
              <Card padding="lg" className="border-clario-primary-200">
                <p className="font-bold text-clario-primary-600">Ayan · Think</p>
                <h3 className="mt-1 text-xl font-black text-clario-surface-900">
                  {orchestration.thinking_result.concept}
                </h3>
                <p className="mt-3 text-clario-surface-700">
                  {orchestration.thinking_result.thinking_prompt}
                </p>
                <h4 className="mt-5 font-bold text-clario-surface-900">Reasoning focus</h4>
                <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-clario-surface-700">
                  {orchestration.thinking_result.expected_reasoning_focus.map((item, index) => (
                    <li key={`${index}-${item}`}>{item}</li>
                  ))}
                </ul>
                <p className="mt-4 text-xs text-clario-surface-500">
                  Difficulty: {orchestration.thinking_result.difficulty}
                </p>
                {orchestration.thinking_result.source_references.length > 0 && (
                  <>
                    <h4 className="mt-5 font-bold text-clario-surface-900">Context sources</h4>
                    <ul className="mt-2 space-y-1 text-sm">
                      {orchestration.thinking_result.source_references.map(source => (
                        <li key={source.source_id}>
                          <a className="font-bold text-clario-primary-700 underline" href={source.url} target="_blank" rel="noopener noreferrer">
                            {source.title}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </Card>
            )}
            {orchestration?.current_state === 'THINKING_READY' && !orchestration.practical_result && (
              <div className="space-y-3">
                {practicalError && <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">{practicalError}</p>}
                <Button
                  type="button"
                  variant="primary"
                  disabled={isPracticing}
                  onClick={() => void requestPractical(sessionId)}
                >
                  {isPracticing ? 'Preparing practice activity...' : 'Continue to Practice'}
                </Button>
              </div>
            )}
            {isPracticing && (
              <div role="status" className="rounded-2xl bg-clario-primary-50 p-5 text-clario-primary-800">
                <p className="font-bold">CLARIO-AI is asking Kira to prepare a practical activity...</p>
              </div>
            )}
            {orchestration?.current_state === 'PRACTICAL_FAILED' && !isPracticing && (
              <div className="space-y-3">
                <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">
                  {practicalError ?? 'Kira could not prepare the practical activity.'}
                </p>
                <Button type="button" variant="primary" onClick={() => void requestPractical(sessionId)}>
                  Retry Practice activity
                </Button>
              </div>
            )}
            {orchestration?.practical_result && (
              <Card padding="lg" className="border-clario-primary-200">
                <p className="font-bold text-clario-primary-600">Kira · Practice</p>
                <h3 className="mt-1 text-xl font-black text-clario-surface-900">
                  {orchestration.thinking_result?.concept ?? 'Practical activity'}
                </h3>
                <h4 className="mt-4 font-bold text-clario-surface-900">REAL-WORLD SCENARIO</h4>
                <p className="mt-1 text-clario-surface-700">{orchestration.practical_result.scenario}</p>
                <h4 className="mt-4 font-bold text-clario-surface-900">PRACTICAL TASK</h4>
                <p className="mt-1 text-clario-surface-700">{orchestration.practical_result.practical_task}</p>
                <p className="mt-3 text-sm text-clario-surface-600">{orchestration.practical_result.real_world_context}</p>
                <h4 className="mt-4 font-bold text-clario-surface-900">EXPECTED ACTION</h4>
                <p className="mt-1 text-clario-surface-700">{orchestration.practical_result.expected_action}</p>
                <h4 className="mt-4 font-bold text-clario-surface-900">SUCCESS CRITERIA</h4>
                <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-clario-surface-700">
                  {orchestration.practical_result.success_criteria.map((criterion, index) => (
                    <li key={`${index}-${criterion}`}>{criterion}</li>
                  ))}
                </ul>
                <p className="mt-4 text-xs text-clario-surface-500">
                  Difficulty: {orchestration.practical_result.difficulty}
                </p>
              </Card>
            )}
            {orchestration?.current_state === 'PRACTICAL_READY' && !quiz && (
              <div className="space-y-3">
                {quizError && <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">{quizError}</p>}
                <Button type="button" variant="primary" disabled={isGeneratingQuiz} onClick={() => void startQuiz(sessionId)}>
                  {isGeneratingQuiz ? 'Preparing challenge...' : 'Start Challenge'}
                </Button>
              </div>
            )}
            {orchestration?.current_state === 'QUIZ_FAILED' && !isGeneratingQuiz && (
              <div className="space-y-3">
                <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">
                  {quizError ?? 'Zayn could not prepare the quiz.'}
                </p>
                <Button type="button" variant="primary" onClick={() => void startQuiz(sessionId)}>
                  Retry Challenge
                </Button>
              </div>
            )}
            {isGeneratingQuiz && (
              <div role="status" className="rounded-2xl bg-clario-primary-50 p-5 text-clario-primary-800">
                <p className="font-bold">CLARIO-AI is asking Zayn to prepare your challenge...</p>
              </div>
            )}
            {quiz && quiz.status === 'SUBMITTED' && (
              <div className="space-y-4">
                <Card padding="lg" className="border-clario-primary-200 bg-clario-primary-50">
                  <p className="font-bold text-clario-primary-700">Challenge submitted</p>
                  <p className="mt-2 text-sm text-clario-surface-700">Your answers have been recorded. Elara will summarize the available learning evidence; CLARIO-AI retains the final learning decision.</p>
                </Card>
                {sessionId && !evaluation && orchestration?.current_state !== 'EVALUATING' && (
                  <div className="space-y-3">
                    {evaluationError && <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">{evaluationError}</p>}
                    {orchestration?.current_state === 'EVALUATION_FAILED' && !evaluationError && (
                      <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">Elara could not complete the evaluation. You can retry.</p>
                    )}
                    <Button type="button" variant="primary" disabled={isEvaluating} onClick={() => void evaluateLearning(sessionId)}>
                      {isEvaluating ? 'Evaluating learning...' : 'Evaluate Learning'}
                    </Button>
                  </div>
                )}
                {isEvaluating && (
                  <div role="status" className="rounded-2xl bg-clario-primary-50 p-5 text-clario-primary-800">
                    <p className="font-bold">CLARIO-AI is asking Elara to evaluate the available evidence...</p>
                  </div>
                )}
                {evaluation && (
                  <div className="space-y-4">
                  <Card padding="lg" className="border-clario-primary-200">
                    <p className="font-bold text-clario-primary-700">ELARA · CONCEPT EVALUATION</p>
                    <h3 className="mt-2 text-xl font-black text-clario-surface-900">{evaluation.concept_name}</h3>
                    <p className="mt-3 text-clario-surface-700">{evaluation.overall_evaluation}</p>
                    <dl className="mt-5 grid gap-3 sm:grid-cols-2">
                      <div><dt className="text-sm text-clario-surface-500">Concept strength</dt><dd className="font-semibold capitalize">{evaluation.concept_strength.replace(/_/g, ' ')}</dd></div>
                      <div><dt className="text-sm text-clario-surface-500">Concept weakness</dt><dd className="font-semibold capitalize">{evaluation.concept_weakness.replace(/_/g, ' ')}</dd></div>
                      <div><dt className="text-sm text-clario-surface-500">Quiz performance</dt><dd className="font-semibold">{evaluation.quiz_performance.correct_answers}/{evaluation.quiz_performance.total_questions} correct · {evaluation.quiz_performance.accuracy}% accuracy</dd></div>
                      <div><dt className="text-sm text-clario-surface-500">Difficulty signal (advisory)</dt><dd className="font-semibold capitalize">{evaluation.difficulty_signal.replace(/_/g, ' ')}</dd></div>
                    </dl>
                    <p className="mt-4 text-sm text-clario-surface-700">{evaluation.evidence_summary}</p>
                    <p className="mt-3 text-xs text-clario-surface-500">
                      Ayan thinking response: {evaluation.thinking_evidence} · Kira practical response: {evaluation.practical_evidence}. CLARIO-AI decision is not part of this evaluation.
                    </p>
                  </Card>
                  {!decision && sessionId && orchestration?.current_state !== 'DECIDING' && (
                    <div className="space-y-3">
                      {decisionError && <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">{decisionError}</p>}
                      {orchestration?.current_state === 'DECISION_FAILED' && !decisionError && (
                        <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">CLARIO-AI could not persist the decision. You can retry.</p>
                      )}
                      <Button type="button" variant="primary" disabled={isDeciding} onClick={() => void requestDecision(sessionId)}>
                        {isDeciding ? 'Preparing next step...' : 'Continue'}
                      </Button>
                    </div>
                  )}
                  {isDeciding && (
                    <div role="status" className="rounded-2xl bg-clario-primary-50 p-5 text-clario-primary-800">
                      <p className="font-bold">CLARIO-AI is selecting the next step for this concept...</p>
                    </div>
                  )}
                  {decision && (
                    <Card padding="lg" className="border-clario-primary-200 bg-clario-primary-50">
                      <p className="font-bold text-clario-primary-700">CLARIO-AI · NEXT LEARNING STEP</p>
                      <h3 className="mt-2 text-xl font-black text-clario-surface-900">{evaluation.concept_name}</h3>
                      <p className="mt-2 text-clario-surface-700">
                        Current status: <span className="font-semibold capitalize">{decision.mastery_status}</span>
                      </p>
                      <p className="mt-1 text-clario-surface-700">
                        {decision.decision === 'CONTINUE' && 'This concept meets its current learning target. You can continue your learning journey.'}
                        {decision.decision === 'RETEACH' && 'CLARIO-AI is preparing another explanation for this concept.'}
                        {decision.decision === 'REDUCE_DIFFICULTY' && 'CLARIO-AI is preparing another attempt for this concept at a lower difficulty.'}
                        {decision.decision === 'RETEST' && 'More evidence is needed. CLARIO-AI is preparing a retest for this concept.'}
                        {decision.decision === 'INCREASE_DIFFICULTY' && 'The next attempt for this concept will use a higher difficulty.'}
                        {decision.decision === 'COMPLETE_LEVEL' && 'All mapped concepts in this learning level are complete.'}
                        {decision.decision === 'UNLOCK_NEXT_LEVEL' && 'The next mapped learning level is ready.'}
                        {decision.decision === 'COMPLETE_GOAL' && 'The mapped learning goal is complete.'}
                      </p>
                      {(decision.decision === 'REDUCE_DIFFICULTY' || decision.decision === 'INCREASE_DIFFICULTY') && (
                        <p className="mt-2 text-sm text-clario-surface-600">Next attempt difficulty: {decision.next_difficulty}</p>
                      )}
                    </Card>
                  )}
                  </div>
                )}
              </div>
            )}
            {quiz && quiz.status !== 'SUBMITTED' && (
              <Card padding="lg" className="border-clario-primary-200">
                {quizError && <p role="alert" className="mb-4 rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">{quizError}</p>}
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-bold text-clario-primary-600">Zayn · Challenge</p>
                    <h3 className="mt-1 text-xl font-black text-clario-surface-900">
                      {quiz.difficulty} · {quiz.questions.length} questions
                    </h3>
                  </div>
                  <p role="timer" aria-live="off" className="rounded-full bg-clario-primary-50 px-4 py-2 font-bold text-clario-primary-800">
                    {String(Math.floor(quizRemainingSeconds / 60)).padStart(2, '0')}:{String(quizRemainingSeconds % 60).padStart(2, '0')}
                  </p>
                </div>
                <p className="mt-2 text-sm text-clario-surface-600">
                  {quiz.time_limit_seconds} seconds per question · {quiz.time_limit_seconds * quiz.questions.length} seconds total
                </p>
                <form className="mt-5 space-y-5" onSubmit={event => { event.preventDefault(); void submitQuiz(sessionId); }}>
                  {quiz.questions.map((question, index) => (
                    <fieldset key={question.question_id} className="rounded-xl border border-clario-surface-200 p-4">
                      <legend className="px-1 font-bold text-clario-surface-900">{index + 1}. {question.question}</legend>
                      <div className="mt-3 space-y-2">
                        {question.options.map(option => (
                          <label key={option} className="flex cursor-pointer items-start gap-3 rounded-lg p-2 hover:bg-clario-surface-50">
                            <input
                              type="radio"
                              name={question.question_id}
                              value={option}
                              checked={quizAnswers[question.question_id] === option}
                              onChange={() => setQuizAnswers(previous => ({ ...previous, [question.question_id]: option }))}
                              disabled={isSubmittingQuiz}
                            />
                            <span className="text-sm text-clario-surface-700">{option}</span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  ))}
                  <Button type="submit" variant="primary" disabled={isSubmittingQuiz || Object.keys(quizAnswers).length !== quiz.questions.length}>
                    {isSubmittingQuiz ? 'Submitting answers...' : 'Submit Challenge'}
                  </Button>
                </form>
              </Card>
            )}
          </section>
        )}
      </Card>
    </div>
  );
}
