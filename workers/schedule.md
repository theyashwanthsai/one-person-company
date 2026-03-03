# Daily Engine Schedule

Edit the list inside the code block. Keep it as valid Python list/dict syntax.

```python
[
    # ---- Inbox: Email Updates ----
    {
        "interval_minutes": 30, "type": "solo",
        "agent": "watari",
        "session_type": "email_check",
        "task": "Check email inbox using email_ops (action='check') and post any new updates to Discord #mails. If there are no new emails, keep it brief."
    },

    # ---- Morning: Signal Gathering ----
    {
        "time": "08:00", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Run a fresh scan of Reddit and Hacker News. First, use surf_reddit on ['AI_Agents', 'LocalLLaMA', 'artificial', 'ArtificialInteligence'] (sort='new', last 1h, ~10 posts per subreddit). Read those, then write a strategic summary in your own words into the knowledge base using write_obsidian_note(folder='thea'). Only after that, use surf_hn for the last 1h of HN stories (~30 posts) and, if necessary, append an HN section to the same note."
    },
    {
        "time": "08:30", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "analysis",
        "task": "Start analysis from the knowledge base, not the external_signals DB. Read all recent notes in knowledgebase/thea from the last 6 hours and create 1 content idea per post section. Use create_ideas_from_thea_notes(folder='thea', since_hours=6). Ensure the ideas are concrete and actionable (Hook/Problem/Answer), then verify they landed in content_pipeline with check_content_pipeline(status='idea')."
    },

    # ---- CEO Standup (each agent posts individually) ----
    {
        "time": "09:00", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "ceo_standup",
        "task": "Daily standup. Use your tools to gather real data before reporting. 1) query_learnings to find what you learned recently. 2) scan_external_source to see what signals you stored. 3) recall_memories for recent work. Then post YOUR standup to Discord via discord_ceo with channel='standup'. Be specific: name actual topics you scanned, patterns you found, signals you stored. No generic statements like 'I scanned sources' — say WHAT you found."
    },
    {
        "time": "09:02", "type": "solo",
        "agent": "creator_lead",
        "session_type": "ceo_standup",
        "task": "Daily standup. Use your tools to gather real data before reporting. 1) check_content_pipeline to see current drafts and ideas. 2) query_learnings for recent insights. 3) recall_memories for recent work. Then post YOUR standup to Discord via discord_ceo with channel='standup'. Be specific: name actual content pieces you drafted, ideas in the pipeline, what stage they're at. No generic statements like 'I'm working on content' — say WHICH pieces, WHAT topics, WHERE they are in the pipeline."
    },
    {
        "time": "09:04", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "ceo_standup",
        "task": "Daily standup. Use your tools to gather real data before reporting. 1) query_learnings for recent analysis findings. 2) check_content_pipeline for items you reviewed. 3) scan_external_source for signals you analyzed. Then post YOUR standup to Discord via discord_ceo with channel='standup'. Be specific: name actual metrics, benchmarks, content pieces you evaluated, patterns you found in the data. No generic statements like 'I analyzed performance' — say WHAT performed well, by HOW much, and WHAT you recommend."
    },

    # ---- Mid-Morning Work ----
    {
        "time": "09:30", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Second scan pass. Use surf_reddit and surf_hn again with the same subreddits but only a 1h window. Focus on contrarian takes and underexplored angles. Capture your synthesis in a new note under folder='thea' via write_obsidian_note, summarizing only what is genuinely interesting."
    },
    {
        "time": "10:00", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "analysis",
        "task": "Check the content pipeline. Review any new ideas created from Thea's notes. Pick the top 1-2 and add market-review style notes: what would you need to validate, what benchmark to compare against, and what would make this a 'good' post. Write findings as learnings."
    },

    # ---- Brainstorm ----
    {
        "time": "10:30", "type": "meeting",
        "agents": ["strategist_lead", "creator_lead"],
        "session_type": "brainstorm",
        "task": "Time to brainstorm content ideas. Strategist: share the strongest themes and patterns you've spotted today. Creator: propose specific content angles, hooks, and formats based on those themes. Build on each other's ideas. When you land on strong ideas, write them as learnings."
    },

    # ---- Late Morning: Creation ----
    {
        "time": "11:00", "type": "solo",
        "agent": "creator_lead",
        "session_type": "drafting",
        "task": "Morning hooks + drafting. You MUST call generate_hooks_from_pipeline(status='idea', limit=20, send_to_discord=True) to turn current content_pipeline ideas into short-form drafts (Hook → Problem → Answer) and send all hooks to Discord #content. Do not claim there is a technical issue with the pipeline unless a tool explicitly returns an Error message. If there are no ideas, say that clearly and suggest which Thea notes should be turned into ideas next."
    },
    {
        "time": "11:30", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Quick scan of Reddit and HN for anything time-sensitive or rapidly trending in the last 1h using surf_reddit and surf_hn. If you find something urgent, both log it into a thea note via write_obsidian_note and message the CEO on Discord with the concrete links and why they matter."
    },

    # ---- Lunch: Watercooler ----
    {
        "time": "12:00", "type": "meeting",
        "agents": "random_2",
        "session_type": "watercooler",
        "task": "Casual watercooler chat. No agenda. Share something surprising you noticed, an assumption you want to question, or a wild idea you've been thinking about. Keep it relaxed and curious. If anything interesting comes up, note it as a learning."
    },

    # ---- Afternoon: Deep Work ----
    {
        "time": "13:00", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Afternoon signal scan. Use surf_reddit + surf_hn again with a 1h window and compare what you see now with the morning scans. In a new thea note via write_obsidian_note, spell out shifts you notice (topics cooling off, new ones emerging) with examples."
    },
    {
        "time": "13:30", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "analysis",
        "task": "Deep analysis session. Use Thea's knowledgebase/thea notes + the content_pipeline ideas created from them. Synthesize 2-4 bigger patterns and propose which ideas to prioritize this week. Write a synthesis as learnings."
    },

    # ---- Market Review ----
    {
        "time": "14:00", "type": "meeting",
        "agents": ["analyst_lead", "strategist_lead", "creator_lead"],
        "session_type": "market_review",
        "task": "Market review meeting. Analyst: present your data on the top content idea in the pipeline — market saturation, engagement benchmarks, similar content performance. Strategist: evaluate strategic fit. Creator: assess execution feasibility. Together, decide: approve, reshape, or kill the idea. Document your decision reasoning as learnings."
    },

    # ---- Afternoon Brainstorm ----
    {
        "time": "15:00", "type": "meeting",
        "agents": ["strategist_lead", "creator_lead"],
        "session_type": "brainstorm",
        "task": "Afternoon brainstorm. Build on what came out of the market review. Generate new angles or refine existing ideas. If you discussed anything interesting at the watercooler, bring those threads in."
    },

    # ---- Late Afternoon Work ----
    {
        "time": "15:30", "type": "solo",
        "agent": "creator_lead",
        "session_type": "drafting",
        "task": "Continue drafting or refining content. Use today's brainstorm outputs and analyst feedback. If a draft is ready, note it in your learnings."
    },
    {
        "time": "16:00", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Late afternoon scan. Use surf_reddit + surf_hn (1h window) to catch anything that emerged recently, especially from international time zones. Summarize these in a thea note via write_obsidian_note, highlighting anything worth turning into content later."
    },

    # ---- Evening Watercooler ----
    {
        "time": "16:30", "type": "meeting",
        "agents": "random_2",
        "session_type": "watercooler",
        "task": "End-of-day watercooler. How did today go? Anything unresolved? Any interesting threads worth picking up tomorrow? Keep it casual."
    },

    # ---- End of Day ----
    {
        "time": "17:00", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "analysis",
        "task": "End-of-day performance review. Check if any posted content got engagement today. Compare against benchmarks. Document what worked and what didn't as learnings."
    },
    {
        "time": "17:30", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Final scan of the day. Quick 1h sweep on Reddit and HN using surf_reddit + surf_hn. Then write an end-of-day thea note via write_obsidian_note summarizing the single most important pattern or theme from today, with links/examples."
    },
]
```
