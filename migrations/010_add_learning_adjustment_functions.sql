-- Database functions for CEO feedback adjustments

-- Boost agent learnings (increase confidence)
CREATE OR REPLACE FUNCTION boost_agent_learnings(
  p_agent_id TEXT,
  p_boost_factor NUMERIC DEFAULT 0.1
)
RETURNS void AS $$
BEGIN
  UPDATE learnings
  SET 
    confidence = LEAST(confidence + p_boost_factor, 1.0),
    ceo_boosted = true,
    last_reinforced_at = now()
  WHERE agent_id = p_agent_id
    AND created_at > now() - interval '7 days'
    AND confidence < 1.0;
END;
$$ LANGUAGE plpgsql;

-- Dampen agent learnings (decrease confidence)
CREATE OR REPLACE FUNCTION dampen_agent_learnings(
  p_agent_id TEXT,
  p_dampen_factor NUMERIC DEFAULT 0.1
)
RETURNS void AS $$
BEGIN
  UPDATE learnings
  SET 
    confidence = GREATEST(confidence - p_dampen_factor, 0.3),
    last_reinforced_at = now()
  WHERE agent_id = p_agent_id
    AND created_at > now() - interval '7 days'
    AND confidence > 0.3;
END;
$$ LANGUAGE plpgsql;

-- Get standup readiness (check if agents have recent activity)
CREATE OR REPLACE FUNCTION get_standup_readiness()
RETURNS TABLE(
  agent_id TEXT,
  ready BOOLEAN,
  reason TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    a.id,
    CASE 
      WHEN l.learning_count > 0 THEN true
      ELSE false
    END as ready,
    CASE 
      WHEN l.learning_count > 0 THEN 'Has recent learnings'
      ELSE 'No recent activity'
    END as reason
  FROM agents a
  LEFT JOIN (
    SELECT agent_id, COUNT(*) as learning_count
    FROM learnings
    WHERE created_at > now() - interval '24 hours'
    GROUP BY agent_id
  ) l ON a.id = l.agent_id;
END;
$$ LANGUAGE plpgsql;

