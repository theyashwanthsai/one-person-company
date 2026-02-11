# One Person Company - Documentation

## Quick Start

**Important:** Migrations must be run in Supabase Dashboard or via psql. The Python script `run_migrations.py` is a helper that shows you how - it cannot execute SQL directly.

### Fast Setup (Recommended)
```bash
./setup.sh  # Auto-creates .env, venv, installs dependencies
```

### Manual Setup

**1. Database Setup**
```bash
# In Supabase Dashboard:
# 1. Go to SQL Editor (left sidebar)
# 2. Click "New Query"
# 3. Copy/paste contents of: migrations/all_migrations.sql
# 4. Click "Run"
# ✓ All 8 tables created!

# Alternative (if you have psql):
# psql $DATABASE_URL -f migrations/all_migrations.sql
```

**2. Environment**
```bash
cp env.example .env
# Edit .env and add:
# - SUPABASE_URL (Supabase Dashboard → Settings → API)
# - SUPABASE_SERVICE_ROLE_KEY
# - OPENAI_API_KEY (platform.openai.com/api-keys)
```

**3. Dependencies**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**4. Register & Cold Start**
```bash
python scripts/register_agents.py     # Register Thea, Kavi, Dara
python scripts/cold_start.py          # Mini essays
python scripts/ingest_website.py      # Website articles
```

---

## Your Team

| Name | Role | Personality |
|------|------|-------------|
| **Thea** | Strategy Lead | Sees patterns, long-term thinker |
| **Kavi** | Content Creator | Executes fast, creative |
| **Dara** | Data Analyst | Data-driven, precise |

**Agent Structure:** Each agent is a skill folder (`agents/<agent_id>/`) with:
- `soul.md` - Personality + instructions (required)
- `tools/` - Agent-specific scripts
- `references/` - Knowledge base
- `prompts/` - Session prompts

---

## Cold Start

**Two-part process** to teach agents your voice:

### Part 1: Mini Essays (`cold_start.py`)
Analyzes writing samples in `seeds/cold_start_dump.md` (your 7 mini essays).

```bash
python scripts/cold_start.py
```

**Result:** 24-30 learnings across all agents from curated content.

### Part 2: Website Articles (`ingest_github_articles.py`)
Scrapes **63 articles** (42,000+ words) from your GitHub repo.

```bash
python scripts/ingest_github_articles.py
```

**What it scrapes:**
- **63 markdown files** across all subdirectories:
  - `/ai_playbooks/` → CrewAI, DSPy, prompting guides
  - `/twitter_essays/` → MCP, frameworks, AI agents
  - `/computers/` → LLM series, backend, deep learning
  - `/osdevlogs/` → OS development logs
  - Root articles → AI predictions, personal essays
- **42,579 total words** of content
- Stores as **63 signals** in `external_signals` table
- Generates **24 learnings** (8 per agent)

