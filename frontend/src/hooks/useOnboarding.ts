import { useState, useCallback } from 'react';
import type { OnboardingRequest, OnboardingResponse } from '../types';
import { api } from '../services';

interface OnboardingState {
  step: number;
  totalSteps: number;
  data: Partial<OnboardingRequest>;
  isSubmitting: boolean;
  error: string | null;
}

export function useOnboarding() {
  const [state, setState] = useState<OnboardingState>({
    step: 1,
    totalSteps: 5,
    data: {
      learning_goal: '',
      current_level: 'beginner',
      learning_preference: 'step_by_step',
      interests: [],
      initial_confidence: 3,
    },
    isSubmitting: false,
    error: null,
  });

  const updateField = useCallback(<K extends keyof OnboardingRequest>(field: K, value: OnboardingRequest[K]) => {
    setState(prev => ({
      ...prev,
      data: { ...prev.data, [field]: value },
      error: null,
    }));
  }, []);

  const nextStep = useCallback(() => {
    setState(prev => ({
      ...prev,
      step: Math.min(prev.step + 1, prev.totalSteps),
    }));
  }, []);

  const prevStep = useCallback(() => {
    setState(prev => ({
      ...prev,
      step: Math.max(prev.step - 1, 1),
    }));
  }, []);

  const submit = useCallback(async (): Promise<OnboardingResponse | null> => {
    setState(prev => ({ ...prev, isSubmitting: true, error: null }));
    try {
      const response = await api.submitOnboarding(state.data as OnboardingRequest);
      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to complete onboarding';
      setState(prev => ({ ...prev, error: message }));
      return null;
    } finally {
      setState(prev => ({ ...prev, isSubmitting: false }));
    }
  }, [state.data]);

  const reset = useCallback(() => {
    setState({
      step: 1,
      totalSteps: 5,
      data: {
        learning_goal: '',
        current_level: 'beginner',
        learning_preference: 'step_by_step',
        interests: [],
        initial_confidence: 3,
      },
      isSubmitting: false,
      error: null,
    });
  }, []);

  return {
    ...state,
    updateField,
    nextStep,
    prevStep,
    submit,
    reset,
    progress: (state.step / state.totalSteps) * 100,
  };
}