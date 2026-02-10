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

