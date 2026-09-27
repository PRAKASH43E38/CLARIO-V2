import { useState, useCallback, useEffect } from 'react';
import type {
  SessionStateResponse,
  ThinkingSubmitResponse,
  QuizGenerateResponse,
  QuizSubmitResponse,
  LearningStage,
} from '../types';
import { api } from '../services';

interface RemediationResult {
  status: string;
  session_id: string;
  teaching_explanation: {
    concept: string;
    explanation: string;
    step_by_step_breakdown: string[];
    analogy: string | null;
    intuitive_example: string;
    check_for_understanding_prompt: string;
  };
}

interface UseLearningSessionReturn {
  session: SessionStateResponse | null;
  isLoading: boolean;
  error: string | null;
  startSession: (userId: string, topicId: string) => Promise<SessionStateResponse>;
  fetchSession: (sessionId: string) => Promise<SessionStateResponse>;
  submitThinking: (sessionId: string, response: string) => Promise<ThinkingSubmitResponse>;
  submitPractical: (sessionId: string, response: string) => Promise<QuizGenerateResponse>;
  generateQuiz: (sessionId: string) => Promise<QuizGenerateResponse>;
  submitQuiz: (sessionId: string, answer: string) => Promise<QuizSubmitResponse>;
  triggerRemediation: (sessionId: string) => Promise<RemediationResult>;
  clearError: () => void;
  resetSession: () => void;
}

export function useLearningSession(): UseLearningSessionReturn {
  const [session, setSession] = useState<SessionStateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const resetSession = useCallback(() => {
    setSession(null);
    setError(null);
  }, []);

  const handleError = useCallback((err: unknown): never => {
    const message = err instanceof Error ? err.message : 'An unexpected error occurred';
    setError(message);
    throw err;
  }, []);

  const fetchSession = useCallback(async (sessionId: string): Promise<SessionStateResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const sessionData = await api.getSessionState(sessionId);
      setSession(sessionData);
      return sessionData;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [handleError]);

  const startSession = useCallback(async (userId: string, topicId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.startSession(userId, topicId);
      return await fetchSession(response.session_id);
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSession, handleError]);

  const submitThinking = useCallback(async (sessionId: string, response: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.submitThinking({ session_id: sessionId, learner_response: response });
      if (result.thinking_assessment && result.practical_exercise) {
        setSession(prev => prev ? {
          ...prev,
          current_step: 'practical' as LearningStage,
        } : null);
      }
      return result;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [handleError]);

  const submitPractical = useCallback(async (sessionId: string, response: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.submitPractical({ session_id: sessionId, learner_response: response });
      if (result.question) {
        setSession(prev => prev ? {
          ...prev,
          current_step: 'quiz' as LearningStage,
        } : null);
      }
      return result;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [handleError]);

  const generateQuiz = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.generateQuiz(sessionId);
      if (result.question) {
        setSession(prev => prev ? {
          ...prev,
          current_step: 'quiz' as LearningStage,
        } : null);
      }
      return result;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [handleError]);

  const submitQuiz = useCallback(async (sessionId: string, answer: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.submitQuiz({ session_id: sessionId, learner_answer: answer });
      
      if (result.next_step) {
        setSession(prev => prev ? {
          ...prev,
          current_step: result.next_step.action === 'advance' ? 'teaching' :
                        result.next_step.action === 'remediate' ? 'teaching' :
                        result.next_step.action === 'topic_completed' ? 'completed' :
                        'quiz',
          current_concept_title: result.next_step.concept || prev.current_concept_title,
          is_remediating: result.next_step.action === 'remediate',
        } : null);
      }
      return result;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [handleError]);

  const triggerRemediation = useCallback(async (sessionId: string): Promise<RemediationResult> => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.triggerRemediation(sessionId);
      setSession(prev => prev ? {
        ...prev,
        current_step: 'teaching' as LearningStage,
        is_remediating: true,
      } : null);
      return result;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [handleError]);

  return {
    session,
    isLoading,
    error,
    startSession,
    fetchSession,
    submitThinking,
    submitPractical,
    generateQuiz,
    submitQuiz,
    triggerRemediation,
    clearError,
    resetSession,
  };
}