export interface OnboardingRequest {
  learning_goal: string;
  current_level: 'beginner' | 'intermediate' | 'advanced';
  learning_preference: 'step_by_step' | 'example_first' | 'practical_first';
  interests: string[];
  initial_confidence: number;
}

export interface OnboardingResponse {
  status: 'success' | 'error';
  user_id: string;
  profile_id: string;
  recommended_topic: string;
  topic_id: string;
  next_action: 'start_session';
}

export interface AuthRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  user_id: string;
  email: string;
  authentication_provider: string;
  profile_complete: boolean;
  mind_profile_complete: boolean;
}

export interface UserProfileRequest {
  name: string;
  gender: string;
  basic_details: string;
}

export interface UserProfileResponse extends UserProfileRequest {
  user_id: string;
  email: string;
  authentication_provider: string;
}

export interface MindProfileRequest {
  learning_motivation: string;
  preferred_explanation: string;
  support_when_stuck: string;
  feedback_preference: string;
  challenge_preference: string;
}

export interface MindProfileResponse extends MindProfileRequest {
  id: string;
  user_id: string;
  created_at: string;
}

export interface SessionInputsRequest {
  task: string;
  goal: string;
  learner_state: string;
  interest: string;
}

export type CalaLearnerLevel = 'beginner' | 'intermediate' | 'advanced';
export type CalaConfidenceLevel = 'unknown' | 'low' | 'moderate' | 'high';

export interface CalaConfidenceState {
  level: CalaConfidenceLevel;
  evidence: string | null;
  self_reported_score: number | null;
}

export interface CalaRoadmapConcept {
  concept_id: string;
  title: string;
  description: string;
  order: number;
}

export interface CalaRoadmapTopic {
  topic_id: string;
  title: string;
  description: string | null;
  order: number;
  concepts: CalaRoadmapConcept[];
}

export interface CalaRoadmapLevel {
  level_id: string;
  title: string;
  description: string;
  order: number;
  is_unlocked: boolean;
  completion_state: 'not_started' | 'in_progress' | 'completed';
  topics: CalaRoadmapTopic[];
}

export interface CalaAgentRoutingStep {
  agent: 'Nova' | 'Mira' | 'Ayan' | 'Kira' | 'Zayn' | 'Elara';
  purpose: string;
  status: 'planned';
}

export interface CalaResult {
  session_id: string;
  learner_level: CalaLearnerLevel;
  learner_level_reason: string;
  weakness_type: string;
  weakness_reason: string;
  confidence_state: CalaConfidenceState;
  recommended_starting_level: string;
  recommended_starting_level_reason: string;
  learning_goal: string;
  task: string;
  learner_state: string;
  interest: string;
  roadmap: CalaRoadmapLevel[];
  initial_agent_routing: CalaAgentRoutingStep[];
}

export interface ResearchConcept {
  concept_id: string;
  title: string;
  description: string;
}

export interface ResearchTopicContext {
  topic_id: string;
  title: string;
  concepts: ResearchConcept[];
}

export interface ResearchRequest {
  session_id: string;
  learning_goal: string;
  task: string;
  learner_state: string;
  interest: string;
  learner_level: CalaLearnerLevel;
  recommended_starting_level: string;
  current_topic: ResearchTopicContext;
  research_objective: string;
}

export interface ResearchSource {
  source_id: string;
  title: string;
  url: string;
  domain: string;
  snippet: string;
  relevance_score: number;
  source_type: string;
  published_date: string | null;
  validation_status: 'validated';
}

export interface SharedResearchPackage {
  session_id: string;
  research_request: ResearchRequest;
  research_summary: string;
  key_concepts: ResearchConcept[];
  selected_sources: ResearchSource[];
  research_timestamp: string;
  queries: Array<{ query: string; result_count: number }>;
  validation_information: {
    status: 'complete' | 'partial' | 'no_sources';
    candidates_received: number;
    sources_validated: number;
    sources_rejected: number;
    duplicate_sources_removed: number;
    maximum_sources_per_domain: number;
  };
}

export type OrchestrationState =
  | 'CALA_READY'
  | 'RESEARCH_REQUESTED'
  | 'RESEARCHING'
  | 'RESEARCH_READY'
  | 'RESEARCH_FAILED'
  | 'TEACHING_REQUESTED'
  | 'TEACHING'
  | 'TEACHING_READY'
  | 'TEACHING_FAILED'
  | 'THINKING_REQUESTED'
  | 'THINKING'
  | 'THINKING_READY'
  | 'THINKING_FAILED'
  | 'PRACTICAL_REQUESTED'
  | 'PRACTICAL'
  | 'PRACTICAL_READY'
  | 'PRACTICAL_FAILED'
  | 'QUIZ_REQUESTED'
  | 'QUIZ_GENERATING'
  | 'QUIZ_READY'
  | 'QUIZ_FAILED'
  | 'QUIZ_SUBMITTED'
  | 'EVALUATION_REQUESTED'
  | 'EVALUATING'
  | 'EVALUATION_READY'
  | 'EVALUATION_FAILED'
  | 'DECISION_REQUESTED'
  | 'DECIDING'
  | 'DECISION_READY'
  | 'DECISION_FAILED';

