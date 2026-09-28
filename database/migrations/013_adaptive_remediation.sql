PRAGMA foreign_keys=OFF;

CREATE TABLE teaching_results_new (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    orchestration_id TEXT NOT NULL,
    concept TEXT NOT NULL,
    response_json TEXT NOT NULL,
    learner_level TEXT NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (session_id, attempt_number),
    UNIQUE (orchestration_id, attempt_number),
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE
);
INSERT INTO teaching_results_new (
    id, session_id, orchestration_id, concept, response_json, learner_level,
    attempt_number, created_at, updated_at
)
SELECT id, session_id, orchestration_id, concept, response_json, learner_level,
       1, created_at, updated_at
FROM teaching_results;
DROP TABLE teaching_results;
ALTER TABLE teaching_results_new RENAME TO teaching_results;

CREATE TABLE thinking_results_new (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    orchestration_id TEXT NOT NULL,
    concept TEXT NOT NULL,
    response_json TEXT NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (session_id, attempt_number),
    UNIQUE (orchestration_id, attempt_number),
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE
);
INSERT INTO thinking_results_new (
    id, session_id, orchestration_id, concept, response_json, attempt_number,
    created_at, updated_at
)
SELECT id, session_id, orchestration_id, concept, response_json, 1,
       created_at, updated_at
FROM thinking_results;
DROP TABLE thinking_results;
ALTER TABLE thinking_results_new RENAME TO thinking_results;

CREATE TABLE practical_results_new (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    orchestration_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    scenario TEXT NOT NULL,
    practical_task TEXT NOT NULL,
    real_world_context TEXT NOT NULL,
    expected_action TEXT NOT NULL,
    success_criteria TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    research_source_ids TEXT NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (session_id, attempt_number),
    UNIQUE (orchestration_id, attempt_number),
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE
);
INSERT INTO practical_results_new (
    id, session_id, orchestration_id, concept_id, scenario, practical_task,
    real_world_context, expected_action, success_criteria, difficulty,
    research_source_ids, attempt_number, created_at
)
SELECT id, session_id, orchestration_id, concept_id, scenario, practical_task,
       real_world_context, expected_action, success_criteria, difficulty,
       research_source_ids, 1, created_at
FROM practical_results;
DROP TABLE practical_results;
ALTER TABLE practical_results_new RENAME TO practical_results;

CREATE TABLE quiz_results_new (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    orchestration_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('EASY', 'MEDIUM', 'HARD')),
    time_limit_seconds INTEGER NOT NULL CHECK (time_limit_seconds IN (30, 60, 90)),
    questions_json TEXT NOT NULL,
    answer_key_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'GENERATED'
        CHECK (status IN ('GENERATED', 'IN_PROGRESS', 'SUBMITTED')),
    submitted_answers_json TEXT,
    correctness_json TEXT,
    attempt_number INTEGER NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    UNIQUE (session_id, attempt_number),
    UNIQUE (orchestration_id, attempt_number),
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE
);
INSERT INTO quiz_results_new (
    id, session_id, orchestration_id, concept_id, difficulty, time_limit_seconds,
    questions_json, answer_key_json, status, submitted_answers_json,
    correctness_json, attempt_number, created_at, updated_at, submitted_at
)
SELECT id, session_id, orchestration_id, concept_id, difficulty, time_limit_seconds,
       questions_json, answer_key_json, status, submitted_answers_json,
       correctness_json, 1, created_at, updated_at, submitted_at
FROM quiz_results;
DROP TABLE quiz_results;
ALTER TABLE quiz_results_new RENAME TO quiz_results;

CREATE TABLE elara_evaluations_new (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    orchestration_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    quiz_result_id TEXT NOT NULL UNIQUE,
    concept_name TEXT NOT NULL,
    quiz_performance_json TEXT NOT NULL,
    concept_strength TEXT NOT NULL
        CHECK (concept_strength IN ('strong', 'moderate', 'weak', 'insufficient_evidence')),
    concept_weakness TEXT NOT NULL
        CHECK (concept_weakness IN (
            'none', 'conceptual', 'reasoning', 'practical', 'recall', 'mixed',
            'insufficient_evidence'
        )),
    overall_evaluation TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    difficulty_signal TEXT NOT NULL
        CHECK (difficulty_signal IN ('increase', 'maintain', 'decrease', 'insufficient_evidence')),
    evidence_summary TEXT NOT NULL,
    evaluation_json TEXT NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP NOT NULL,
    UNIQUE (session_id, attempt_number),
    UNIQUE (orchestration_id, attempt_number),
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    FOREIGN KEY (quiz_result_id) REFERENCES quiz_results(id) ON DELETE CASCADE
);
INSERT INTO elara_evaluations_new (
    id, session_id, orchestration_id, concept_id, quiz_result_id, concept_name,
    quiz_performance_json, concept_strength, concept_weakness, overall_evaluation,
    confidence, difficulty_signal, evidence_summary, evaluation_json,
    attempt_number, created_at, updated_at, evaluated_at
)
SELECT id, session_id, orchestration_id, concept_id, quiz_result_id, concept_name,
       quiz_performance_json, concept_strength, concept_weakness, overall_evaluation,
       confidence, difficulty_signal, evidence_summary, evaluation_json, 1,
       created_at, updated_at, evaluated_at
FROM elara_evaluations;
DROP TABLE elara_evaluations;
ALTER TABLE elara_evaluations_new RENAME TO elara_evaluations;

CREATE TABLE clario_adaptive_executions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    orchestration_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    decision_id TEXT NOT NULL UNIQUE,
    source_evaluation_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    decision_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'IN_PROGRESS', 'AWAITING_SUBMISSION', 'COMPLETED',
            'FAILED', 'LIMIT_REACHED'
        )
    ),
    remediation_context_json TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (session_id, concept_id, attempt_number),
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    FOREIGN KEY (decision_id) REFERENCES adaptive_decisions(id) ON DELETE CASCADE,
    FOREIGN KEY (source_evaluation_id) REFERENCES elara_evaluations(id) ON DELETE CASCADE
);
CREATE INDEX ix_clario_adaptive_executions_session_created
    ON clario_adaptive_executions (session_id, created_at);

PRAGMA foreign_keys=ON;
