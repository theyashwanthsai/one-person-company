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

