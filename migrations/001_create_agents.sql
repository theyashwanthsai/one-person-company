CREATE TABLE agents (
  id TEXT PRIMARY KEY,
  folder_path TEXT NOT NULL,
  state TEXT DEFAULT 'idle',
  current_location TEXT DEFAULT 'lounge',
  pixel_position JSONB,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

