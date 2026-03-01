---
title: "We gave terabytes of CI logs to an LLM | Hacker News"
type: source_web
created: 2026-02-28T03:07:01+00:00
source_url: https://news.ycombinator.com/item?id=47181801
tags: [web, knowledge]
---

# We gave terabytes of CI logs to an LLM | Hacker News

## Source
- URL: https://news.ycombinator.com/item?id=47181801
- Captured By: watari

## Extracted Content

Lots of logs contain non-interesting information so it easily pollutes the context. Instead, my approach has a TF-IDF classifier + a BERT model on GPU for classifying log lines further to reduce the number of logs that should be then fed to a LLM model. The total size of the models is 50MB and the classifier is written in Rust so it allows achieve >1M lines/sec for classifying. And it finds interesting cases that can be missed by simple grepping I trained it on ~90GB of logs and provide scripts to retrain the models ( https://github.com/ascii766164696D/log-mcp/tree/main/scripts ) It's meant to be used with Claude Code CLI so it could use these tools instead of trying to read the log files

I trained it on ~90GB of logs and provide scripts to retrain the models ( https://github.com/ascii766164696D/log-mcp/tree/main/scripts ) It's meant to be used with Claude Code CLI so it could use these tools instead of trying to read the log files

It's meant to be used with Claude Code CLI so it could use these tools instead of trying to read the log files

reply

This is an interesting approach. I definitely agree with the problem statement: if the LLM has to filter by error/fatal because of context window constraints, it will miss crucial information. We took a different approach: we have a main agent (opus 4.6) dispatching "log research" jobs to sub agents (haiku 4.5 which is fast/cheap). The sub agent reads a whole bunch of logs and returns only the relevant parts to the parent agent. This is exactly how coding agents (e.g. Claude Code) do it as well. Except instead of having sub agents use grep/read/tail, they use plain SQL.

We took a different approach: we have a main agent (opus 4.6) dispatching "log research" jobs to sub agents (haiku 4.5 which is fast/cheap). The sub agent reads a whole bunch of logs and returns only the relevant parts to the parent agent. This is exactly how coding agents (e.g. Claude Code) do it as well. Except instead of having sub agents use grep/read/tail, they use plain SQL.

This is exactly how coding agents (e.g. Claude Code) do it as well. Except instead of having sub agents use grep/read/tail, they use plain SQL.

reply

And I just wanted to try MCP tooling tbh hehe Took me 2 days to create this to be honest

reply

- Opus agent wakes up when we detect an incident (e.g. CI broke on main) - It looks at the big picture (e.g. which job broke) and makes a plan to investigate - It dispatches narrowly focused tasks to Haiku sub agents (e.g. "extract the failing log patterns from commit XXX on job YYY ...") - Sub agents use the equivalent of "tail", "grep", etc (using SQL) on a very narrow sub-set of logs (as directed by Opus) and return only relevant data (so they can interpret INFO logs as actually being the problem) - Parent Opus agent correlates between sub agents. Can decide to spawn more sub agents to continue the investigation It's no different than what I would do as a human, really. If there are terabytes of logs, I'm not going to read all of them: I'll make a plan, open a bunch of tabs and surface interesting bits.

- It looks at the big picture (e.g. which job broke) and makes a plan to investigate - It dispatches narrowly focused tasks to Haiku sub agents (e.g. "extract the failing log patterns from commit XXX on job YYY ...") - Sub agents use the equivalent of "tail", "grep", etc (using SQL) on a very narrow sub-set of logs (as directed by Opus) and return only relevant data (so they can interpret INFO logs as actually being the problem) - Parent Opus agent correlates between sub agents. Can decide to spawn more sub agents to continue the investigation It's no different than what I would do as a human, really. If there are terabytes of logs, I'm not going to read all of them: I'll make a plan, open a bunch of tabs and surface interesting bits.

- It dispatches narrowly focused tasks to Haiku sub agents (e.g. "extract the failing log patterns from commit XXX on job YYY ...") - Sub agents use the equivalent of "tail", "grep", etc (using SQL) on a very narrow sub-set of logs (as directed by Opus) and return only relevant data (so they can interpret INFO logs as actually being the problem) - Parent Opus agent correlates between sub agents. Can decide to spawn more sub agents to continue the investigation It's no different than what I would do as a human, really. If there are terabytes of logs, I'm not going to read all of them: I'll make a plan, open a bunch of tabs and surface interesting bits.

- Sub agents use the equivalent of "tail", "grep", etc (using SQL) on a very narrow sub-set of logs (as directed by Opus) and return only relevant data (so they can interpret INFO logs as actually being the problem) - Parent Opus agent correlates between sub agents. Can decide to spawn more sub agents to continue the investigation It's no different than what I would do as a human, really. If there are terabytes of logs, I'm not going to read all of them: I'll make a plan, open a bunch of tabs and surface interesting bits.

- Parent Opus agent correlates between sub agents. Can decide to spawn more sub agents to continue the investigation It's no different than what I would do as a human, really. If there are terabytes of logs, I'm not going to read all of them: I'll make a plan, open a bunch of tabs and surface interesting bits.

It's no different than what I would do as a human, really. If there are terabytes of logs, I'm not going to read all of them: I'll make a plan, open a bunch of tabs and surface interesting bits.

reply

This isn't anything new. It's not particularly technical or novel in any way, but it seems to work pretty well for identifying anomalies and comparing series over time horizons. It's even less token efficient on small windows than piping in a bunch of json, but it seems to be more effective from an analysis point of view. The strange thing about it is that it involves fairly deterministic analysis before we even send the data to the LLM, so one might ask, what's the point if you're already doing analysis? The answer is that LLMs can actually find interesting patterns across a lot of well presented data, and they can pick up on patterns in a way that feels like they are cross-referencing many different time series and correlate signals in interesting ways. That's where the general purpose LLMs are helpful in my experience. Breaking out analysis into sub-agents is a logical next step, we just haven't gotten there yet. And yeah the goal is to approximate those of us engineers who are good at RCAs in the moment, who have instincts about the system and can juggle a bunch of tabs and cross reference the signals in them.

The strange thing about it is that it involves fairly deterministic analysis before we even send the data to the LLM, so one might ask, what's the point if you're already doing analysis? The answer is that LLMs can actually find interesting patterns across a lot of well presented data, and they can pick up on patterns in a way that feels like they are cross-referencing many different time series and correlate signals in interesting ways. That's where the general purpose LLMs are helpful in my experience. Breaking out analysis into sub-agents is a logical next step, we just haven't gotten there yet. And yeah the goal is to approximate those of us engineers who are good at RCAs in the moment, who have instincts about the system and can juggle a bunch of tabs and cross reference the signals in them.

Breaking out analysis into sub-agents is a logical next step, we just haven't gotten there yet. And yeah the goal is to approximate those of us engineers who are good at RCAs in the moment, who have instincts about the system and can juggle a bunch of tabs and cross reference the signals in them.

And yeah the goal is to approximate those of us engineers who are good at RCAs in the moment, who have instincts about the system and can juggle a bunch of tabs and cross reference the signals in them.

reply

reply

Have an array of scripts to run against each log (just rust code probably for speed) and have them flag for performance, errors, intrusions, etc...

reply

reply

In my tool I was going more of a premise that it's frequently difficult to even say what you're looking for so I wanted to have some step after reading logs to say what should be actually analyzed further which naturally requires to have some model

reply

reply

But, my guess, I could see an algorithm like that being very fast. It's basically just doing a form of compression, so I'm thinking ballpark, like similar amount to just zipping the log Can't be anything CLOSE to the compute cost of running any part of the file through an LLM haha

Can't be anything CLOSE to the compute cost of running any part of the file through an LLM haha

reply

https://github.com/y-scope/clp https://www.uber.com/blog/reducing-logging-cost-by-two-order...

https://www.uber.com/blog/reducing-logging-cost-by-two-order...

reply

Since the classifier would need to have access to the whole log message I was looking into how search is organized for the CLP compression and see that: > First, recall that CLP-compressed logs are searchable–a user query will first be directed to dictionary searches, and only matching log messages will be decompressed. so then yeah it can be combined with a classifier as they get decompressed to get a filtered view at only log lines that should be interesting. The toughest part is still figuring out what does "interesting" actually mean in this context and without domain knowledge of the logs it would be difficult to capture everything. But I think it's still better than going through all the logs post searching.

> First, recall that CLP-compressed logs are searchable–a user query will first be directed to dictionary searches, and only matching log messages will be decompressed. so then yeah it can be combined with a classifier as they get decompressed to get a filtered view at only log lines that should be interesting. The toughest part is still figuring out what does "interesting" actually mean in this context and without domain knowledge of the logs it would be difficult to capture everything. But I think it's still better than going through all the logs post searching.

so then yeah it can be combined with a classifier as they get decompressed to get a filtered view at only log lines that should be interesting. The toughest part is still figuring out what does "interesting" actually mean in this context and without domain knowledge of the logs it would be difficult to capture everything. But I think it's still better than going through all the logs post searching.

The toughest part is still figuring out what does "interesting" actually mean in this context and without domain knowledge of the logs it would be difficult to capture everything. But I think it's still better than going through all the logs post searching.

reply

Another thing SQL has in it's favor is the ability with tools like trino or datafusion to basically turn "everything" into a table. EDIT: thinking on it some more, though, at what point do you just know off the top of your head the small handful of SQL queries you regularly use and just skip the expensive LLM step altogether? Like... that's the thing that underwhelms me about all the "natural language query" excitement. We already have a very good, natural language for queries: SQL.

EDIT: thinking on it some more, though, at what point do you just know off the top of your head the small handful of SQL queries you regularly use and just skip the expensive LLM step altogether? Like... that's the thing that underwhelms me about all the "natural language query" excitement. We already have a very good, natural language for queries: SQL.

reply

Give those queries to the LLM and enjoy your sleep while the agent works.

reply

reply

reply

Yes, it works really well. 1) The latest models are radically better at this. We noticed a massive improvement in quality starting with Sonnet 4.5 2) The context issue is real. We solve this by using sub agents that read through logs and return only relevant bits to the parent agent’s context

