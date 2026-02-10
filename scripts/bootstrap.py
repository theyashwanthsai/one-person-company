import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

print("="*60)
print("🚀 ONE PERSON COMPANY - BOOTSTRAP")
print("="*60)
print()

def check_env():
    required = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "OPENAI_API_KEY"]
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("   Please configure your .env file\n")
        return False
    
    print("✓ Environment variables configured\n")
    return True


def run_script(name, description):
    print(f"{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}\n")
    
    script_path = Path(__file__).parent / f"{name}.py"
    
    if not script_path.exists():
        print(f"⚠️  Script {name}.py not found, skipping\n")
        return False
    
    import subprocess
    result = subprocess.run([sys.executable, str(script_path)], capture_output=False)
    
    if result.returncode != 0:
        print(f"\n⚠️  {name}.py completed with errors\n")
        return False
    
    print()
    return True


def main():
    if not check_env():
        sys.exit(1)
    
    steps = [
        ("register_agents", "Step 1: Register Agents"),
        ("cold_start", "Step 2: Process CEO's Mini Essays"),
        ("ingest_website", "Step 3: Scrape Website Articles"),
    ]
    
    for script_name, description in steps:
        success = run_script(script_name, description)
        if not success:
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("\n⚠️  Bootstrap stopped")
                sys.exit(1)
    
    print("="*60)
    print("✅ BOOTSTRAP COMPLETE")
    print("="*60)
    print()
    print("Your AI team is ready!")
    print()
    print("Team members:")
    print("  • Thea (Strategy Lead) - Sees patterns, identifies themes")
    print("  • Kavi (Content Creator) - Crafts hooks, writes content")
    print("  • Dara (Data Analyst) - Tracks metrics, validates with data")
    print()
    print("Next steps:")
    print("  1. Check Supabase → agents table (should have 3 rows)")
    print("  2. Check learnings table (should have 30+ entries)")
    print("  3. Run your first session: python workers/ceo_standup.py")
    print()


if __name__ == "__main__":
    main()

