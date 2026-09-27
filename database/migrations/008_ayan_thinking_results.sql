CREATE TABLE IF NOT EXISTS thinking_results (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    orchestration_id TEXT NOT NULL UNIQUE,
    concept TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (orchestration_id) REFERENCES clario_orchestrations(id) ON DELETE CASCADE
);