1) The latest models are radically better at this. We noticed a massive improvement in quality starting with Sonnet 4.5 2) The context issue is real. We solve this by using sub agents that read through logs and return only relevant bits to the parent agent’s context

2) The context issue is real. We solve this by using sub agents that read through logs and return only relevant bits to the parent agent’s context

reply

reply

reply

reply

Taking good note of your comment :)

reply

reply

So yes it works, we have customers in production.

reply

This post is a case study that shows one way to do this for a specific task. We found an RCA to a long-standing problem with our dev boxes this week using Ai. I fed Gemini Deep Research a few logs and our tech stack, it came back with an explanation of the underlying interactions, debugging commands, and the most likely fix. It was spot on, GDR is one of the best debugging tools for problems where you don't have full understanding. If you are curious, and perhaps a PSA, the issue was that Docker and Tailscale were competing on IP table updates, and in rare circumstances (one dev, once every few weeks), Docker DNS would get borked. The fix is to ignore Docker managed interfaces in NetworkManager so Tailscale stops trying to do things with them.

If you are curious, and perhaps a PSA, the issue was that Docker and Tailscale were competing on IP table updates, and in rare circumstances (one dev, once every few weeks), Docker DNS would get borked. The fix is to ignore Docker managed interfaces in NetworkManager so Tailscale stops trying to do things with them.

