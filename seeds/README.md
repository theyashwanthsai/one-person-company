# Seeds

Agents are no longer seeded via SQL. Instead, they are registered from their skill folders.

## Register Agents

After running database migrations, register your agents:

```bash
python scripts/register_agents.py
```

This will:
1. Scan the `agents/` folder
2. Parse each agent's `soul.md` file
3. Register them in the database

## Agent Structure

Each agent is a folder under `agents/`:

```
agents/
├── strategist_lead/
│   ├── soul.md              # Personality + instructions (required)
│   └── skills/              # Session/task-specific skills
```

## Adding a New Agent

1. Create a new folder under `agents/`
2. Add a `soul.md` file with frontmatter
3. Run `python scripts/register_agents.py`

Done! The agent is now ready to work.
