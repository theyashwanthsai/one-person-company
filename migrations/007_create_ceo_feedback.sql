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