reply

This. We had much better success by letting the agent pull context rather trying to push what we thought was relevant. Turns out it's exactly like a human: if you push the wrong context, it'll influence them to follow the wrong pattern.

Turns out it's exactly like a human: if you push the wrong context, it'll influence them to follow the wrong pattern.

reply

- I force the AGENTS.md into the system prompt if the agent reads a directory, or file within, that contains one such file. This is anecdotally very good and saves on function calls and context growth in multiple ways. Sort them. I'm now doing this with planning and long-term task tracking markdown files. - Everything else is pull, ideally be search, yet to substantially leverage subagents for context gathering. Savings elsewhere have pushed the need out. btw, hi Al, I see you are working on a new company since our last collaboration, want to catch up sometime and talk shop?

- Everything else is pull, ideally be search, yet to substantially leverage subagents for context gathering. Savings elsewhere have pushed the need out. btw, hi Al, I see you are working on a new company since our last collaboration, want to catch up sometime and talk shop?

btw, hi Al, I see you are working on a new company since our last collaboration, want to catch up sometime and talk shop?

reply

reply

reply

reply

I agree with your statement and explained in a few other comments how we're doing this. tldr: - Something happens that needs investigating - Main (Opus) agent makes focused plan and spawns sub agents (Haiku) - They use ClickHouse queries to grab only relevant pieces of logs and return summaries/patterns This is what you would do manually: you're not going to read through 10 TB of logs when something happens; you make a plan, open a few tabs and start doing narrow, focused searches.

