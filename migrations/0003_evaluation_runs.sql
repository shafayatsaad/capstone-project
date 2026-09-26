CREATE TABLE IF NOT EXISTS evaluation_runs (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL DEFAULT 'demo',
  cases INTEGER NOT NULL,
  correct INTEGER NOT NULL,
  top1_precision REAL NOT NULL,
  results_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_evaluation_runs_tenant_created ON evaluation_runs(tenant_id,created_at);
