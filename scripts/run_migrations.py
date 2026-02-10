import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("⚠️  Supabase migrations cannot be run via Python script")
print("=" * 60)
print("\nSupabase doesn't support executing SQL via REST API.")
print("\n📋 To run migrations, choose one of these methods:\n")

print("Method 1: Supabase Dashboard (Recommended)")
print("  1. Go to your Supabase project")
print("  2. Click 'SQL Editor' in the left sidebar")
print("  3. Click 'New Query'")
print("  4. Copy contents of: migrations/all_migrations.sql")
print("  5. Paste and click 'Run'")
print("  ✓ All 8 tables created at once!\n")

print("Method 2: psql Command Line")
migrations_dir = Path(__file__).parent.parent / "migrations"
all_migrations = migrations_dir / "all_migrations.sql"

if all_migrations.exists():
    print(f"  psql $DATABASE_URL -f {all_migrations}")
    print("  (Requires DATABASE_URL in .env)\n")

print("Method 3: Individual Migrations (psql)")
migration_files = sorted([f for f in migrations_dir.glob("0*.sql")])
if migration_files:
    print(f"  Found {len(migration_files)} migration files:")
    for i, f in enumerate(migration_files, 1):
        print(f"  {i}. psql $DATABASE_URL -f {f}")

print("\n" + "=" * 60)
print("💡 After running migrations, verify in Supabase:")
print("   Dashboard → Table Editor → should see 8 tables")
print("=" * 60)
