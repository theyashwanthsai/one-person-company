# Build Plan: One Person Company

## Database Setup

- [ ] Create Supabase project
- [x] Create `agents` table
- [x] Create `learnings` table
- [x] Create `memories` table
- [x] Create `sessions` table
- [x] Create `content_pipeline` table
- [x] Create `external_signals` table
- [x] Create `ceo_feedback` table
- [x] Create `company_trajectory` table
- [x] Add indexes for learnings (agent_id, confidence, tags)
- [x] Add indexes for sessions (type, status)
- [x] Add indexes for content_pipeline (status)
- [x] Add indexes for external_signals (source, analyzed)
- [x] Add indexes for company_trajectory (period_type, period_start)

## Seed Data

- [x] Create agent skill folders (strategist_lead, creator_lead, analyst_lead)
- [x] Create soul.md for each agent with personalities
- [x] Set agent capabilities in soul.md frontmatter
- [x] Set initial pixel positions for office map
- [x] Create agent-specific prompts in agent folders
- [x] Write agent registration script (register_agents.py)
- [x] Write lib/agents.py with progressive disclosure loading
- [x] Create HTML dashboard with pixel art map
- [x] Add agent sprites to dashboard
- [x] Style dashboard (dark theme, borders, layout)

## Cold Start: Ingest Existing Content

- [x] Create cold_start_dump.md with CEO's mini essays
- [x] Write cold_start.py to process mini essays
- [x] Analyze writing style via LLM
- [x] Generate seed learnings (24-30) from mini essays
- [x] Write ingest_website.py to scrape saiyashwanth.com/articles
- [x] Recursive crawling (follows article links)
- [x] Extract article content (title, body, word count)
- [x] Store articles in `external_signals` with source='your_blog'
- [x] Generate additional learnings (15-24) from articles
- [x] Insert all learnings with ceo_boosted=true
- [ ] Optional: Create bootstrap.py master script (runs both)

## Core Library: Learning System

- [x] Write `lib/learnings.py` - query_learnings function
- [x] Write learning filtering (tags, types, confidence)
- [x] Write write_learning function
- [x] Write CEO boost/dismiss learning functions
- [x] Write get_agent_learnings_summary function
- [ ] Write learning decay function (weekly decay)
- [ ] Write apply_decay cron function
- [ ] Write learning conflict detection

## Core Library: Memory System

- [x] Write `lib/memories.py` - store_memory function
- [x] Write query_memories function
- [x] Write link_memory_to_learning function
- [x] Write get_memory function
- [ ] Write memory summarization (compress long experiences)

## Core Library: Session Engine

- [x] Write `lib/sessions.py` - create_session function
- [x] Write get_session, update_session, complete_session
- [x] Write append_turn function (conversation management)
- [x] Write fail_session function
- [x] Write get_recent_sessions function
- [x] Write add_learning_to_session function
- [x] Write session state transitions (running → completed/failed)

## Core Library: Agent State Management

- [x] Write `lib/agents.py` - get_agent function
- [x] Write update_agent_state function
- [x] Write update_agent_location function
- [x] Write load_agent_full with progressive disclosure
- [x] Write load_agent_prompt function
- [x] Write load_agent_reference function
- [ ] Write get_agent_context (learnings + memories)

## Core Library: LLM Wrapper

- [x] Write `lib/llm.py` - OpenAI chat completion wrapper
- [x] Write chat_completion function (simple)
- [x] Write chat_completion_json function (JSON mode)
- [x] Write chat_with_history function (conversation)
- [x] Handle retries (3 attempts, exponential backoff)
- [x] Handle rate limits via retry logic
- [ ] Handle token counting (not yet needed)

## Session Type: CEO Daily Standup ✅

- [x] Write `workers/ceo_standup.py` runner (email-based)
- [x] Implement per-agent standup format (what_changed, confident, uncertain)
- [x] Update agent states during standup
- [x] Store conversation in session
- [x] Extract key points as learnings
- [x] Email integration (lib/email_client.py)
- [x] CEO feedback commands (boost/dampen/focus)
- [x] Database functions for learning adjustments
- [x] Documentation (CEO_STANDUP_SETUP.md)

## Session Type: Brainstorm ✅

- [x] Write `workers/brainstorm.py` runner
- [x] Implement turn-by-turn conversation (10 turns)
- [x] Strategist shares themes, Creator proposes angles
- [x] Store ideas in content_pipeline table
- [x] Extract learnings from conversation
- [x] Auto-topic selection based on learnings
- [x] Create memories for participants

## Session Type: Market Review ✅

