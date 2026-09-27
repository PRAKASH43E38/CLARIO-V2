CREATE TABLE IF NOT EXISTS elara_evaluations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    orchestration_id TEXT NOT NULL UNIQUE,
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
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    FOREIGN KEY (quiz_result_id) REFERENCES quiz_results(id) ON DELETE CASCADE
);
