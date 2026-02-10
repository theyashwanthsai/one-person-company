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

