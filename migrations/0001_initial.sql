PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS images (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL,
  expected_subject TEXT NOT NULL, caption_hint TEXT NOT NULL,
  attributes_json TEXT NOT NULL DEFAULT '[]', demo_confidence REAL NOT NULL DEFAULT 0.96,
  image_url TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT 'curated-demo',
  tags_json TEXT, vector_json TEXT, confidence REAL,
  status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_images_status ON images(status);
CREATE INDEX IF NOT EXISTS ix_images_category_subject ON images(category, expected_subject);
CREATE TABLE IF NOT EXISTS posts (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL,
  expected_category TEXT NOT NULL, expected_subject TEXT NOT NULL,
  vector_json TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_posts_expected_subject ON posts(expected_category, expected_subject);
CREATE TABLE IF NOT EXISTS suggestions (
  id TEXT PRIMARY KEY, post_id TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  image_id TEXT REFERENCES images(id) ON DELETE SET NULL,
  similarity REAL NOT NULL, confidence REAL, decision TEXT NOT NULL,
  reason TEXT NOT NULL, rank INTEGER, review_status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_suggestions_post ON suggestions(post_id, created_at);
CREATE INDEX IF NOT EXISTS ix_suggestions_review ON suggestions(review_status);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
  total INTEGER NOT NULL DEFAULT 0, processed INTEGER NOT NULL DEFAULT 0,
  succeeded INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0,
  attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs(status);
CREATE TABLE IF NOT EXISTS ai_calls (
  id TEXT PRIMARY KEY, provider TEXT NOT NULL, operation TEXT NOT NULL,
  model TEXT NOT NULL, image_id TEXT REFERENCES images(id) ON DELETE SET NULL,
  post_id TEXT REFERENCES posts(id) ON DELETE SET NULL,
  job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
  status TEXT NOT NULL, input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0, cost_usd REAL NOT NULL DEFAULT 0,
  duration_ms INTEGER NOT NULL DEFAULT 0, error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_ai_calls_created ON ai_calls(created_at);
CREATE INDEX IF NOT EXISTS ix_ai_calls_job ON ai_calls(job_id);
