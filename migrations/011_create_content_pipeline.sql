-- Content Pipeline Table
-- Stores content ideas through their lifecycle: idea → approved → drafted → posted → analyzed

CREATE TABLE content_pipeline (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'idea',
  -- status: idea | approved | rejected | drafted | posted | analyzed
  
  platform TEXT DEFAULT 'twitter',
  -- platform: twitter | linkedin | blog
  
  draft_content TEXT,
  final_content TEXT,
  
  tags TEXT[] DEFAULT '{}',
  priority TEXT DEFAULT 'medium',
  -- priority: low | medium | high
  
  source_session_id UUID REFERENCES sessions(id),
  -- Which session generated this idea
  
  review_notes TEXT,
  -- Market review feedback
  
  created_by TEXT REFERENCES agents(id),
  reviewed_at TIMESTAMPTZ,
  drafted_at TIMESTAMPTZ,
  posted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_content_pipeline_status ON content_pipeline(status);
CREATE INDEX idx_content_pipeline_priority ON content_pipeline(priority DESC, created_at DESC);
CREATE INDEX idx_content_pipeline_tags ON content_pipeline USING gin(tags);
CREATE INDEX idx_content_pipeline_platform ON content_pipeline(platform);

-- Get next content for review (helper function)
CREATE OR REPLACE FUNCTION get_next_content_for_review()
RETURNS TABLE(
  id UUID,
  title TEXT,
  description TEXT,
  tags TEXT[],
  priority TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    c.id,
    c.title,
    c.description,
    c.tags,
    c.priority
  FROM content_pipeline c
  WHERE c.status = 'idea'
  ORDER BY 
    CASE c.priority
      WHEN 'high' THEN 3
      WHEN 'medium' THEN 2
      WHEN 'low' THEN 1
    END DESC,
    c.created_at DESC
  LIMIT 1;
END;
$$ LANGUAGE plpgsql;