tldr: - Something happens that needs investigating - Main (Opus) agent makes focused plan and spawns sub agents (Haiku) - They use ClickHouse queries to grab only relevant pieces of logs and return summaries/patterns This is what you would do manually: you're not going to read through 10 TB of logs when something happens; you make a plan, open a few tabs and start doing narrow, focused searches.

- Something happens that needs investigating - Main (Opus) agent makes focused plan and spawns sub agents (Haiku) - They use ClickHouse queries to grab only relevant pieces of logs and return summaries/patterns This is what you would do manually: you're not going to read through 10 TB of logs when something happens; you make a plan, open a few tabs and start doing narrow, focused searches.

- Main (Opus) agent makes focused plan and spawns sub agents (Haiku) - They use ClickHouse queries to grab only relevant pieces of logs and return summaries/patterns This is what you would do manually: you're not going to read through 10 TB of logs when something happens; you make a plan, open a few tabs and start doing narrow, focused searches.

- They use ClickHouse queries to grab only relevant pieces of logs and return summaries/patterns This is what you would do manually: you're not going to read through 10 TB of logs when something happens; you make a plan, open a few tabs and start doing narrow, focused searches.

This is what you would do manually: you're not going to read through 10 TB of logs when something happens; you make a plan, open a few tabs and start doing narrow, focused searches.

reply

In this piece though--and maybe I need to read it again--I was under the impression that the LLM's "interface" to the logs data is queries against clickhouse. So long as the queries return sensibly limited results, and it doesn't go wild with the queries, that could address both concerns?

reply

reply

I'm guessing that intention was to say "around 10 lines", though it kind of stretches the definition if we're being picky.

reply

reply

reply

O(some constant) -- "nearby" that constant (maybe "order of magnitude" or whatever is contextually convenient) O(some parameter) -- denotes the asymptotic behavior of some parametrized process O(some variable representing a small number) -- denotes the negligible part of something that you're deciding you don't have to care about--error terms with exponent larger than 2 for example

O(some parameter) -- denotes the asymptotic behavior of some parametrized process O(some variable representing a small number) -- denotes the negligible part of something that you're deciding you don't have to care about--error terms with exponent larger than 2 for example

O(some variable representing a small number) -- denotes the negligible part of something that you're deciding you don't have to care about--error terms with exponent larger than 2 for example

reply

reply

reply

reply

reply

Basically a surefire way to train LLM to parse logs and detect real issues almost entirely depends on the readability and precision of logging. And if logging is good enough then humans can do debug faster and more reliable too :) . Unfortunately people reading logs and people coding them are almost not intersecting in practice and so the issue remains.

