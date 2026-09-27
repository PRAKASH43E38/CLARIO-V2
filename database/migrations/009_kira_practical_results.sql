CREATE TABLE IF NOT EXISTS practical_results (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    orchestration_id TEXT NOT NULL UNIQUE,
    concept_id TEXT NOT NULL,
    scenario TEXT NOT NULL,
    practical_task TEXT NOT NULL,
    real_world_context TEXT NOT NULL,
    expected_action TEXT NOT NULL,
    success_criteria TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    research_source_ids TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE
);
