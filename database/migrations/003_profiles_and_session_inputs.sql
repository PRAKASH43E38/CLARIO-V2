ALTER TABLE users ADD COLUMN name TEXT;
ALTER TABLE users ADD COLUMN gender TEXT;
ALTER TABLE users ADD COLUMN basic_details TEXT;
ALTER TABLE users ADD COLUMN authentication_provider TEXT NOT NULL DEFAULT 'email';

CREATE TABLE IF NOT EXISTS mind_profiles (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    learning_motivation TEXT NOT NULL,
    preferred_explanation TEXT NOT NULL,
    support_when_stuck TEXT NOT NULL,
    feedback_preference TEXT NOT NULL,
    challenge_preference TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS session_inputs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    task TEXT NOT NULL,
    goal TEXT NOT NULL,
    learner_state TEXT NOT NULL,
    interest TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE
);
