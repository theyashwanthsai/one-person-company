"""
Shared helpers for the manual test scripts under tests/.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]


def setup_test_environment():
    """Ensure tests can import from the repo root and load env variables."""
    sys.path.insert(0, str(REPO_ROOT))
    load_dotenv()


def print_header(title: str):
    divider = "=" * 60
    print(f"\n{divider}\n{title}\n{divider}")
