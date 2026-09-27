-- Initial CLARIO Schema matching DATABASE.md

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learner_profiles (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    learning_goal TEXT NOT NULL,
    current_level TEXT NOT NULL,
    learning_preference TEXT NOT NULL,
    interests TEXT NOT NULL,
    initial_confidence INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    sequence_order INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    title TEXT NOT NULL,
    base_difficulty INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS concept_performances (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('learning', 'mastered', 'remediating')),
    difficulty_level INTEGER NOT NULL DEFAULT 1,
    mastery_score REAL NOT NULL DEFAULT 0.0,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES learner_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    UNIQUE(profile_id, concept_id)
);

CREATE TABLE IF NOT EXISTS learning_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    concept_id TEXT,
    companion_type TEXT NOT NULL,
    content_payload TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES learning_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS learner_responses (
    id TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL,
    response_text TEXT NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evaluations (
    id TEXT PRIMARY KEY,
    response_id TEXT NOT NULL,
    evaluator_name TEXT NOT NULL,
    score REAL NOT NULL,
    feedback_payload TEXT NOT NULL,
    remediation_required INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (response_id) REFERENCES learner_responses(id) ON DELETE CASCADE
);
