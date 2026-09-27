CREATE TABLE IF NOT EXISTS session_concept_performances (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    orchestration_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    concept_name TEXT NOT NULL,
    current_difficulty TEXT NOT NULL
        CHECK (current_difficulty IN ('EASY', 'MEDIUM', 'HARD')),
    mastery_status TEXT NOT NULL
        CHECK (mastery_status IN ('learning', 'mastered', 'remediating')),
    strength TEXT NOT NULL
        CHECK (strength IN ('strong', 'moderate', 'weak', 'insufficient_evidence')),
    weakness TEXT NOT NULL
        CHECK (weakness IN (
            'none', 'conceptual', 'reasoning', 'practical', 'recall', 'mixed',
            'insufficient_evidence'
        )),
    evaluation_confidence REAL NOT NULL
        CHECK (evaluation_confidence >= 0 AND evaluation_confidence <= 1),
    quiz_accuracy REAL NOT NULL CHECK (quiz_accuracy >= 0 AND quiz_accuracy <= 100),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    remediation_count INTEGER NOT NULL DEFAULT 0 CHECK (remediation_count >= 0),
    last_evaluation_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (session_id, concept_id),
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    FOREIGN KEY (last_evaluation_id) REFERENCES elara_evaluations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS adaptive_decisions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    orchestration_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    evaluation_id TEXT NOT NULL UNIQUE,
    decision TEXT NOT NULL CHECK (decision IN (
        'CONTINUE', 'RETEACH', 'RETEST', 'REDUCE_DIFFICULTY',
        'INCREASE_DIFFICULTY', 'COMPLETE_LEVEL', 'UNLOCK_NEXT_LEVEL',
        'COMPLETE_GOAL'
    )),
    mastery_status TEXT NOT NULL
        CHECK (mastery_status IN ('learning', 'mastered', 'remediating')),
    current_difficulty TEXT NOT NULL
        CHECK (current_difficulty IN ('EASY', 'MEDIUM', 'HARD')),
    next_difficulty TEXT NOT NULL
        CHECK (next_difficulty IN ('EASY', 'MEDIUM', 'HARD')),
    reason TEXT NOT NULL,
    remediation_required INTEGER NOT NULL CHECK (remediation_required IN (0, 1)),
    decision_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (orchestration_id, evaluation_id),
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    FOREIGN KEY (evaluation_id) REFERENCES elara_evaluations(id) ON DELETE CASCADE
);
