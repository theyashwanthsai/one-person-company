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
- `skills/` - Session/task-specific skills

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
- **CEO Standup** - Discord-based async standup with agents
- **Brainstorm** - Creative ideation (Strategist + Creator)
- **Market Review** - Content validation with benchmarks
- **Watercooler** - Casual chats for weak signals
- **1-on-1** - Agent-initiated focused conversations
- **Scheduler** - Automated daily session orchestration
- **Content Pipeline** - Idea → Approved → Draft → Post lifecycle

### ✅ Agent Tool System
- **Tool Registry** — Auto-discovers tools from `tools/`
- **Tool Runner** — LLM ↔ tool execution loop with retries
- **12 Shared Tools** — learnings, memories, sessions, content pipeline, external integrations

- **surf_reddit.py** — Surf Reddit posts via public JSON endpoints
- **surf_hn.py** — Fetch HN stories via Algolia with time-window filters
- **store_external_signal.py** — Persist surf_* payloads to Supabase
- **publish_content.py** — Post tweets (single or threads)
- **fetch_metrics.py** — Pull engagement metrics and analyze performance

### 🚧 Next Up
- **Frontend** - Pixel art office dashboard
- **Discord Client** - Complete CEO standup + direct request flow
- **Deployment** - Production setup and cron jobs

**Progress:** 90+ items complete in `plan.md` (out of 150+)

---

## External Integration Tools

### Reddit (`surf_reddit.py`)
```python
result = await execute(
    subreddits=["MachineLearning", "buildapcsales"],
    sort="new",
    limit_per_subreddit=10,
    min_score=5,
    max_age_hours=12
)
# Returns: count, posts, top_post
```

**Features:**
- Public `/r/<subreddit>/<sort>.json` endpoints (no API key)
- Supports hot/new/top/rising plus time filters for top
- Filters by minimum score and max age
- Returns structured metadata so you can decide what to save via `store_external_signal`

### Hacker News (`surf_hn.py`)
```python
# Surf the last few hours of HN stories
result = await execute(
    hours_window=6,        # past 6 hours
    min_points=10,         # optional
    max_posts=50
)
# Returns: count, posts, top_post
```

**Features:**
- Algolia search_by_date (supports time ranges and pagination)
- Filter by minimum points / score
- Includes structured content + raw payloads for each story

### Store External Signal (`store_external_signal.py`)
```python
result = await execute(
    source="hackernews",
    category="hn_surf",
    signals=[post1, post2]
)
# Returns: signals_stored, signal_ids
```

**Features:**
- Persists structured payloads into `external_signals`
- Adds `ingested_at` automatically and retains the supplied metrics/raw_data

### Publishing (`publish_content.py`)
```python
# Post a single tweet
result = await execute(text="Hello world! 🚀")

# Post a thread (separate with \n---\n)
result = await execute(
    text="Tweet 1\n---\nTweet 2\n---\nTweet 3",
    draft_id="optional-pipeline-id"
)
# Returns: tweets_posted, is_thread, tweets[], primary_url
```

**Features:**
- OAuth 1.0a authentication
- Thread support (automatic replies)
- Updates content_pipeline if draft_id provided
- Returns URLs for all posted tweets

### Metrics (`fetch_metrics.py`)
```python
# Get engagement metrics
result = await execute(
    tweet_id="1234567890",
    update_pipeline=True
)
# Returns: metrics, performance, analysis
```

**Features:**
- Likes, retweets, replies, impressions
- Engagement rate calculation
- Performance classification (low/average/good/excellent)
- Viral potential and discussion quality analysis
- Auto-updates content_pipeline

### Testing External Tools

Run the test suite:
```bash
python3 tests/test_external_tools.py
```

This will:
1. Surf Hacker News, Reddit, and Twitter (when configured)
2. Persist a small sample into `external_signals` via `store_external_signal` if Supabase credentials are present
3. Optionally test publishing (confirmation required)
4. Optionally test metrics fetching

### API Setup

**Twitter API:**
1. Go to https://developer.twitter.com/en/portal/dashboard
2. Create a project and app
3. Set permissions to "Read and Write"
4. Generate API Key & Secret, Bearer Token, Access Token & Secret
5. Add to `.env`

**Reddit API:**
- No API key is required for `surf_reddit.py` in the current implementation.
- It uses Reddit's public `/r/<subreddit>/<sort>.json` endpoints with a custom user agent.

**Hacker News:**
- No API key needed! Works out of the box.

---

## Agent Tool System

### How It Works

