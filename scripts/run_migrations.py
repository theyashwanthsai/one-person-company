import os
from pathlib import Path
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

migrations_dir = Path(__file__).parent.parent / "migrations"
migration_files = sorted([f for f in migrations_dir.glob("*.sql") if f.name != "README.md"])

print(f"Found {len(migration_files)} migrations")

for migration_file in migration_files:
    print(f"\nRunning {migration_file.name}...")
    sql = migration_file.read_text()
    
    try:
        supabase.postgrest.rpc("exec_sql", {"sql": sql}).execute()
        print(f"✓ {migration_file.name} completed")
    except Exception as e:
        print(f"✗ {migration_file.name} failed: {e}")
        break

print("\n✓ All migrations completed!")

