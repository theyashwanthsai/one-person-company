import os
from pathlib import Path
from typing import Dict, List, Optional
import frontmatter
from supabase import create_client

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

AGENTS_DIR = Path(__file__).parent.parent / "agents"

_agent_cache = {}


def load_all_agents_metadata() -> Dict[str, dict]:
    agents = {}
    
    for agent_folder in AGENTS_DIR.iterdir():
        if not agent_folder.is_dir():
            continue
        
        soul_file = agent_folder / "soul.md"
        if not soul_file.exists():
            continue
        
        soul = frontmatter.load(soul_file)
        metadata = soul.metadata
        
        agents[metadata['id']] = {
            "id": metadata['id'],
            "name": metadata['name'],
            "role": metadata['role'],
            "description": metadata['description'],
            "capabilities": metadata.get('capabilities', []),
            "personality": metadata.get('personality', {}),
            "location": metadata.get('location', {}),
            "folder": str(agent_folder),
        }
    
    return agents


def load_agent_full(agent_id: str) -> dict:
    if agent_id in _agent_cache:
        return _agent_cache[agent_id]
    
    agent_folder = AGENTS_DIR / agent_id
    soul_file = agent_folder / "soul.md"
    
    if not soul_file.exists():
        raise FileNotFoundError(f"Agent {agent_id} not found")
    
    soul = frontmatter.load(soul_file)
    metadata = soul.metadata
    instructions = soul.content
    
    agent = {
        "id": metadata['id'],
        "name": metadata['name'],
        "role": metadata['role'],
        "description": metadata['description'],
        "capabilities": metadata.get('capabilities', []),
        "personality": metadata.get('personality', {}),
        "location": metadata.get('location', {}),
        "folder": str(agent_folder),
        "soul_instructions": instructions,
    }
    
    _agent_cache[agent_id] = agent
    return agent


def get_agent_db(agent_id: str) -> Optional[dict]:
    result = supabase.table("agents").select("*").eq("id", agent_id).execute()
    if result.data:
        return result.data[0]
    return None


def update_agent_state(agent_id: str, state: str):
    supabase.table("agents").update({"state": state}).eq("id", agent_id).execute()


def update_agent_location(agent_id: str, location: str, pixel_position: Optional[dict] = None):
    data = {"current_location": location}
    if pixel_position:
        data["pixel_position"] = pixel_position
    supabase.table("agents").update(data).eq("id", agent_id).execute()


def update_agent(agent_id: str, state: str = None, current_location: str = None):
    """Update agent state and/or location in one call."""
    data = {}
    if state:
        data["state"] = state
    if current_location:
        data["current_location"] = current_location
    if data:
        supabase.table("agents").update(data).eq("id", agent_id).execute()


def load_agent_prompt(agent_id: str, prompt_name: str) -> Optional[str]:
    agent_folder = AGENTS_DIR / agent_id
    prompt_file = agent_folder / "prompts" / f"{prompt_name}.md"
    
    if prompt_file.exists():
        return prompt_file.read_text()
    return None


def load_agent_reference(agent_id: str, reference_name: str) -> Optional[str]:
    agent_folder = AGENTS_DIR / agent_id
    ref_file = agent_folder / "references" / f"{reference_name}.md"
    
    if ref_file.exists():
        return ref_file.read_text()
    return None


def get_all_agents() -> List[dict]:
    result = supabase.table("agents").select("*").execute()
    
    agents = []
    for db_agent in result.data:
        agent_id = db_agent['id']
        metadata = load_all_agents_metadata().get(agent_id)
        
        if metadata:
            agents.append({
                **db_agent,
                "name": metadata['name'],
                "role": metadata['role'],
                "capabilities": metadata['capabilities'],
            })
    
    return agents

