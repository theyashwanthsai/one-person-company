# One Person Company - Documentation

## Quick Start

### Fast Setup (Recommended)
```bash
./setup.sh  # Auto-creates .env, venv, installs dependencies
```

### Manual Setup

**1. Database Setup**
```bash
# In Supabase SQL Editor, paste: migrations/all_migrations.sql
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

### Part 2: Website Articles (`ingest_website.py`)
Crawls saiyashwanth.com/articles recursively.

```bash
python scripts/ingest_website.py
```

**What it does:**
- Crawls articles page + follows all article links
- Extracts title + content from each article
- Stores in `external_signals` table
- Generates 15-24 additional learnings per agent
- Max 50 articles (configurable)

**Result:** Agents learn from your full body of work, not just samples. All learnings marked `ceo_boosted=true`.

---

## Core Libraries ✅

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

### 🚧 Next Up
- **First Session** - CEO Daily Standup
- **Content Loop** - Brainstorm → Market Review → Draft → Post
- **External Scanning** - Twitter/Reddit/HN ingestion
- **Frontend** - Pixel art office dashboard

**Progress:** 50+ items complete in `plan.md` (out of 150+)

---

## Libraries Built (This Session)

**`lib/llm.py`** (60 lines) - OpenAI wrapper with retry logic

**`lib/learnings.py`** (100 lines) - Query, write, boost/dismiss learnings

**`lib/memories.py`** (70 lines) - Store/query experiential records

**`lib/sessions.py`** (110 lines) - Full session lifecycle management

**`scripts/ingest_website.py`** (240 lines) - Website crawler
- Recursive crawling within saiyashwanth.com domain
- Content extraction (title, body, word count)
- Batch analysis via GPT-4
- Stores articles + generates learnings
- Max 50 articles (configurable)

**`.gitignore`** - Protects sensitive files (.env, __pycache__, venv, etc.)

**`setup.sh`** - One-command setup script (creates .env, venv, installs deps)

**Total:** ~600 lines of clean, functional code.

**Test the libraries:**
```bash
python scripts/test_core_libs.py
# Tests learnings, memories, and sessions
# Verifies database connectivity
```

---

## Project Setup

**.gitignore** - Protects sensitive files:
- `.env` and environment files
- `__pycache__` and Python artifacts
- Virtual environments
- IDE files
- Logs and temporary files

**Important:** Never commit `.env` file! It contains your API keys.

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

See `plan.md` for full build order.