- [x] Write `workers/market_review.py` runner
- [x] Fetch similar content from external_signals
- [x] Calculate benchmark metrics
- [x] Group decision: approve/kill/reshape
- [x] Store decision reasoning as learning
- [x] Update content_pipeline status
- [x] Three-way evaluation (Analyst + Strategist + Creator)

## Session Type: 1-on-1

- [ ] Create `prompts/sessions/1on1.md` template
- [ ] Write `workers/1on1.py` runner
- [ ] Implement agent-initiated 1-on-1 requests
- [ ] Store conversation
- [ ] Extract learnings and memories

## Session Type: Watercooler ✅

- [x] Write `workers/watercooler.py` runner
- [x] Random agent selection (2-3 agents)
- [x] Casual conversation (3-5 turns)
- [x] Random casual topics
- [x] No action items allowed
- [x] Extract weak signals as learnings
- [x] High temperature for creativity

## Agent Tools: Function Calling ✅

- [x] Build `lib/tool_registry.py` — discovers tools, validates schemas, executes
- [x] Build `lib/tool_runner.py` — LLM ↔ tool execution loop (run_agent_with_tools)
- [x] Tool convention: each tool = Python file with SCHEMA + execute()
- [x] Shared tools in `tools/` (all agents), agent-specific in `agents/<id>/tools/`
- [x] `tools/query_learnings.py` — search team knowledge
- [x] `tools/write_learning.py` — document patterns/insights
- [x] `tools/store_memory.py` — record experiential memories
- [x] `tools/recall_memories.py` — search past experiences
- [x] `tools/request_1on1.py` — request conversation with another agent
- [x] `tools/email_ceo.py` — escalate to CEO via email
- [x] `tools/scan_external_source.py` — search external signals
- [x] `tools/check_content_pipeline.py` — view content pipeline status
- [x] `run_agent_step()` — high-level: load soul + tools + run (one function call)
- [x] Test script: `tests/test_tools.py`

## Engine Architecture ✅

- [x] Single file: `workers/engine.py` runs the entire company
- [x] Flat SCHEDULE list — add/remove entries to change the day
- [x] Solo tasks: `run_agent_step()` → agent uses tools autonomously
- [x] Meetings: turn-taking, each turn is `run_agent_step()` with history
- [x] Natural conclusion detection (agents say [DONE] or wrap-up phrases)
- [x] CLI: `--run scan`, `--run-all`, `--list` for manual control
- [x] Deleted all hardcoded worker files (brainstorm, watercooler, etc.)

## Daily Schedule (in engine.py)

- [x] 08:00 Thea scans signals (solo)
- [x] 08:30 Dara analyzes signals (solo)
- [x] 09:00 CEO standup (meeting)
- [x] 09:30 Thea scans signals (solo)
- [x] 10:00 Dara reviews pipeline (solo)
- [x] 10:30 Brainstorm: Thea + Kavi (meeting)
- [x] 11:00 Kavi drafts content (solo)
- [x] 11:30 Thea scans signals (solo)
- [x] 12:00 Watercooler: random 2 (meeting)
- [x] 13:00 Thea scans signals (solo)
- [x] 13:30 Dara deep analysis (solo)
- [x] 14:00 Market review: all 3 (meeting)
- [x] 15:00 Brainstorm: Thea + Kavi (meeting)
- [x] 15:30 Kavi drafts content (solo)
- [x] 16:00 Thea scans signals (solo)
- [x] 16:30 Watercooler: random 2 (meeting)
- [x] 17:00 Dara performance review (solo)
- [x] 17:30 Thea final scan (solo)

## Signal Ingestion, Scanning, Content, Performance

All handled by agents via tools + engine schedule:
- [x] Signal ingestion → Thea uses `scan_external_source` tool (6x/day)
- [x] Signal analysis → Dara uses `scan_external_source` + `write_learning` (3x/day)
- [x] Content ideation → Brainstorm meetings + `write_learning` (2x/day)
- [x] Content validation → Market review meetings (1x/day)
- [x] Content drafting → Kavi uses `check_content_pipeline` + tools (2x/day)
- [x] Performance analysis → Dara uses tools end-of-day (1x/day)

## External Integration Tools (COMPLETED)

- [x] `tools/store_external_signal.py` — persist surf_* payloads to external_signals
- [x] `tools/surf_reddit.py` — fetch Reddit posts via public JSON endpoints
- [x] `tools/surf_hn.py` — fetch HN stories via Algolia time-window API
- [x] `tools/publish_content.py` — post tweets (single or threads)
- [x] `tools/fetch_metrics.py` — pull engagement metrics and analyze performance
- [x] Store metrics in content_pipeline — automatically done by fetch_metrics
- [x] Compare against benchmarks — engagement score analysis built-in
- [x] Generate learnings — agents write learnings using write_learning tool
- [x] Analyst creates performance summary — scheduled in engine.py

