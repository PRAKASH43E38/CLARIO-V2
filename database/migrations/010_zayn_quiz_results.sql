CREATE TABLE IF NOT EXISTS quiz_results (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    orchestration_id TEXT NOT NULL UNIQUE,
    concept_id TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('EASY', 'MEDIUM', 'HARD')),
    time_limit_seconds INTEGER NOT NULL CHECK (time_limit_seconds IN (30, 60, 90)),
    questions_json TEXT NOT NULL,
    answer_key_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'GENERATED'
        CHECK (status IN ('GENERATED', 'IN_PROGRESS', 'SUBMITTED')),
    submitted_answers_json TEXT,
    correctness_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE
);
