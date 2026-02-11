import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


## Positions will change depending if they are idle, meeting or chilling
positions = {
    "strategist_lead": {"x": 30, "y": 16},
    "creator_lead": {"x": 50.5, "y": 16},
    "analyst_lead": {"x": 40.5, "y": 16}
}

for agent_id, pos in positions.items():
    result = supabase.table("agents").update({
        "pixel_position": {"x": pos["x"], "y": pos["y"]}
    }).eq("id", agent_id).execute()
    
    print(f"Updated {agent_id}: {pos}")

print("\n✓ All agent positions updated in database")

