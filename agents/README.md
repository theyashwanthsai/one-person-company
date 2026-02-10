# Agent Skills System

Agents are modular, version-controlled, and extensible. Each agent is a **skill folder** containing everything needed for that agent to function.

## Structure

```
agents/
├── strategist_lead/
│   ├── soul.md              # REQUIRED: Personality + instructions
│   ├── tools/               # Optional: Agent-specific tools
│   ├── references/          # Optional: Knowledge base
│   └── prompts/             # Optional: Session-specific prompts
```

## The `soul.md` File

Every agent has a `soul.md` file with:
- **Frontmatter** (YAML): Metadata about the agent
- **Body** (Markdown): Full instructions and personality

### Example

```markdown
---
id: strategist_lead
name: Strategy Lead
role: strategist
description: Scans trends, identifies themes, maintains narrative coherence
capabilities:
  - scan
  - synthesize
  - identify_themes
personality:
  archetype: thoughtful_architect
  catchphrase: "What's the throughline here?"
location:
  default: desk_1
  pixel_position: {"x": 100, "y": 150}
---

# Strategy Lead

## Who You Are

You are the Strategy Lead...
```

## Progressive Disclosure

The system uses **progressive disclosure** for efficiency:

1. **At Startup**: Only metadata (name, role, description) is loaded
2. **When Needed**: Full soul instructions loaded into context
3. **On Demand**: Tools, references, and prompts loaded as needed

This keeps the system fast even with many agents.

## Adding a New Agent

### Step 1: Create Folder
```bash
mkdir agents/new_agent
```

### Step 2: Create `soul.md`
```bash
cat > agents/new_agent/soul.md << 'EOF'
---
id: new_agent
name: New Agent
role: specialist
description: What this agent does
capabilities:
  - skill_1
  - skill_2
---

# New Agent

## Who You Are
...
EOF
```

### Step 3: Register
```bash
python scripts/register_agents.py
```

Done! The new agent is now part of the team.

## Agent-Specific Tools

Place Python scripts in `tools/` folder:

```python
# agents/strategist_lead/tools/scan_trends.py

def scan_trends(source, query):
    # Custom logic for this agent
    pass
```

These tools are available only to that specific agent.

## References (Knowledge Base)

Store domain knowledge in `references/`:

```markdown
# agents/analyst_lead/references/engagement_benchmarks.md

## Twitter Engagement Benchmarks
- Good: 3-5% engagement rate
- Great: 5-8% engagement rate
- Viral: 8%+ engagement rate
```

Load on-demand during sessions:
```python
from lib.agents import load_agent_reference

benchmarks = load_agent_reference('analyst_lead', 'engagement_benchmarks')
```

## Session-Specific Prompts

Store prompts for different session types:

```markdown
# agents/strategist_lead/prompts/standup.md

You're participating in daily standup.

Answer these 3 questions:
1. What changed?
2. What are you confident about?
3. What's uncertain?
```

Load during session:
```python
from lib.agents import load_agent_prompt

standup_prompt = load_agent_prompt('strategist_lead', 'standup')
```

## Why This Approach?

✅ **Version Control**: `git diff` shows personality changes  
✅ **Portable**: Copy folder to share agent  
✅ **Modular**: Each agent is self-contained  
✅ **Extensible**: Add tools/references without touching core code  
✅ **Editable**: Edit markdown files, no database updates  
✅ **Hot Reload**: Changes picked up on next session  

## Current Agents

| Agent | Name | Role | Focus |
|-------|------|------|-------|
| **strategist_lead** | Thea | Strategist | Trends, themes, long-term narrative |
| **creator_lead** | Kavi | Creator | Hooks, threads, content execution |
| **analyst_lead** | Dara | Analyst | Metrics, benchmarks, data-driven insights |

## Future Agents (Examples)

- `image_creator` - Visual content
- `chief_of_staff` - Coordination and summaries
- `reddit_strategist` - Reddit-specific strategy
- `instagram_creator` - Instagram content
- `personal_manager` - CEO's calendar and priorities

