CREATE TABLE company_trajectory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  period_type TEXT NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  agent_summaries JSONB DEFAULT '{}',
  consolidated_summary TEXT,
  metrics JSONB,
  top_learnings UUID[],
  top_content UUID[],
  challenges TEXT[],
  direction TEXT,
  momentum_score NUMERIC(3,2),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(period_type, period_start)
);

CREATE INDEX idx_trajectory_period ON company_trajectory(period_type, period_start DESC);

