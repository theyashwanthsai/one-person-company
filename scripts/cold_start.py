import os
import re
from pathlib import Path
from supabase import create_client
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

COLD_START_FILE = Path(__file__).parent.parent / "seeds" / "cold_start_dump.md"


def read_cold_start_content():
    if not COLD_START_FILE.exists():
        print(f"❌ Cold start file not found: {COLD_START_FILE}")
        return None
    
    content = COLD_START_FILE.read_text()
    
    essays = re.split(r'Mini Essay \d+ —', content)
    essays = [e.strip() for e in essays if e.strip()]
    
    return {
        "full_text": content,
        "essays": essays,
        "essay_count": len(essays)
    }


def analyze_writing_style(content):
    print("\n📝 Analyzing writing style...")
    
    prompt = f"""Analyze this writer's style and extract key characteristics.

Content:
{content['full_text'][:3000]}

Return JSON with:
{{
  "tone": "description of tone",
  "style_traits": ["trait1", "trait2", ...],
  "common_techniques": ["technique1", "technique2", ...],
  "key_themes": ["theme1", "theme2", ...],
  "voice_summary": "one paragraph summary of voice"
}}"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    analysis = json.loads(response.choices[0].message.content)
    return analysis


def generate_learnings_for_agents(content, style_analysis):
    print("\n🧠 Generating seed learnings for each agent...")
    
    agents = {
        "strategist_lead": {
            "name": "Thea",
            "focus": "Extract strategic themes, narrative patterns, and long-term positioning insights"
        },
        "creator_lead": {
            "name": "Kavi",
            "focus": "Extract content structure techniques, hook patterns, and writing tactics"
        },
        "analyst_lead": {
            "name": "Dara",
            "focus": "Extract observable patterns, success factors, and what makes content work"
        }
    }
    
    all_learnings = {}
    
    for agent_id, agent_info in agents.items():
        print(f"\n  Generating learnings for {agent_info['name']}...")
        
        prompt = f"""You are {agent_info['name']}, analyzing the CEO's writing to learn their style.

CEO's content:
{content['full_text']}

Style analysis:
{json.dumps(style_analysis, indent=2)}

Your role focus: {agent_info['focus']}

Generate 8-10 high-quality learnings that will help you understand how the CEO writes and thinks.

Return JSON array of learnings:
[
  {{
    "type": "pattern" | "insight" | "preference" | "strategy",
    "statement": "clear, specific learning",
    "confidence": 0.7-0.95,
    "tags": ["relevant", "tags"],
    "evidence": "brief quote or reference"
  }}
]

Focus on actionable insights specific to your role."""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        learnings_data = json.loads(response.choices[0].message.content)
        all_learnings[agent_id] = learnings_data.get("learnings", learnings_data)
        
        print(f"    ✓ Generated {len(all_learnings[agent_id])} learnings")
    
    return all_learnings


def insert_learnings(agent_learnings):
    print("\n💾 Inserting learnings into database...")
    
    total_inserted = 0
    
    for agent_id, learnings in agent_learnings.items():
        for learning in learnings:
            learning_data = {
                "agent_id": agent_id,
                "type": learning["type"],
                "statement": learning["statement"],
                "confidence": learning["confidence"],
                "tags": learning.get("tags", []),
                "evidence_refs": [{
                    "source": "cold_start",
                    "content": learning.get("evidence", "")
                }],
                "source_session_id": None,
                "ceo_boosted": True,
            }
            
            try:
                supabase.table("learnings").insert(learning_data).execute()
                total_inserted += 1
            except Exception as e:
                print(f"    ✗ Failed to insert learning: {e}")
    
    print(f"\n✓ Inserted {total_inserted} learnings total")


def store_content_as_signals(content):
    print("\n📚 Storing essays as external signals...")
    
    for i, essay in enumerate(content['essays'], 1):
        title_match = re.match(r'^(.+?)\n', essay)
        title = title_match.group(1) if title_match else f"Essay {i}"
        
        signal_data = {
            "source": "your_blog",
            "source_id": f"cold_start_essay_{i}",
            "author": "CEO",
            "content": essay,
            "url": "cold_start",
            "tags": ["ai_agents", "writing_sample", "cold_start"],
            "analyzed": True,
        }
        
        try:
            supabase.table("external_signals").upsert(signal_data).execute()
            print(f"  ✓ Stored: {title[:60]}...")
        except Exception as e:
            print(f"  ✗ Failed to store essay {i}: {e}")


def main():
    print("🚀 Starting Cold Start Process\n")
    print("=" * 60)
    
    content = read_cold_start_content()
    if not content:
        return
    
    print(f"✓ Loaded {content['essay_count']} essays from cold_start_dump.md")
    
    style_analysis = analyze_writing_style(content)
    print(f"\n✓ Analyzed writing style:")
    print(f"  Tone: {style_analysis.get('tone', 'N/A')}")
    print(f"  Key themes: {', '.join(style_analysis.get('key_themes', [])[:3])}")
    
    agent_learnings = generate_learnings_for_agents(content, style_analysis)
    
    print("\n📊 Learning Summary:")
    for agent_id, learnings in agent_learnings.items():
        print(f"  {agent_id}: {len(learnings)} learnings")
    
    insert_learnings(agent_learnings)
    
    store_content_as_signals(content)
    
    print("\n" + "=" * 60)
    print("✅ Cold Start Complete!")
    print("\nYour agents now understand:")
    print("  • Your writing style and voice")
    print("  • Your key themes and focus areas")
    print("  • How you structure content")
    print("  • What makes your content work")
    print("\nThey're ready to work! 🎉")


if __name__ == "__main__":
    main()