**Source:** [github.com/theyashwanthsai/DigitalGarden](https://github.com/theyashwanthsai/DigitalGarden/tree/master/public/content)

**Why GitHub API?**
- ✅ Direct markdown access (no web scraping)
- ✅ Parses frontmatter automatically
- ✅ No browser/Selenium needed
- ✅ 100% reliable

**Expected output:**
```
✓ Found 63 markdown files
✓ Processed 63 articles (42,579 words)
✓ Stored 63 articles
✓ Generated 24 learnings
```

**Result:** Agents understand your writing voice across your entire blog. All learnings marked `ceo_boosted=true`.

---

## Core Libraries ✅

### `lib/tool_registry.py` - Tool Discovery & Execution
```python
from lib.tool_registry import get_tools_for_agent, get_tool_schemas, execute_tool, list_tools

# See what tools an agent has
list_tools('strategist_lead')

# Get OpenAI-format schemas (pass to chat.completions.create)
schemas = get_tool_schemas('strategist_lead')

# Execute a tool
result = await execute_tool('strategist_lead', 'query_learnings', {'tags': ['content']})
```
**Features:** Auto-discovers shared + agent-specific tools, validates schemas, handles sync/async.

### `lib/tool_runner.py` - Agent Execution Engine
```python
from lib.tool_runner import run_agent_with_tools, run_agent_step

# Low-level: full control
response, tool_calls = await run_agent_with_tools(
    agent_id='strategist_lead',
    system_prompt='You are Thea...',
    user_prompt='Scan for trends',
    model='gpt-4o'
)

# High-level: loads soul.md + tools automatically
response, tool_calls = await run_agent_step(
    agent_id='strategist_lead',
    task='Find patterns in recent content performance'
)
```
**Features:** Automatic tool loop, retries, logs tool calls, safety limits.

### `lib/llm.py` - OpenAI Wrapper
```python
from lib.llm import chat_completion, chat_completion_json, chat_with_history

# Simple completion
response = chat_completion(
    system="You are Thea", 
    user="What trends?",
    model="gpt-4o-mini"
)

# JSON mode
json_str = chat_completion_json(system="...", user="...", model="gpt-4o-mini")

# With conversation history
response = chat_with_history(messages=[...], model="gpt-4o-mini")
```
**Features:** 3 retry attempts, exponential backoff, clean API.

### `lib/learnings.py` - Learning System
```python
from lib.learnings import query_learnings, write_learning, boost_learning

# Query
learnings = query_learnings('strategist_lead', tags=['trends'], min_confidence=0.6, limit=5)

# Write
write_learning(agent_id='creator_lead', type='pattern', statement='Questions > statements', confidence=0.8)

# Boost (CEO action)
boost_learning(learning_id)  # Increases confidence by 20%, caps at 0.95
```
**Features:** Filter by type/tags/confidence, CEO boost/dismiss, summary stats.

### `lib/memories.py` - Memory System
```python
from lib.memories import store_memory, query_memories, link_memory_to_learning

# Store
store_memory(agent_id='analyst_lead', memory_type='conversation', summary='Debated metrics with Kavi', emotional_valence='challenging')

# Query
recent = query_memories('analyst_lead', memory_type='conversation', limit=5)

# Link to learning
link_memory_to_learning(memory_id, learning_id)
```
**Features:** Emotional valence tracking, tag search, learning links.

### `lib/sessions.py` - Session Engine
```python
from lib.sessions import create_session, append_turn, complete_session

# Create
session_id = create_session(type='ceo_standup', participants=['ceo', 'strategist_lead'])

# Add turns
append_turn(session_id, speaker='strategist_lead', text='Scanned 50 tweets...')

# Complete
complete_session(session_id, artifacts={'decisions': ['Focus on AI agents']})
```
**Features:** Status tracking, conversation history, artifact storage, learning links.

---

## Build Status

### ✅ Complete
- **Database** - 8 tables (agents, learnings, memories, sessions, content_pipeline, external_signals, ceo_feedback, company_trajectory)
- **Agent System** - 3 agents (Thea, Kavi, Dara) with skill folders
- **Cold Start** - Writing analysis + learning generation
- **Core Libraries** - LLM, learnings, memories, sessions, agents

### ✅ Sessions System
- **CEO Standup** - Email-based async standup with agents
- **Brainstorm** - Creative ideation (Strategist + Creator)
- **Market Review** - Content validation with benchmarks
- **Watercooler** - Casual chats for weak signals
- **1-on-1** - Agent-initiated focused conversations
- **Scheduler** - Automated daily session orchestration
- **Content Pipeline** - Idea → Approved → Draft → Post lifecycle

### ✅ Agent Tool System
- **Tool Registry** — Auto-discovers tools from `tools/` and `agents/<id>/tools/`
- **Tool Runner** — LLM ↔ tool execution loop with retries
- **7 Shared Tools** — query_learnings, write_learning, store_memory, recall_memories, request_1on1, email_ceo, scan_external_source, check_content_pipeline

### 🚧 Next Up
- **Content Drafting & Posting** - Agents write and publish
- **External Scanning** - Twitter/Reddit/HN ingestion
- **Frontend** - Pixel art office dashboard

**Progress:** 80+ items complete in `plan.md` (out of 150+)

---

## Agent Tool System

### How It Works

Each tool is a Python file with two things:
- `SCHEMA` — OpenAI function calling format (dict)
- `execute(agent_id, **kwargs)` — runs the tool, returns string result

Tools live in two places:
- `tools/` — shared tools available to all agents
- `agents/<agent_id>/tools/` — agent-specific tools (override shared ones)

### Available Tools

| Tool | Description |
|------|-------------|
| `query_learnings` | Search team knowledge base |
| `write_learning` | Document a pattern/insight/strategy |
| `store_memory` | Record an experiential memory |
| `recall_memories` | Search past experiences and interactions |
| `request_1on1` | Request conversation with another agent |
| `email_ceo` | Send email to CEO (escalations, questions) |
| `scan_external_source` | Search external signals (Twitter, Reddit, HN) |
| `check_content_pipeline` | View content pipeline status |

### Running an Agent with Tools

```python
from lib.tool_runner import run_agent_step

# One function call: loads soul.md, discovers tools, runs LLM loop
response, tool_calls = await run_agent_step(
    agent_id='strategist_lead',
    task='Scan for trending topics and document any new patterns'
)
# Agent will autonomously decide which tools to call
```

### Adding a New Tool

Create a Python file in `tools/` (shared) or `agents/<agent_id>/tools/` (agent-specific):

```python
# tools/my_tool.py
SCHEMA = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "What this tool does",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "..."}
            },
            "required": ["param1"]
        }
    }
}

def execute(agent_id: str, **kwargs):
    # Do something
    return "Result string for the LLM"
```

That's it. The registry auto-discovers it.

### Testing

```bash
python3 scripts/test_tools.py
```

---

## Sessions System

### How Sessions Work

All sessions follow the same pattern:
1. **Create session** → record in `sessions` table
2. **Agent interactions** → LLM-generated conversation turns
3. **Store learnings** → `learnings` table (what was discovered)
4. **Store memories** → `memories` table (what happened, emotional context)
5. **Complete session** → artifacts stored, states reset

Every session writes to **both** learnings and memories. Learnings are factual insights; memories are experiential records of what happened.

### Session Types

| Type | Participants | Schedule | Purpose |
|------|-------------|----------|---------|
| CEO Standup | You + 3 leads | Daily 9 AM | Email-based async sync |
| Brainstorm | Strategist + Creator | 2x/day | Creative ideation |
| Market Review | All 3 leads | 1x/day | Validate content ideas |
| Watercooler | Random 2-3 | 2x/day | Weak signal discovery |

### CEO Standup (Email-Based)

**Flow:** Reminder email → Agent updates → CEO receives summary → CEO replies with feedback

**Agent Updates:**
- What changed since last time
- What they're confident about
- What they're uncertain about

**CEO Commands (reply to email):**
- `boost [agent_id]` → increase learning confidence
- `dampen [agent_id]` → decrease confidence
- `focus on [topic]` → set strategic direction for all agents

**Email Setup (Gmail):**
1. Enable 2-Step Verification at https://myaccount.google.com/security
2. Create App Password at https://myaccount.google.com/apppasswords
3. Add to `.env`:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
IMAP_HOST=imap.gmail.com
EMAIL_ADDRESS=your-bot-email@gmail.com
EMAIL_PASSWORD=your-16-char-app-password
CEO_EMAIL=your-personal-email@gmail.com
```

### Brainstorm Session

- Strategist opens with themes/insights from learnings
- 10-turn creative dialogue
- Extracts 2-5 content ideas → `content_pipeline` table
- Each agent stores learnings AND memories from the conversation

### Market Review Session

- Picks top unreviewed idea from `content_pipeline`
- Analyst scans `external_signals` for similar content
- Three-way evaluation (Analyst + Strategist + Creator)
- Group decision: **approve / reshape / kill**
- Updates `content_pipeline` status

### Watercooler Session

- Random 2-3 agents, random casual topic
- Short (3-5 turns), high creativity (temp 0.9)
- Extracts weak signals (low confidence, high potential)
- Agents store memories of the conversation

### Running Sessions

```bash
# Test individual sessions
python3 workers/brainstorm.py
python3 workers/market_review.py
python3 workers/watercooler.py
python3 workers/ceo_standup.py

# Run automated scheduler (all sessions on schedule)
python3 workers/scheduler.py
```

### Daily Schedule

```
09:00 → CEO Standup (you get email)
10:30 → Brainstorm (ideas generated)
12:00 → Watercooler (casual chat)
14:00 → Market Review (validate top idea)
15:00 → Brainstorm (more ideas)
16:30 → Watercooler (weak signals)
```

### Content Pipeline

Ideas flow through: `idea → approved → drafted → posted → analyzed`

```sql
-- Check pipeline
SELECT title, status, priority FROM content_pipeline ORDER BY created_at DESC;
```

---

## Frontend Architecture

### Recommended: Direct Supabase Client

Frontend uses Supabase JS client directly for reads + realtime:

```html
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script>
    const supabase = supabase.createClient('YOUR_URL', 'YOUR_ANON_KEY');

    // Fetch agents
    const { data } = await supabase.from('agents').select('*');

    // Realtime updates
    supabase.channel('agents-changes')
        .on('postgres_changes', { event: '*', schema: 'public', table: 'agents' },
            (payload) => updateSingleAgent(payload.new))
        .subscribe();
</script>
```

Later: Add FastAPI for complex operations (CEO feedback, session triggers).

---

## Complete Cold Start Workflow

```bash
# 1. Register your team
python scripts/register_agents.py

# 2. Teach from curated samples (7 mini essays)
python scripts/cold_start.py
# → 24-30 learnings

# 3. Teach from full body of work (up to 50 articles)
python scripts/ingest_website.py
# → 15-24 additional learnings

# Total: 40-60 CEO-boosted learnings across all agents
```

## Database Migrations

```bash
# Run in Supabase SQL Editor (in order):
migrations/001_create_agents.sql
migrations/002_create_learnings.sql
migrations/003_create_memories.sql
migrations/004_create_sessions.sql
migrations/005_create_external_signals.sql
migrations/006_create_ceo_feedback.sql
migrations/007_create_company_trajectory.sql
# ... or use all_migrations.sql for 001-008

# Session system additions:
migrations/010_add_learning_adjustment_functions.sql
migrations/011_create_content_pipeline.sql
```

See `plan.md` for full build order.

