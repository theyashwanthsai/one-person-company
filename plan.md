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

- [x] Create agent skill folders (strategist_lead, creator_hooks, analyst_lead)
- [x] Create soul.md for each agent with personalities
- [x] Set agent capabilities in soul.md frontmatter
- [x] Set initial pixel positions for office map
- [x] Create agent-specific prompts in agent folders
- [x] Write agent registration script (register_agents.py)
- [x] Write lib/agents.py with progressive disclosure loading

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

## Session Type: CEO Daily Standup

- [ ] Create `prompts/sessions/ceo_standup.md` template
- [ ] Write `workers/ceo_standup.py` runner
- [ ] Implement per-agent standup format (what_changed, confident, uncertain)
- [ ] Update agent states during standup
- [ ] Store conversation in session
- [ ] Extract key points as memories
- [ ] Test manually with 3 agents

## Session Type: Brainstorm

- [ ] Create `prompts/sessions/brainstorm.md` template
- [ ] Write `workers/brainstorm.py` runner
- [ ] Implement turn-by-turn conversation (8-12 turns)
- [ ] Strategist shares themes, Creator proposes angles
- [ ] Store ideas in session artifacts
- [ ] Extract learnings from conversation
- [ ] Create memories for participants

## Session Type: Market Review

- [ ] Create `prompts/sessions/market_review.md` template
- [ ] Write `workers/market_review.py` runner
- [ ] Fetch similar content from external_signals
- [ ] Calculate benchmark metrics
- [ ] Group decision: approve/kill/reshape
- [ ] Store decision reasoning as learning
- [ ] Update content_pipeline status

## Session Type: 1-on-1

- [ ] Create `prompts/sessions/1on1.md` template
- [ ] Write `workers/1on1.py` runner
- [ ] Implement agent-initiated 1-on-1 requests
- [ ] Store conversation
- [ ] Extract learnings and memories

## Session Type: Watercooler

- [ ] Create `prompts/sessions/watercooler.md` template
- [ ] Write `workers/watercooler.py` runner
- [ ] Random agent selection (2-3 agents)
- [ ] Casual conversation (3-5 turns)
- [ ] No action items allowed
- [ ] Extract weak signals as learnings

## Agent Tools: Function Calling

- [ ] Define `tools/scan_external_source.json` schema
- [ ] Implement scan_external_source (Twitter, Reddit, HN)
- [ ] Define `tools/query_learnings.json` schema
- [ ] Implement query_learnings tool
- [ ] Define `tools/request_1on1.json` schema
- [ ] Implement request_1on1 (creates session)
- [ ] Define `tools/email_ceo.json` schema
- [ ] Implement email_ceo (sends email)
- [ ] Define `tools/write_learning.json` schema
- [ ] Implement write_learning tool
- [ ] Wire tools into LLM function calling

## External Signal Ingestion: Twitter

- [ ] Write `workers/ingest_twitter.py`
- [ ] Connect to Twitter API (or use scraper)
- [ ] Fetch trending threads in your niche
- [ ] Store in external_signals table
- [ ] Mark as unanalyzed

## External Signal Ingestion: Reddit

- [ ] Write `workers/ingest_reddit.py`
- [ ] Use Reddit API (PRAW)
- [ ] Fetch top posts from relevant subreddits
- [ ] Store in external_signals table

## External Signal Ingestion: Hacker News

- [ ] Write `workers/ingest_hackernews.py`
- [ ] Use HN API (Algolia)
- [ ] Fetch top/best stories
- [ ] Store in external_signals table

## Scan Session: Strategist Scans Signals

- [ ] Create `prompts/sessions/strategist_scan.md` template
- [ ] Write `workers/strategist_scan.py`
- [ ] Fetch unanalyzed signals
- [ ] Strategist analyzes and extracts themes/narratives
- [ ] Store insights as learnings
- [ ] Mark signals as analyzed

## Content Creation Flow

- [ ] Write `lib/content.py` - create_content_idea function
- [ ] Transition idea to approved
- [ ] Transition approved to drafted
- [ ] Generate draft text via Creator agent
- [ ] Store draft in content_pipeline
- [ ] Calculate confidence score for draft

## Content Publishing

- [ ] Write `workers/publish_content.py`
- [ ] Check confidence threshold (>= 0.7 auto-publish)
- [ ] Post to Twitter API
- [ ] Update content_pipeline with posted status
- [ ] Store posted URL

## Content Performance Analysis

- [ ] Write `workers/analyze_performance.py`
- [ ] Fetch metrics for posted content (impressions, engagement)
- [ ] Store metrics in content_pipeline
- [ ] Compare against benchmarks
- [ ] Generate learnings (lessons/patterns)
- [ ] Analyst creates performance summary

## Learning Extraction from Sessions

- [ ] Write `lib/extract_learnings.py`
- [ ] Send session conversation to LLM
- [ ] Prompt: extract insights, patterns, strategies
- [ ] Parse structured output (type, statement, confidence)
- [ ] Dedupe via source_session_id
- [ ] Insert into learnings table

## Session Scheduling System

- [ ] Write `scheduler.py` cron manager
- [ ] Schedule CEO standup daily (morning)
- [ ] Schedule brainstorm sessions 2x per day
- [ ] Schedule market review after brainstorms
- [ ] Schedule watercooler 1x per day (random time)
- [ ] Schedule strategist scans 3x per day
- [ ] Schedule performance analysis daily (evening)
- [ ] Add jitter (±30 min randomness)

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

