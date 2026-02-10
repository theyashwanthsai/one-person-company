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

## How to Run

### Option 1: Supabase Dashboard
1. Go to your Supabase project
2. Click "SQL Editor" in the left sidebar
3. Copy contents of each migration file
4. Paste and click "Run"
5. Repeat for all 8 files in order

### Option 2: Python Script
```bash
python scripts/run_migrations.py
```

## Seed Data

After migrations, run seed data:
```bash
psql $DATABASE_URL -f seeds/001_seed_agents.sql
```

Or copy contents to Supabase SQL Editor.

