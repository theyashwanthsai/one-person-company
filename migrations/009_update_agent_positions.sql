-- Update agent positions to match dashboard layout
-- Run this in Supabase SQL Editor

UPDATE agents 
SET pixel_position = '{"x": 30, "y": 16}'::jsonb
WHERE id = 'strategist_lead';

UPDATE agents 
SET pixel_position = '{"x": 50.5, "y": 16}'::jsonb
WHERE id = 'creator_lead';

UPDATE agents 
SET pixel_position = '{"x": 40.5, "y": 16}'::jsonb
WHERE id = 'analyst_lead';

-- Verify updates
SELECT id, folder_path, pixel_position, state 
FROM agents 
ORDER BY id;

