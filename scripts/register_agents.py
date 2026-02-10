import os
from pathlib import Path
from supabase import create_client
import frontmatter
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

agents_dir = Path(__file__).parent.parent / "agents"

print("🤖 Registering agents from folders...\n")

for agent_folder in agents_dir.iterdir():
    if not agent_folder.is_dir():
        continue
    
    soul_file = agent_folder / "soul.md"
    if not soul_file.exists():
        print(f"⚠️  Skipping {agent_folder.name} - no soul.md found")
        continue
    
    soul = frontmatter.load(soul_file)
    metadata = soul.metadata
    
    agent_data = {
        "id": metadata['id'],
        "folder_path": str(agent_folder.relative_to(agents_dir.parent)),
        "state": "idle",
        "current_location": metadata.get('location', {}).get('default', 'lounge'),
        "pixel_position": metadata.get('location', {}).get('pixel_position'),
        "metadata": {
            "name": metadata['name'],
            "role": metadata['role'],
            "capabilities": metadata.get('capabilities', []),
            "description": metadata.get('description', ''),
        }
    }
    
    try:
        supabase.table("agents").upsert(agent_data).execute()
        print(f"✓ Registered: {metadata['name']} ({metadata['id']})")
    except Exception as e:
        print(f"✗ Failed to register {metadata['name']}: {e}")

print(f"\n✓ Agent registration complete!")
print(f"\n💡 Agents are now ready to work. Their personalities live in:")
print(f"   agents/<agent_id>/soul.md")

