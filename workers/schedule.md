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
        "task": "Scan external sources (Twitter, Reddit, HN) for trending topics in AI, coding, developer tools, and personal branding. Look for emerging patterns, viral threads, and new narratives. Document any new patterns as learnings."
    },
    {
        "time": "08:30", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "analysis",
        "task": "Review recent external signals in the database. Look for engagement patterns and benchmark data. Calculate what content formats and topics are performing well. Document findings as learnings."
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
        "task": "Do another scan of external sources. Focus on anything you might have missed earlier. Look for contrarian takes and underexplored angles. Write learnings for anything interesting."
    },
    {
        "time": "10:00", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "analysis",
        "task": "Check the content pipeline. Review any ideas waiting for validation. Look at external signals related to those ideas. Assess market saturation and engagement potential. Write your analysis as learnings."
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
        "task": "Check the content pipeline for approved ideas. Pick the highest priority one and start drafting. Use your learnings about what performs well. Write your draft progress and any insights as learnings and memories."
    },
    {
        "time": "11:30", "type": "solo",
        "agent": "strategist_lead",
        "session_type": "scan",
        "task": "Quick scan of external sources. Look for anything time-sensitive or rapidly trending. If something urgent comes up, message the CEO on Discord."
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
        "task": "Afternoon signal scan. Focus on what's trending right now. Compare with what you saw this morning — any shifts?"
    },
    {
        "time": "13:30", "type": "solo",
        "agent": "analyst_lead",
        "session_type": "analysis",
        "task": "Deep analysis session. Look at the bigger picture — what patterns emerge across all recent signals? Any market shifts? Write a synthesis as learnings."
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
        "task": "Late afternoon scan. Catch anything that emerged during the day. Focus on evening/international trends."
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
        "task": "Final scan of the day. Quick sweep for anything you missed. Write a brief end-of-day learning summarizing the most important pattern or theme from today."
    },
]
```
