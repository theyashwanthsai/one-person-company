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