## Learning Extraction from Sessions

- [x] ~~Write `lib/extract_learnings.py`~~ — Not needed: agents write learnings live during sessions via `write_learning` tool
- [x] ~~Send session conversation to LLM~~ — Agents extract insights in real-time as they converse
- [x] ~~Prompt: extract insights, patterns, strategies~~ — Built into agent prompts in engine.py
- [x] ~~Parse structured output~~ — Tools handle structured input/output
- [x] ~~Dedupe via source_session_id~~ — Learnings track source_agent
- [x] ~~Insert into learnings table~~ — `tools/write_learning.py` handles this

## Session Scheduling System

- [x] ~~Write `scheduler.py` cron manager~~ — Replaced by `workers/engine.py` SCHEDULE
- [x] Schedule CEO standup daily (morning) — 09:00
- [x] Schedule brainstorm sessions 2x per day — 10:30, 15:00
- [x] Schedule market review after brainstorms — 14:00
- [x] Schedule watercooler 1x per day (random time) — 12:00, 16:30 (2x with random agents)
- [x] Schedule strategist scans 3x per day — 08:00, 09:30, 11:30, 13:00, 16:00, 17:30
- [x] Schedule performance analysis daily (evening) — 17:00
- [ ] Add jitter (±30 min randomness)




- [x] Remove solo_work in session table of the db. These sessions should lead to learnings/memories only i feel
- [x] Twitter, Hackernews, Reddit tools must be made better.
- [ ] Find a cheap tool for ai agents to surf internet like crazy.
- [ ] a way to get our analyst to learn about past posts
- [ ] analyst should be more of a team lead since it has less responsiblity
- [ ] Sort out emails.
- [ ] Add apis, but we shouldnt expose them. Should be strictly for testing
- [ ] 


## FastAPI: Basic Server

- [ ] Create `api/main.py` FastAPI app
- [ ] Add CORS middleware
- [ ] Connect to Supabase client

## FastAPI: Agents Endpoints

- [ ] `GET /agents` - list all agents
- [ ] `GET /agents/{agent_id}` - get agent details
- [ ] `PATCH /agents/{agent_id}/state` - update agent state (for testing)

## FastAPI: Sessions Endpoints

- [ ] `GET /sessions` - list sessions (filter by type, status)
- [ ] `GET /sessions/{session_id}` - get session details + conversation
- [ ] `POST /sessions` - manually trigger session (for testing)

## FastAPI: Learnings Endpoints

- [ ] `GET /learnings` - list learnings (filter by agent, type, tags)
- [ ] `POST /learnings/{learning_id}/boost` - CEO boost learning
- [ ] `POST /learnings/{learning_id}/dismiss` - CEO dismiss learning

## FastAPI: Content Pipeline Endpoints

- [ ] `GET /content` - list content in pipeline
- [ ] `GET /content/{content_id}` - get content details
- [ ] `POST /content/{content_id}/approve` - CEO approve
- [ ] `POST /content/{content_id}/veto` - CEO veto

## FastAPI: CEO Feedback Endpoints

- [ ] `POST /ceo/feedback` - submit CEO feedback
- [ ] `GET /ceo/pending-reviews` - get items needing CEO review

## FastAPI: Webhooks for Real-time

- [ ] `POST /webhooks/session-started` - notify frontend
- [ ] `POST /webhooks/session-completed` - notify frontend
- [ ] `POST /webhooks/content-posted` - notify frontend

## Frontend: Setup Next.js

- [ ] Create Next.js project
- [ ] Install Supabase client
- [ ] Install Tailwind CSS
- [ ] Configure env variables (Supabase URL, keys)

## Frontend: Supabase Realtime Subscriptions

- [ ] Subscribe to `agents` table changes
- [ ] Subscribe to `sessions` table changes
- [ ] Subscribe to `content_pipeline` table changes
- [ ] Update UI on realtime events

## Frontend: Office Map Component

- [ ] Create `components/OfficeMap.tsx`
- [ ] Load pixel art office background
- [ ] Render agent sprites at pixel_position
- [ ] Update sprite based on agent.state
- [ ] Add click handler to open agent panel

## Frontend: Agent Sprite Component

- [ ] Create `components/AgentSprite.tsx`
- [ ] Load sprite sheet for each agent
- [ ] Animate based on state (idle, walking, working, meeting)
- [ ] Show state label on hover

## Frontend: Agent Details Panel

- [ ] Create `components/AgentPanel.tsx`
- [ ] Show agent name, role, current state
- [ ] Show recent learnings (last 5)
- [ ] Show recent memories (last 5)
- [ ] Add "Request 1-on-1" button

## Frontend: Session Timeline

