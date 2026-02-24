-- Migration 001: Create agents table
CREATE TABLE agents (
  id TEXT PRIMARY KEY,
  folder_path TEXT NOT NULL,
  state TEXT DEFAULT 'idle',
  current_location TEXT DEFAULT 'lounge',
  pixel_position JSONB,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Migration 002: Create learnings table
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

-- Migration 003: Create memories table
CREATE TABLE memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT REFERENCES agents(id),
  memory_type TEXT,
  summary TEXT NOT NULL,
  full_content JSONB,
  emotional_valence TEXT,
  related_learning_ids UUID[] DEFAULT '{}',
  tags TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_memories_agent ON memories(agent_id, created_at DESC);
CREATE INDEX idx_memories_type ON memories(memory_type);

-- Migration 004: Create sessions table
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type TEXT NOT NULL,
  participants TEXT[] NOT NULL,
  initiator TEXT,
  status TEXT DEFAULT 'scheduled',
  intent TEXT,
  conversation JSONB DEFAULT '[]',
  artifacts JSONB DEFAULT '{}',
  learnings_created UUID[] DEFAULT '{}',
  error_log TEXT,
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_sessions_type_status ON sessions(type, status);
CREATE INDEX idx_sessions_participants ON sessions USING gin(participants);
CREATE INDEX idx_sessions_created ON sessions(created_at DESC);

-- Migration 005: Create content_pipeline table
CREATE TABLE content_pipeline (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status TEXT DEFAULT 'idea',
  platform TEXT NOT NULL,
  content_type TEXT,
  theme TEXT,
  angle TEXT,
  source_session_id UUID,
  draft_text TEXT,
  draft_metadata JSONB,
  drafted_by TEXT,
  posted_url TEXT,
  posted_at TIMESTAMPTZ,
  metrics JSONB,
  analyzed_at TIMESTAMPTZ,
  confidence NUMERIC(3,2),
  supporting_learnings UUID[] DEFAULT '{}',
  approval_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_content_status ON content_pipeline(status, created_at DESC);
CREATE INDEX idx_content_platform ON content_pipeline(platform, posted_at DESC);

-- Migration 006: Create external_signals table
CREATE TABLE external_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,
  source_id TEXT,
  author TEXT,
  content TEXT NOT NULL,
  url TEXT,
  metrics JSONB,
  tags TEXT[] DEFAULT '{}',
  ingested_at TIMESTAMPTZ DEFAULT now(),
  analyzed BOOLEAN DEFAULT false,
  analyzed_at TIMESTAMPTZ,
  UNIQUE(source, source_id)
);

CREATE INDEX idx_signals_source_analyzed ON external_signals(source, analyzed, ingested_at DESC);
CREATE INDEX idx_signals_tags ON external_signals USING gin(tags);

-- Migration 007: Create ceo_feedback table
CREATE TABLE ceo_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  feedback_type TEXT NOT NULL,
  target_type TEXT,
  target_id UUID,
  feedback_text TEXT,
  action TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ceo_feedback_target ON ceo_feedback(target_type, target_id);
CREATE INDEX idx_ceo_feedback_type ON ceo_feedback(feedback_type, created_at DESC);

-- Migration 008: Create company_trajectory table
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

-- Migration 012: Add seen-tracking fields to external_signals
ALTER TABLE external_signals
  ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ DEFAULT now(),
  ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT now(),
  ADD COLUMN IF NOT EXISTS seen_count INTEGER DEFAULT 1;

UPDATE external_signals
SET
  first_seen_at = COALESCE(first_seen_at, ingested_at, now()),
  last_seen_at = COALESCE(last_seen_at, ingested_at, now()),
  seen_count = COALESCE(seen_count, 1);

ALTER TABLE external_signals
  ALTER COLUMN first_seen_at SET NOT NULL,
  ALTER COLUMN last_seen_at SET NOT NULL,
  ALTER COLUMN seen_count SET NOT NULL;
