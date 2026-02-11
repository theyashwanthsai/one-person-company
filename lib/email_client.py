"""
Email client for CEO standup sessions.
Handles sending reminders, questionnaires, and parsing replies.
"""

import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime
import re


class EmailClient:
    """Email client for sending and receiving standup communications."""
    
    def __init__(self):
        # Email credentials from environment
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.imap_host = os.getenv('IMAP_HOST', 'imap.gmail.com')
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.ceo_email = os.getenv('CEO_EMAIL')
        
        if not all([self.email_address, self.email_password, self.ceo_email]):
            raise ValueError("Email credentials not configured. Set EMAIL_ADDRESS, EMAIL_PASSWORD, and CEO_EMAIL in .env")
    
    def send_reminder(self, session_id: str, scheduled_time: str) -> bool:
        """Send 5-minute reminder to CEO before standup."""
        subject = f"⏰ Standup in 5 minutes - {datetime.now().strftime('%B %d, %Y')}"
        
        body = f"""Hi!

Your daily standup with the team starts in 5 minutes.

You'll receive a questionnaire email shortly where each agent will share their updates.

Session ID: {session_id}
Time: {scheduled_time}

See you soon!
"""
        
        return self._send_email(self.ceo_email, subject, body)
    
    def send_questionnaire(self, session_id: str, agents: List[str]) -> bool:
        """Send standup questionnaire to agents and CEO."""
        subject = f"📋 Daily Standup - {datetime.now().strftime('%B %d, %Y')}"
        
        # Email to CEO
        ceo_body = f"""Time for standup! 

Your team will respond with their updates below. Please reply with your feedback once you've reviewed them.

Session ID: {session_id}

---

Agents participating: {', '.join(agents)}

Please reply to this email with your feedback or questions. Take your time (1-3 minutes).
"""
        
        return self._send_email(
            self.ceo_email, 
            subject, 
            ceo_body,
            session_id=session_id
        )
    
    def send_agent_prompt(self, session_id: str, agent_id: str, agent_email: str) -> bool:
        """Send questionnaire to individual agent."""
        subject = f"📋 Your Standup Update - {datetime.now().strftime('%B %d, %Y')}"
        
        body = f"""Hi {agent_id},

Please provide your standup update by replying to this email:

1. What changed since last time?
2. What are you confident about?
3. What are you uncertain about?

Keep it brief (2-3 sentences per question). You have 1-3 minutes.

Session ID: {session_id}
"""
        
        return self._send_email(agent_email, subject, body, session_id=session_id)
    
    def parse_replies(self, session_id: str, timeout_minutes: int = 5) -> Dict[str, str]:
        """
        Parse email replies for a given session.
        Returns dict of {sender_email: response_text}
        """
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host)
            mail.login(self.email_address, self.email_password)
            mail.select('inbox')
            
            # Search for emails with session_id in subject or body
            search_criteria = f'(SUBJECT "{session_id}")'
            _, message_numbers = mail.search(None, search_criteria)
            
            replies = {}
            
            for num in message_numbers[0].split():
                _, msg_data = mail.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                sender = email_message['From']
                
                # Extract email address from "Name <email>" format
                email_match = re.search(r'<(.+?)>', sender)
                if email_match:
                    sender = email_match.group(1)
                
                # Get email body
                body = self._get_email_body(email_message)
                replies[sender] = body
            
            mail.close()
            mail.logout()
            
            return replies
            
        except Exception as e:
            print(f"Error parsing email replies: {e}")
            return {}
    
    def _send_email(self, to: str, subject: str, body: str, session_id: Optional[str] = None) -> bool:
        """Send an email via SMTP."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = to
            msg['Subject'] = subject
            
            # Add session_id to headers for threading
            if session_id:
                msg['X-Session-ID'] = session_id
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Error sending email to {to}: {e}")
            return False
    
    def _get_email_body(self, email_message) -> str:
        """Extract plain text body from email message."""
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    return part.get_payload(decode=True).decode()
        else:
            return email_message.get_payload(decode=True).decode()
        return ""