reply

Meanwhile stats have fewer expectations, and moving signal out of the logs into stats is a much much smaller battle to win. It can’t tell you everything, but what it can tell you is easier to make unambiguous. Over time I got people to stop pulling up Splunk as an automatic reflex and start pulling up Grafana instead for triage.

Over time I got people to stop pulling up Splunk as an automatic reflex and start pulling up Grafana instead for triage.

reply

reply

reply

reply

reply

reply

reply

reply

reply

reply

We're writing another post about that specifically, we'll publish it sometimes next week

reply

reply

I don't think implementing filtering on log ingestion is the right approach, because you don't know what is noise at this stage. We spent more time on thinking about the schema and indexes to make sure complex queries perform at scale.

reply

reply

I would like to see this approach compared to a more minimal approach with say, VictoriaLogs where the LLM is taught to use LogsQL, but overall it's a more "out of the box" architecture.

reply

IIUC this is addressed with the ClickHouse JSON type which can promote individual fields in unstructured data into its own column: https://clickhouse.com/blog/a-new-powerful-json-data-type-fo... Parquet is getting a VARIANT data type which can do the same thing (called "shredding") but in a standards-based way: https://parquet.apache.org/blog/2026/02/27/variant-type-in-a...

Parquet is getting a VARIANT data type which can do the same thing (called "shredding") but in a standards-based way: https://parquet.apache.org/blog/2026/02/27/variant-type-in-a...

reply

Large scale data like metrics, logs, traces are optimised for storage and access patterns and OLAP/SQL systems may not be the most optimal way to store or retrieve it. This is one of the reasons I’ve been working on a Text2SQL / Intent2SQL engine for Observability data to let an agent explore schema, semantics, syntax of any metrics, logs data. It is open sourced as Codd Text2SQL engine - https://github.com/sathish316/codd_query_engine/ It is far from done and currently works for Prometheus,Loki,Splunk for few scenarios and is open to OSS contributions. You can find it in action used by Claude Code to debug using Metrics and Logs queries: Metric analyzer and Log analyzer skills for Claude code - https://github.com/sathish316/precogs_sre_oncall_skills/tree...

It is far from done and currently works for Prometheus,Loki,Splunk for few scenarios and is open to OSS contributions. You can find it in action used by Claude Code to debug using Metrics and Logs queries: Metric analyzer and Log analyzer skills for Claude code - https://github.com/sathish316/precogs_sre_oncall_skills/tree...

Metric analyzer and Log analyzer skills for Claude code - https://github.com/sathish316/precogs_sre_oncall_skills/tree...

reply

I took this a few steps further beyond the web UI's AI assistant. There's an MCP server[2] so any AI assistant (Claude Desktop, Cursor, etc.) can discover your log sources, introspect schemas, and query directly. And a Rust CLI[3] with syntax highlighting and `--output jsonl` for piping — which means you can write a skill[4] that teaches the agent to triage incidents by running `logchef query` and `logchef sql` in a structured investigation workflow (count → group → sample → pivot on trace_id). The interesting bit is this ends up very similar to what OP describes — an agent that iteratively queries logs to narrow down root cause — except it's composable pieces you self-host rather than an integrated product. [1] https://github.com/mr-karan/logchef [2] https://github.com/mr-karan/logchef-mcp [3] https://logchef.app/integration/cli/ [4] https://github.com/mr-karan/logchef/tree/main/.agents/skills...

The interesting bit is this ends up very similar to what OP describes — an agent that iteratively queries logs to narrow down root cause — except it's composable pieces you self-host rather than an integrated product. [1] https://github.com/mr-karan/logchef [2] https://github.com/mr-karan/logchef-mcp [3] https://logchef.app/integration/cli/ [4] https://github.com/mr-karan/logchef/tree/main/.agents/skills...

