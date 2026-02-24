# Database Migrations

Run these in order in your Supabase SQL Editor.

## Order

1. `001_create_agents.sql`
2. `002_create_learnings.sql`
3. `003_create_memories.sql`
4. `004_create_sessions.sql`
5. `005_create_content_pipeline.sql`
6. `006_create_external_signals.sql`
7. `007_create_ceo_feedback.sql`
8. `008_create_company_trajectory.sql`
9. `009_update_agent_positions.sql`
10. `010_add_learning_adjustment_functions.sql`
11. `011_create_content_pipeline.sql`
12. `012_add_external_signal_seen_tracking.sql`

## How to Run

### Option 1: All-in-One (Recommended)
**Use `all_migrations.sql` to create all tables at once:**

**Supabase Dashboard:**
1. Go to your Supabase project
2. Click "SQL Editor" in the left sidebar
3. Click "New Query"
4. Copy **entire contents** of `all_migrations.sql`
5. Paste and click "Run"
6. ✓ All 8 tables created!

**Command Line (if you have psql):**
```bash
psql $DATABASE_URL -f migrations/all_migrations.sql
```

### Option 2: Individual Files
Run files 001-012 in order if you prefer granular control.

**Note:** `python scripts/run_migrations.py` won't work - Supabase doesn't support SQL execution via REST API. Use the dashboard or psql.

## Seed Data

After migrations, run seed data:
```bash
psql $DATABASE_URL -f seeds/001_seed_agents.sql
```

Or copy contents to Supabase SQL Editor.