export interface MiraTeachingResponse {
  session_id: string;
  concept: string;
  explanation: string;
  key_points: string[];
  examples: string[];
  learner_level: CalaLearnerLevel;
  teaching_style: string;
  source_references: Array<{
    source_id: string;
    title: string;
    url: string;
  }>;
  generated_at: string;
}

export interface AyanThinkingResponse {
  session_id: string;
  concept: string;
  thinking_prompt: string;
  expected_reasoning_focus: string[];
  difficulty: CalaLearnerLevel;
  source_references: Array<{
    source_id: string;
    title: string;
    url: string;
  }>;
  generated_at: string;
}

export interface KiraPracticalOutput {
  agent: 'Kira';
  session_id: string;
  orchestration_id: string;
  concept_id: string;
  scenario: string;
  practical_task: string;
  real_world_context: string;
  expected_action: string;
  success_criteria: string[];
  difficulty: CalaLearnerLevel;
  research_source_ids: string[];
  generated_at: string;
}

export type ZaynDifficulty = 'EASY' | 'MEDIUM' | 'HARD';

export interface ZaynPresentationQuestion {
  question_id: string;
  question: string;
  options: string[];
  difficulty: ZaynDifficulty;
  concept_id: string;
}

export interface ZaynQuizPresentation {
  quiz_id: string;
  session_id: string;
  orchestration_id: string;
  concept_id: string;
  difficulty: ZaynDifficulty;
  time_limit_seconds: number;
  questions: ZaynPresentationQuestion[];
  status: 'GENERATED' | 'IN_PROGRESS' | 'SUBMITTED';
  created_at: string;
}

export interface ZaynSubmissionRequest {
  quiz_id: string;
  answers: Record<string, string>;
}

export interface ZaynSubmissionResponse {
  quiz_id: string;
  status: 'SUBMITTED';
  submitted_at: string;
}

export interface ElaraEvaluation {
  agent: 'Elara';
  session_id: string;
  orchestration_id: string;
  concept_id: string;
  concept_name: string;
  concept_strength: 'strong' | 'moderate' | 'weak' | 'insufficient_evidence';
  concept_weakness:
    | 'none'
    | 'conceptual'
    | 'reasoning'
    | 'practical'
    | 'recall'
    | 'mixed'
    | 'insufficient_evidence';
  quiz_performance: {
    quiz_result_id: string;
    difficulty: ZaynDifficulty;
    total_questions: number;
    answered_questions: number;
    unanswered_questions: number;
    correct_answers: number;
    incorrect_answers: number;
    accuracy: number;
  };
  thinking_evidence: 'unavailable';
  practical_evidence: 'unavailable';
  overall_evaluation: string;
  confidence: number;
  difficulty_signal: 'increase' | 'maintain' | 'decrease' | 'insufficient_evidence';
  evidence_summary: string;
  evaluated_at: string;
}

export type AdaptiveDecisionAction =
  | 'CONTINUE'
  | 'RETEACH'
  | 'RETEST'
  | 'REDUCE_DIFFICULTY'
  | 'INCREASE_DIFFICULTY'
  | 'COMPLETE_LEVEL'
  | 'UNLOCK_NEXT_LEVEL'
  | 'COMPLETE_GOAL';

export interface ClarioAdaptiveDecision {
  session_id: string;
  orchestration_id: string;
  concept_id: string;
  decision: AdaptiveDecisionAction;
  mastery_status: 'learning' | 'mastered' | 'remediating';
  current_difficulty: ZaynDifficulty;
  next_difficulty: ZaynDifficulty;
  reason: string;
  evaluation_reference: string;
  remediation_required: boolean;
  decided_at: string;
}

export interface SessionConceptPerformance {
  id: string;
  session_id: string;
  orchestration_id: string;
  concept_id: string;
  concept_name: string;
  current_difficulty: ZaynDifficulty;
  mastery_status: 'learning' | 'mastered' | 'remediating';
  strength: ElaraEvaluation['concept_strength'];
  weakness: ElaraEvaluation['concept_weakness'];
  evaluation_confidence: number;
  quiz_accuracy: number;
  attempt_count: number;
  remediation_count: number;
  last_evaluation_id: string;
  created_at: string;
  updated_at: string;
}

