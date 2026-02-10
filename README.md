# One Person Company - AI Social Media Team

An autonomous AI team that manages your personal brand on social media. Built from first principles with sessions, learnings, and memory.

## What This Is

A team of AI agents that:
- Scans Twitter, Reddit, HN for trends
- Brainstorms content ideas
- Creates and posts content
- Analyzes performance
- Learns from outcomes
- Reports to you (the CEO)

## The Team

🎯 **Thea** (Strategy Lead) - Identifies themes and narratives  
✍️ **Kavi** (Content Creator) - Turns ideas into viral posts  
📊 **Dara** (Data Analyst) - Tracks performance and extracts patterns

## Tech Stack

- **Database**: Supabase (PostgreSQL)
- **Backend**: Python + FastAPI
- **LLM**: OpenAI API
- **Frontend**: Next.js + Pixel Art Office

## Quick Start

See `DOCS.md` for detailed setup and API reference.

### 1. Database Setup
```bash
# In Supabase SQL Editor: paste migrations/all_migrations.sql
```

### 2. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp env.example .env
# Add your Supabase and OpenAI credentials
```

### 4. Register Agents
```bash
python scripts/register_agents.py
# Registers: Thea, Kavi, Dara
```

### 5. Cold Start (Teach Your Agents)
```bash
# Part 1: Mini essays (curated samples)
python scripts/cold_start.py

# Part 2: Website articles (full body of work)
python scripts/ingest_website.py

# Result: 40-60 learnings across all agents
```

### 6. Run Your First Session
```bash
python workers/ceo_standup.py
# Your 3 agents will give you their daily standup
```

## Project Structure

```
one_person_company/
├── migrations/          # Database schema
├── seeds/              # Initial data
├── lib/                # Core libraries
│   ├── agents.py       # Agent management
│   ├── learnings.py    # Learning system
│   ├── memories.py     # Memory system
│   ├── sessions.py     # Session engine
│   └── llm.py          # OpenAI wrapper
├── workers/            # Background workers
│   ├── ceo_standup.py
│   ├── brainstorm.py
│   └── strategist_scan.py
├── prompts/            # LLM prompts (markdown)
├── api/                # FastAPI server
├── frontend/           # Next.js dashboard
└── scripts/            # Utility scripts
```

## Build Progress

See `plan.md` for the full 150+ step build plan.

Current status:
- [x] Database schema designed (8 tables)
- [x] Migrations created
- [x] Agent skill system (Thea, Kavi, Dara)
- [x] Cold start system (mini essays + website scraper)
- [x] Core libraries (llm, learnings, sessions, memories)
- [ ] Session engine (CEO standup, brainstorm, etc.)
- [ ] Content creation flow
- [ ] Frontend dashboard
- [ ] Deployment

## Key Concepts

### Sessions
Everything happens in sessions. A session = a structured interaction with a purpose.
- CEO Standup (you + team leads)
- Brainstorm (strategist + creator)
- Market Review (all 3 agents)
- 1-on-1 (any 2 agents)
- Watercooler (casual chat)

### Learnings
Distilled knowledge that compounds over time.
- "Weekend posts get 30% less engagement"
- "Technical depth outperforms hype"
- Confidence scores, decay over time, CEO can boost

### Memories
Experiential records, not just facts.
- "Had a heated debate with Analyst on Jan 15"
- Provides emotional context

### Company Trajectory
Daily/weekly/monthly summaries that compress history.

## Philosophy

Built from first principles:
- Session-centric design (everything is a session)
- Learning as currency (agents compound knowledge)
- CEO-in-the-loop (you have override authority)
- Visual observability (pixel art office shows everything)
- Extensible by design (easy to add new roles)

## License

MIT

