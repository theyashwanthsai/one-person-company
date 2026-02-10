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