export interface ClarioOrchestrationContext {
  session_id: string;
  cala_plan_id: string;
  current_state: OrchestrationState;
  current_step: string;
  research_package_id: string | null;
  research_package: SharedResearchPackage | null;
  teaching_result_id: string | null;
  teaching_result: MiraTeachingResponse | null;
  thinking_result_id: string | null;
  thinking_result: AyanThinkingResponse | null;
  practical_result_id: string | null;
  practical_result: KiraPracticalOutput | null;
  quiz_id: string | null;
  quiz_difficulty: ZaynDifficulty | null;
  quiz_status: 'GENERATED' | 'IN_PROGRESS' | 'SUBMITTED' | null;
  evaluation_id: string | null;
  evaluation: ElaraEvaluation | null;
  adaptive_decision: ClarioAdaptiveDecision | null;
  concept_performance: SessionConceptPerformance | null;
  created_at: string;
  updated_at: string;
}

export interface LearnerProfileResponse {
  id: string;
  user_id: string;
  learning_goal: string;
  current_level: string;
  learning_preference: string;
  interests: string;
  initial_confidence: number;
  updated_at: string;
}

export interface SessionCreateRequest {
  topic_id: string;
}

export interface SessionCreateResponse {
  status: 'success' | 'error';
  session_id: string;
  topic_id: string;
  topic_title: string;
}

export interface SessionStateResponse {
  session_id: string;
  user_id: string;
  profile_id: string | null;
  topic_id: string;
  topic_title: string;
  current_concept_id: string | null;
  current_concept_title: string | null;
  current_step: string;
  current_action: string;
  current_content: Record<string, unknown> | null;
  inputs: SessionInputsRequest | null;
  difficulty_level: number;
  is_remediating: boolean;
  remediation_notes: string | null;
  attempt_count: number;
  asked_question_ids: string[];
}

export interface ThinkingSubmitRequest {
  session_id: string;
  learner_response: string;
}

export interface ThinkingSubmitResponse {
  status: 'success' | 'error';
  session_id: string;
  thinking_assessment: {
    reasoning_assessment: string;
    conceptual_understanding: 'high' | 'moderate' | 'low';
    misconception: string | null;
    confidence: number;
  };
  practical_exercise: {
    scenario_title: string;
    practical_type: string;
    scenario_description: string;
    task_prompt: string;
    hints: string[];
  };
  next_step: {
    action: string;
    companion: string;
    concept: string;
    instructions: string;
  };
}

export interface PracticalSubmitRequest {
  session_id: string;
  learner_response: string;
}

export interface QuizQuestionResponse {
  question_id: string;
  format: string;
  question_text: string;
  options: string[] | null;
  correct_answer: string;
  difficulty: number;
}

export interface QuizGenerateResponse {
  status: 'success' | 'error';
  session_id: string;
  question: QuizQuestionResponse;
}

export interface QuizSubmitRequest {
  session_id: string;
  learner_answer: string;
}

export interface EvaluationResult {
  concept: string;
  status: string;
  reasoning_score: number;
  misconceptions: string[];
}

export interface NextStep {
  action: 'advance' | 'remediate' | 'continue' | 'topic_completed';
  companion: string;
  concept: string;
  instructions: string;
}

export interface QuizSubmitResponse {
  status: 'success' | 'error';
  session_id: string;
  evaluated_by: string;
  evaluation: EvaluationResult;
  next_step: NextStep;
}

export interface ConceptBreakdownItem {
  concept: string;
  status: 'mastered' | 'remediating' | 'learning';
  difficulty: number;
  mastery_score: number;
}

export interface DashboardResponse {
  status: 'success' | 'error';
  learner_name: string;
  current_topic: string;
  concept_breakdown: ConceptBreakdownItem[];
  weak_concepts: string[];
  recommended_action: string;
}

export interface RoadmapItem {
  concept_id: string;
  concept_title: string;
  status: 'mastered' | 'remediating' | 'learning' | 'upcoming';
  difficulty: number;
  is_next: boolean;
}

export interface RoadmapResponse {
  status: 'success' | 'error';
  current_topic: string;
  topic_id: string;
  roadmap: RoadmapItem[];
}

export interface HealthResponse {
  status: 'ok';
  service: string;
  version: string;
}

export interface ApiError {
  detail: string;
}

export type LearningStage = 'teaching' | 'thinking' | 'practical' | 'quiz' | 'evaluation' | 'completed';