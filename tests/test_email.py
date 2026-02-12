import os
import sys
from pathlib import Path

# Add repo root so shared modules can be imported even when the script lives in tests/
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from lib.email_client import EmailClient



def test_email():
    client = EmailClient()

    success = client._send_email(
        client.ceo_email,
        "Test Email",
        "If you're reading this, SMTP works."
    )

    print(success)


def test_email_ceo():
    from tools.email_ceo import execute
    
    result = execute(
        agent_id="Thea",
        subject="Model drift detected in production",
        message="Validation accuracy dropped from 91% to 87% over the last 24 hours. Investigating potential data distribution shift.",
        urgency="high"
    )
    
    print(result)


if __name__ == "__main__":
    # test_email()
    test_email_ceo()