- [ ] Create `components/SessionTimeline.tsx`
- [ ] Show upcoming sessions
- [ ] Show running sessions with progress
- [ ] Show completed sessions (clickable)

## Frontend: Session Replay

- [ ] Create `components/SessionReplay.tsx`
- [ ] Display conversation turn by turn
- [ ] Add play/pause controls
- [ ] Show extracted learnings at end

## Frontend: Content Pipeline Kanban

- [ ] Create `components/ContentPipeline.tsx`
- [ ] Columns: Ideas, Approved, Drafted, Posted, Analyzed
- [ ] Drag-and-drop (optional)
- [ ] Show confidence score on each card

## Frontend: CEO Console

- [ ] Create `components/CEOConsole.tsx`
- [ ] "Join Next Standup" button (opens modal)
- [ ] Pending reviews list (low-confidence content)
- [ ] Boost/dismiss learnings interface
- [ ] Issue directive text input

## Frontend: CEO Standup Modal

- [ ] Create `components/CEOStandupModal.tsx`
- [ ] Show each agent's standup response
- [ ] Input for CEO feedback per agent
- [ ] Submit feedback to API

## Frontend: Dashboard Layout

- [ ] Create `app/page.tsx` main dashboard
- [ ] Left: CEO Console
- [ ] Center: Office Map
- [ ] Right: Session Timeline + Content Pipeline
- [ ] Bottom: Learnings feed (recent)

## Frontend: Styling

- [ ] Style office map container
- [ ] Style agent sprites
- [ ] Style session timeline
- [ ] Style CEO console
- [ ] Add animations (agent movement, state transitions)

## Testing: Manual Session Tests

- [ ] Run CEO standup manually, verify conversation quality
- [ ] Run brainstorm manually, check idea generation
- [ ] Run market review manually, check decision logic
- [ ] Run watercooler manually, check casual tone

## Testing: Learning System Tests

- [ ] Create learning manually
- [ ] Query learnings by tags
- [ ] Test decay function (manually adjust dates)
- [ ] Test CEO boost/dismiss

## Testing: Content Flow Tests

- [ ] Create idea manually
- [ ] Run market review on it
- [ ] Generate draft
- [ ] Check confidence score
- [ ] Publish (test mode, don't actually post)

## Testing: Frontend Integration Tests

- [ ] Verify realtime updates work
- [ ] Verify agent state changes reflect immediately
- [ ] Verify session appears in timeline
- [ ] Verify CEO console interactions work

## Deployment: VPS Setup

- [ ] Provision VPS (Hetzner or similar)
- [ ] Install Python 3.11+
- [ ] Install pip, virtualenv
- [ ] Clone repo
- [ ] Install dependencies (`requirements.txt`)
- [ ] Set environment variables (.env file)

## Deployment: Run Workers

- [ ] Create systemd service for FastAPI
- [ ] Create systemd service for scheduler
- [ ] Create systemd service for each worker (optional: use single scheduler)
- [ ] Test services start on boot
- [ ] Check logs

## Deployment: Cron Jobs

- [ ] Add cron for learning decay (daily)
- [ ] Add cron for strategist scans (3x daily)
- [ ] Add cron for performance analysis (daily evening)
- [ ] Verify cron execution in logs

## Deployment: Frontend

- [ ] Deploy Next.js to Vercel
- [ ] Set environment variables in Vercel
- [ ] Connect to Supabase
- [ ] Test production build

## Documentation: Setup Instructions

- [ ] Write README.md
- [ ] Document environment variables
- [ ] Document database schema
- [ ] Document API endpoints
- [ ] Document session types

## Monitoring & Observability

- [ ] Add basic logging (Python logging module)
- [ ] Log session starts/completions
- [ ] Log LLM API calls (tokens used)
- [ ] Log errors with traceback
- [ ] Optional: Add Sentry for error tracking

## Iteration: Review After 1 Week

- [ ] Review which sessions are most valuable
- [ ] Check learning quality (are they useful?)
- [ ] Check content quality (would you post it?)
- [ ] Tune confidence thresholds
- [ ] Tune agent personalities
- [ ] Add more seed learnings if needed

## Future Enhancements (Not Now)

- [ ] Add image creator agent
- [ ] Add chief of staff agent
- [ ] Add Instagram platform
- [ ] Add LinkedIn platform
- [ ] Add relationship tracking between agents
- [ ] Add voice evolution based on memories
- [ ] Add more session types (war room, retro)
- [ ] Add agent initiative system
- [ ] Implement relevance-based learning queries (PostgreSQL function)
- [ ] Implement tiered context loading with token budgets
- [ ] Implement memory consolidation (monthly compression)
- [ ] Implement automatic archival system for old data
- [ ] Add token counting and context budget management
