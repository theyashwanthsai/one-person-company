import ast
import os
import re
from typing import List


SCHEDULE_CODE_BLOCK_PATTERN = re.compile(r"```(?:python|py)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def _normalize_schedule_source(source: str) -> str:
    stripped = source.strip()
    if stripped.startswith("SCHEDULE") and "=" in stripped:
        return stripped.split("=", 1)[1].strip()
    return stripped


def load_schedule_from_markdown(path: str) -> List[dict]:
    """Load schedule entries from the first python fenced block in a markdown file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Schedule file not found: {path}")

    raw = open(path, "r", encoding="utf-8").read()
    match = SCHEDULE_CODE_BLOCK_PATTERN.search(raw)
    if not match:
        raise ValueError(f"No fenced python schedule block found in {path}")

    code_block = _normalize_schedule_source(match.group(1))
    data = ast.literal_eval(code_block)

    if not isinstance(data, list):
        raise ValueError("Schedule markdown block must evaluate to a list of entries")

    required_common = {"time", "type", "task"}
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"Schedule entry #{idx + 1} must be a dict")
        missing = required_common.difference(entry.keys())
        if missing:
            raise ValueError(f"Schedule entry #{idx + 1} missing required keys: {sorted(missing)}")
        if entry["type"] == "solo" and "agent" not in entry:
            raise ValueError(f"Schedule entry #{idx + 1} is solo and must include 'agent'")
        if entry["type"] == "meeting" and "agents" not in entry:
            raise ValueError(f"Schedule entry #{idx + 1} is meeting and must include 'agents'")

    return data
