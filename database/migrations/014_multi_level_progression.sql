PRAGMA foreign_keys=OFF;

ALTER TABLE topics
    ADD COLUMN owner_session_id TEXT REFERENCES learning_sessions(id) ON DELETE CASCADE;

CREATE TABLE research_packages_new (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    level_id TEXT,
    attempt_number INTEGER NOT NULL DEFAULT 1 CHECK (attempt_number >= 1),
    package_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (session_id, attempt_number),
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE
);

INSERT INTO research_packages_new (
    id, session_id, level_id, attempt_number, package_json, created_at
)
SELECT id, session_id, NULL, 1, package_json, created_at
FROM research_packages;

DROP TABLE research_packages;
ALTER TABLE research_packages_new RENAME TO research_packages;

CREATE INDEX ix_research_packages_session_level_attempt
    ON research_packages (session_id, level_id, attempt_number);

ALTER TABLE adaptive_decisions ADD COLUMN level_id TEXT;

PRAGMA foreign_keys=ON;
