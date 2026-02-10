CREATE TABLE learnings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT REFERENCES agents(id),
  type TEXT NOT NULL,
  statement TEXT NOT NULL,
  confidence NUMERIC(3,2) DEFAULT 0.60,
  evidence_refs JSONB DEFAULT '[]',
  tags TEXT[] DEFAULT '{}',
  source_session_id UUID,
  ceo_boosted BOOLEAN DEFAULT false,
  decay_rate NUMERIC(3,2) DEFAULT 0.95,
  last_reinforced_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_learnings_agent_confidence ON learnings(agent_id, confidence DESC);
CREATE INDEX idx_learnings_tags ON learnings USING gin(tags);
CREATE INDEX idx_learnings_type ON learnings(type);

