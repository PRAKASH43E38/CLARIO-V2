import type {
  OnboardingRequest,
  OnboardingResponse,
  LearnerProfileResponse,
  SessionCreateRequest,
  SessionCreateResponse,
  SessionStateResponse,
  ThinkingSubmitRequest,
  ThinkingSubmitResponse,
  PracticalSubmitRequest,
  QuizGenerateResponse,
  QuizSubmitRequest,
  QuizSubmitResponse,
  DashboardResponse,
  RoadmapResponse,
  HealthResponse,
  AuthRequest,
  AuthResponse,
  UserProfileRequest,
  UserProfileResponse,
  MindProfileRequest,
  MindProfileResponse,
  SessionInputsRequest,
  CalaResult,
  ClarioOrchestrationContext,
  MiraTeachingResponse,
  AyanThinkingResponse,
  KiraPracticalOutput,
  ZaynQuizPresentation,
  ZaynSubmissionRequest,
  ZaynSubmissionResponse,
  ElaraEvaluation,
  ClarioAdaptiveDecision,
  SessionConceptPerformance,
} from '../types';

const API_BASE = '/api/v1';

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Health
  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  async register(data: AuthRequest): Promise<AuthResponse> {
    return this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async login(data: AuthRequest): Promise<AuthResponse> {
    return this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAuthStatus(userId: string): Promise<AuthResponse> {
    return this.request<AuthResponse>(`/auth/status?user_id=${encodeURIComponent(userId)}`);
  }

  async getUserProfile(userId: string): Promise<UserProfileResponse> {
    return this.request<UserProfileResponse>(`/profile?user_id=${encodeURIComponent(userId)}`);
  }

  async saveUserProfile(userId: string, data: UserProfileRequest): Promise<UserProfileResponse> {
    return this.request<UserProfileResponse>(`/profile?user_id=${encodeURIComponent(userId)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getMindProfile(userId: string): Promise<MindProfileResponse> {
    return this.request<MindProfileResponse>(`/mind-profile?user_id=${encodeURIComponent(userId)}`);
  }

  async saveMindProfile(userId: string, data: MindProfileRequest): Promise<MindProfileResponse> {
    return this.request<MindProfileResponse>(`/mind-profile?user_id=${encodeURIComponent(userId)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Onboarding
  async submitOnboarding(data: OnboardingRequest): Promise<OnboardingResponse> {
    return this.request<OnboardingResponse>('/onboarding/submit', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getOnboardingStatus(userId: string): Promise<{ status: string; onboarding_complete: boolean; profile_id: string | null }> {
    return this.request(`/onboarding/status?user_id=${encodeURIComponent(userId)}`);
  }

  // Learner Profile
  async getLearnerProfile(userId: string): Promise<LearnerProfileResponse> {
    return this.request<LearnerProfileResponse>(`/learner/profile?user_id=${encodeURIComponent(userId)}`);
  }

  // Sessions
  async startSession(userId: string, topicId: string): Promise<SessionCreateResponse> {
    return this.request<SessionCreateResponse>(`/session/start?user_id=${encodeURIComponent(userId)}`, {
      method: 'POST',
      body: JSON.stringify({ topic_id: topicId }),
    });
  }

  async createLearningSession(userId: string, data: SessionInputsRequest): Promise<SessionCreateResponse> {
    return this.request<SessionCreateResponse>(`/learning-session/create?user_id=${encodeURIComponent(userId)}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async createCalaPlan(userId: string, sessionId: string): Promise<CalaResult> {
    return this.request<CalaResult>(
      `/sessions/${encodeURIComponent(sessionId)}/cala-plan?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' },
    );
  }

  async getCalaPlan(userId: string, sessionId: string): Promise<CalaResult> {
    return this.request<CalaResult>(
      `/sessions/${encodeURIComponent(sessionId)}/cala-plan?user_id=${encodeURIComponent(userId)}`,
    );
  }

  async initializeOrchestration(userId: string, sessionId: string): Promise<ClarioOrchestrationContext> {
    return this.request<ClarioOrchestrationContext>(
      `/sessions/${encodeURIComponent(sessionId)}/orchestration?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' },
    );
  }

  async getOrchestrationState(userId: string, sessionId: string): Promise<ClarioOrchestrationContext> {
    return this.request<ClarioOrchestrationContext>(
      `/sessions/${encodeURIComponent(sessionId)}/orchestration?user_id=${encodeURIComponent(userId)}`,
    );
  }

  async requestOrchestrationResearch(userId: string, sessionId: string): Promise<ClarioOrchestrationContext> {
    return this.request<ClarioOrchestrationContext>(
      `/sessions/${encodeURIComponent(sessionId)}/orchestration/research?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' },
    );
  }

  async requestOrchestrationTeaching(userId: string, sessionId: string): Promise<ClarioOrchestrationContext> {
    return this.request<ClarioOrchestrationContext>(
      `/sessions/${encodeURIComponent(sessionId)}/orchestration/teach?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' },
    );
  }

  async getTeachingResult(userId: string, sessionId: string): Promise<MiraTeachingResponse> {
    return this.request<MiraTeachingResponse>(
      `/sessions/${encodeURIComponent(sessionId)}/teaching?user_id=${encodeURIComponent(userId)}`,
    );
  }

  async requestOrchestrationThinking(userId: string, sessionId: string): Promise<ClarioOrchestrationContext> {
    return this.request<ClarioOrchestrationContext>(
      `/sessions/${encodeURIComponent(sessionId)}/orchestration/think?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' },
    );
  }

  async getThinkingResult(userId: string, sessionId: string): Promise<AyanThinkingResponse> {
    return this.request<AyanThinkingResponse>(
      `/sessions/${encodeURIComponent(sessionId)}/thinking?user_id=${encodeURIComponent(userId)}`,
    );
  }

  async requestOrchestrationPractical(userId: string, sessionId: string): Promise<ClarioOrchestrationContext> {
    return this.request<ClarioOrchestrationContext>(
      `/sessions/${encodeURIComponent(sessionId)}/orchestration/practical?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' },
    );
  }

  async getPracticalResult(userId: string, sessionId: string): Promise<KiraPracticalOutput> {
    return this.request<KiraPracticalOutput>(
      `/sessions/${encodeURIComponent(sessionId)}/practical?user_id=${encodeURIComponent(userId)}`,
    );
  }

  async requestOrchestrationQuiz(userId: string, sessionId: string): Promise<ZaynQuizPresentation> {
    return this.request<ZaynQuizPresentation>(
      `/sessions/${encodeURIComponent(sessionId)}/orchestration/quiz?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' },
    );
  }

  async getQuiz(userId: string, sessionId: string): Promise<ZaynQuizPresentation> {
    return this.request<ZaynQuizPresentation>(
      `/sessions/${encodeURIComponent(sessionId)}/quiz?user_id=${encodeURIComponent(userId)}`,
    );
  }

  async submitZaynQuiz(
    userId: string,
    sessionId: string,
    data: ZaynSubmissionRequest,
  ): Promise<ZaynSubmissionResponse> {
    return this.request<ZaynSubmissionResponse>(
      `/sessions/${encodeURIComponent(sessionId)}/quiz/submit?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST', body: JSON.stringify(data) },
    );
  }

  async requestOrchestrationEvaluation(
    userId: string,
    sessionId: string,
  ): Promise<ElaraEvaluation> {
    return this.request<ElaraEvaluation>(
      `/sessions/${encodeURIComponent(sessionId)}/orchestration/evaluate?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' },
    );
  }

  async getEvaluation(userId: string, sessionId: string): Promise<ElaraEvaluation> {
    return this.request<ElaraEvaluation>(
      `/sessions/${encodeURIComponent(sessionId)}/evaluation?user_id=${encodeURIComponent(userId)}`,
    );
  }

  async requestOrchestrationDecision(
    userId: string,
    sessionId: string,
  ): Promise<ClarioAdaptiveDecision> {
    return this.request<ClarioAdaptiveDecision>(
      `/sessions/${encodeURIComponent(sessionId)}/orchestration/decide?user_id=${encodeURIComponent(userId)}`,
      { method: 'POST' },
    );
  }

  async getDecision(userId: string, sessionId: string): Promise<ClarioAdaptiveDecision> {
    return this.request<ClarioAdaptiveDecision>(
      `/sessions/${encodeURIComponent(sessionId)}/decision?user_id=${encodeURIComponent(userId)}`,
    );
  }

  async getConceptPerformance(
    userId: string,
    sessionId: string,
  ): Promise<SessionConceptPerformance[]> {
    return this.request<SessionConceptPerformance[]>(
      `/sessions/${encodeURIComponent(sessionId)}/concept-performance?user_id=${encodeURIComponent(userId)}`,
    );
  }

  async getSessionState(sessionId: string): Promise<SessionStateResponse> {
    return this.request<SessionStateResponse>(`/session/${sessionId}/state`);
  }

  // Learning Flow
  async submitThinking(data: ThinkingSubmitRequest): Promise<ThinkingSubmitResponse> {
    return this.request<ThinkingSubmitResponse>('/thinking/submit', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async submitPractical(data: PracticalSubmitRequest): Promise<QuizGenerateResponse> {
    return this.request<QuizGenerateResponse>('/practical/submit', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async generateQuiz(sessionId: string): Promise<QuizGenerateResponse> {
    return this.request<QuizGenerateResponse>(`/quiz/generate?session_id=${encodeURIComponent(sessionId)}`, {
      method: 'POST',
    });
  }

  async submitQuiz(data: QuizSubmitRequest): Promise<QuizSubmitResponse> {
    return this.request<QuizSubmitResponse>('/quiz/submit', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async triggerRemediation(sessionId: string): Promise<{
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
  }> {
    const result = await this.request(`/remediation/trigger?session_id=${encodeURIComponent(sessionId)}`, {
      method: 'POST',
    });
    return result as {
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
    };
  }

  // Dashboard & Roadmap
  async getDashboard(userId: string): Promise<DashboardResponse> {
    return this.request<DashboardResponse>(`/dashboard?user_id=${encodeURIComponent(userId)}`);
  }

  async getRoadmap(userId: string): Promise<RoadmapResponse> {
    return this.request<RoadmapResponse>(`/roadmap?user_id=${encodeURIComponent(userId)}`);
  }
}

export const api = new ApiClient();