"""
Session Scheduler
Triggers different session types at scheduled times.
"""

import os
import sys
import asyncio
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from workers.ceo_standup import run_ceo_standup
from workers.brainstorm import run_brainstorm_session
from workers.market_review import run_market_review_session
from workers.watercooler import run_watercooler_session


def schedule_ceo_standup(time_str: str = "09:00"):
    """Schedule daily CEO standup."""
    def job():
        print(f"\n[{datetime.now()}] Triggering CEO standup...")
        asyncio.run(run_ceo_standup())
    
    schedule.every().day.at(time_str).do(job)
    print(f"  CEO standup → {time_str} daily")


def schedule_agent_sessions():
    """Schedule agent-to-agent sessions throughout the day."""
    
    def run_brainstorm():
        print(f"\n[{datetime.now()}] Triggering brainstorm...")
        asyncio.run(run_brainstorm_session())
    
    def run_market_review():
        print(f"\n[{datetime.now()}] Triggering market review...")
        asyncio.run(run_market_review_session())
    
    def run_watercooler():
        print(f"\n[{datetime.now()}] Triggering watercooler...")
        asyncio.run(run_watercooler_session())
    
    schedule.every().day.at("10:30").do(run_brainstorm)
    schedule.every().day.at("15:00").do(run_brainstorm)
    schedule.every().day.at("14:00").do(run_market_review)
    schedule.every().day.at("12:00").do(run_watercooler)
    schedule.every().day.at("16:30").do(run_watercooler)
    
    print("  Brainstorm   → 10:30, 15:00")
    print("  Market Review → 14:00")
    print("  Watercooler   → 12:00, 16:30")


def run_scheduler():
    """Run the scheduler loop."""
    print("🕐 Session scheduler starting...")
    print(f"   Time: {datetime.now()}\n")
    
    schedule_ceo_standup("09:00")
    schedule_agent_sessions()
    
    print(f"\n⏳ Running. Ctrl+C to stop.\n")
    
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == '__main__':
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n👋 Scheduler stopped")
