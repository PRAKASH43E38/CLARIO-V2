CREATE TABLE IF NOT EXISTS clario_orchestrations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    cala_plan_id TEXT NOT NULL,
    current_state TEXT NOT NULL,
    current_step TEXT NOT NULL,
    research_package_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (cala_plan_id) REFERENCES cala_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (research_package_id) REFERENCES research_packages(id) ON DELETE SET NULL
);