Each tool is a Python file with two things:
- `SCHEMA` — OpenAI function calling format (dict)
- `execute(agent_id, **kwargs)` — runs the tool, returns string result

Tools live in one place:
- `tools/` — shared tools available to all agents

### Available Tools

**Knowledge & Memory:**
- `query_learnings` — Search team knowledge base
- `write_learning` — Document a pattern/insight/strategy
- `store_memory` — Record an experiential memory
- `recall_memories` — Search past experiences and interactions

**Communication:**
- `request_1on1` — Request conversation with another agent
- `discord_ceo` — Send Discord message to CEO (escalations, questions)
- `email_ops` — Check inbox updates or send an email

**External Ingestion:**
- `surf_reddit` — Surf Reddit posts via public JSON endpoints
- `surf_hn` — Surf Hacker News stories via Algolia time-window search
- `store_external_signal` — Persist selected signals after surf_ tools run
- `scan_external_source` — Search stored external signals

**Content & Publishing:**
- `check_content_pipeline` — View content pipeline status
- `publish_content` — Post tweets (supports threads)
- `fetch_metrics` — Get engagement metrics for published content

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

Create a Python file in `tools/`:

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
python3 tests/test_tools.py
```

---

## Engine — `workers/engine.py`

`workers/engine.py` orchestrates execution. Schedule data and Discord inbox logic are now split out:
- Schedule file: `workers/schedule.md`
- Discord inbox runtime: `lib/discord/inbox.py`

### How It Works

**Solo tasks:** Engine tells agent what to do → `run_agent_step()` → agent uses tools autonomously

**Meetings:** Engine orchestrates turn-taking → each turn is `run_agent_step()` with conversation history → agents use tools during conversation → natural conclusion detection

### Running

```bash
# Start the engine (runs on schedule)
python3 workers/engine.py

# Run a specific task right now
python3 workers/engine.py --run brainstorm
python3 workers/engine.py --run scan

# Run ALL tasks sequentially (full day)
python3 workers/engine.py --run-all

# See the schedule
python3 workers/engine.py --list
```

Startup behavior for always-on process managers:

- `ENGINE_CATCH_UP_ON_START=1` (default): run recently missed daily tasks on boot.
- `ENGINE_CATCH_UP_MINUTES=180` (default): how far back missed daily tasks are eligible for catch-up.
- `ENGINE_RUN_INTERVAL_ON_START=1` (default): run interval-based tasks once at boot so the process doesn't wait for the first interval boundary.

### Daily Schedule

```
08:00  Thea scans signals (solo)
08:30  Dara analyzes signals (solo)
09:00  CEO standup (meeting: all 3)
09:30  Thea scans signals (solo)
10:00  Dara reviews pipeline (solo)
10:30  Brainstorm (meeting: Thea + Kavi)
11:00  Kavi drafts content (solo)
11:30  Thea scans signals (solo)
12:00  Watercooler (meeting: random 2)
13:00  Thea scans signals (solo)
13:30  Dara deep analysis (solo)
14:00  Market review (meeting: all 3)
15:00  Brainstorm (meeting: Thea + Kavi)
15:30  Kavi drafts content (solo)
16:00  Thea scans signals (solo)
16:30  Watercooler (meeting: random 2)
17:00  Dara performance review (solo)
17:30  Thea final scan (solo)
```

### Adding a New Task

Add one entry to the list in `workers/schedule.md`:

```python
{
    "time": "18:00", "type": "solo",
    "agent": "creator_lead",
    "session_type": "review",
    "task": "Review all drafts from today. Polish the best one."
}
```

You can also run recurring tasks by specifying an interval:

```python
{
    "interval_minutes": 30, "type": "solo",
    "agent": "watari",
    "session_type": "email_check",
    "task": "Check email inbox and post updates to #mails."
}
```

That's it. The agent uses their tools to figure out how.

### Content Pipeline

Ideas flow through: `idea → approved → drafted → posted → analyzed`

```sql
SELECT title, status, priority FROM content_pipeline ORDER BY created_at DESC;
```

### Discord Setup (for CEO standup + direct requests)

1. Create bot(s) at https://discord.com/developers/applications
2. Add the bot(s) to your server with permission to read/send messages in `#general` and `#standup`
3. Add to `.env`:
```bash
DISCORD_BOT_TOKEN=your-discord-bot-token
DISCORD_CEO_USER_ID=your-discord-user-id
DISCORD_GENERAL_CHANNEL_ID=your-general-channel-id
DISCORD_STANDUP_CHANNEL_ID=your-standup-channel-id
DISCORD_POLL_SECONDS=60
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