[1] https://github.com/mr-karan/logchef [2] https://github.com/mr-karan/logchef-mcp [3] https://logchef.app/integration/cli/ [4] https://github.com/mr-karan/logchef/tree/main/.agents/skills...

[2] https://github.com/mr-karan/logchef-mcp [3] https://logchef.app/integration/cli/ [4] https://github.com/mr-karan/logchef/tree/main/.agents/skills...

[3] https://logchef.app/integration/cli/ [4] https://github.com/mr-karan/logchef/tree/main/.agents/skills...

[4] https://github.com/mr-karan/logchef/tree/main/.agents/skills...

reply

Any qualifiers here from your experience or documentation?

reply

Same applies when picking a programming language nowadays.

reply

I believe this method works well because it turns a long context problem (hard for LLMs) into a coding and reasoning problem (much better!). You’re leveraging the last 18 months of coding RL by changing you scaffold.

reply

reply

reply

reply

reply

We wrote about how this works for PostHog: https://www.mendral.com/blog/ci-at-scale

reply

reply

- ZSTD (actual data compression) - De-duplication (i.e. what you're saying) Although AFAIK it's not "just point to it" but rather storing sorted data and being able to say "the next 2M rows have the same PR Title"

- De-duplication (i.e. what you're saying) Although AFAIK it's not "just point to it" but rather storing sorted data and being able to say "the next 2M rows have the same PR Title"

Although AFAIK it's not "just point to it" but rather storing sorted data and being able to say "the next 2M rows have the same PR Title"

reply

reply

reply

reply

Same is applicable for other language community, of course

reply

reply

We noticed for example the importance of letting the model pull from the context, instead of pushing lots of data in the prompt. We have a "complex" error reporting because we have to differentiate between real non-retryable errors and errors that teach the model to retry differently. It changes the model behavior completely. Also I agree with "significant weight of human input and judgement", we spent lots of time optimizing the index and thinking about how to organize data so queries perform at scale. Claude wasn't very helpful there.

Also I agree with "significant weight of human input and judgement", we spent lots of time optimizing the index and thinking about how to organize data so queries perform at scale. Claude wasn't very helpful there.

reply

reply

reply

Isn't that precisely what is done when prompting?

reply

reply

Models are evolving fast . If your experience is older than a few months, I encourage you to try again. I mean this with the best intentions: it's seriously mind boggling. We started doing this with Sonnet 4.0 and the relevance was okay at best. Then in September we shifted to Sonnet 4.5 and it's been night and day. Every single model released since then (Opus 4.5, 4.6) has meaningfully improved the quality of results

I mean this with the best intentions: it's seriously mind boggling. We started doing this with Sonnet 4.0 and the relevance was okay at best. Then in September we shifted to Sonnet 4.5 and it's been night and day. Every single model released since then (Opus 4.5, 4.6) has meaningfully improved the quality of results

Every single model released since then (Opus 4.5, 4.6) has meaningfully improved the quality of results

reply

reply

But it's night and day to fix your CI when someone (in this case an agent) already dug into the logs, the code of the test and propose options to fix. We have several customers asking us to automate the rest (all the way to merge code), but we haven't done it for the reasons you mention. Although I am sure we'll get there sometimes this year.

reply

There are bridges here that the industry has yet to figure out. There is absolutely a place for LLMs in these workflows, and what you've done here with the Mendral agent is very disciplined, which is, I'd venture to say, uncommon. Leadership wants results, which presses teams to ship things that maybe shouldn't be shipped quite yet. IMO the industry is moving faster than they can keep up with the implications.

reply

reply

reply

In the history of this company, I can honestly say that this SQL/LLM thing wasn't the hardest :)

reply

reply

reply

(In that way you can see the title edit as conforming to the HN guideline: "" Please use the original title, unless it is misleading or linkbait; don't editorialize. "" under the "linkbait" umbrella. - https://news.ycombinator.com/newsguidelines.html )

reply

reply

reply

reply
