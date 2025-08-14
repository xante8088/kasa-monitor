"""Email notification system with templates and queuing.

Copyright (C) 2025 Kasa Monitor Contributors

This file is part of Kasa Monitor.

Kasa Monitor is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Kasa Monitor is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Kasa Monitor. If not, see <https://www.gnu.org/licenses/>.
"""

import smtplib
import sqlite3
import json
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import jinja2
import markdown
import queue
import threading
import time
import hashlib
import base64


class EmailStatus(Enum):
    """Email delivery status."""
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"
    RETRY = "retry"


class EmailPriority(Enum):
    """Email priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class EmailMessage:
    """Email message structure."""
    to: Union[str, List[str]]
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    cc: Optional[Union[str, List[str]]] = None
    bcc: Optional[Union[str, List[str]]] = None
    reply_to: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    headers: Optional[Dict[str, str]] = None
    priority: EmailPriority = EmailPriority.NORMAL
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    track_opens: bool = True
    track_clicks: bool = True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['priority'] = self.priority.value
        return data


class SMTPConfig:
    """SMTP server configuration."""
    
    def __init__(self,
                 host: str,
                 port: int,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 use_tls: bool = True,
                 use_ssl: bool = False,
                 from_email: str = "noreply@kasa-monitor.local",
                 from_name: str = "Kasa Monitor",
                 timeout: int = 30):
        """Initialize SMTP configuration.
        
        Args:
            host: SMTP server hostname
            port: SMTP server port
            username: SMTP username
            password: SMTP password
            use_tls: Use STARTTLS
            use_ssl: Use SSL/TLS
            from_email: Default sender email
            from_name: Default sender name
            timeout: Connection timeout
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.from_email = from_email
        self.from_name = from_name
        self.timeout = timeout


class EmailTemplateEngine:
    """Email template rendering engine."""
    
    def __init__(self, template_dir: str = "templates/email"):
        """Initialize template engine.
        
        Args:
            template_dir: Directory containing email templates
        """
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Register custom filters
        self.jinja_env.filters['markdown'] = self._markdown_filter
        self.jinja_env.filters['format_date'] = self._format_date_filter
        
        # Create default templates
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default email templates."""
        templates = {
            'base.html': """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Kasa Monitor{% endblock %}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2563eb; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f8f9fa; }
        .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
        .button { display: inline-block; padding: 10px 20px; background: #2563eb; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{% block header %}Kasa Monitor{% endblock %}</h1>
        </div>
        <div class="content">
            {% block content %}{% endblock %}
        </div>
        <div class="footer">
            {% block footer %}
            <p>&copy; {{ year }} Kasa Monitor. All rights reserved.</p>
            <p>You are receiving this email because you are registered with Kasa Monitor.</p>
            {% endblock %}
        </div>
    </div>
</body>
</html>""",
            
            'alert.html': """{% extends "base.html" %}
{% block title %}Alert: {{ alert_title }}{% endblock %}
{% block header %}⚠️ Alert Notification{% endblock %}
{% block content %}
<h2>{{ alert_title }}</h2>
<p><strong>Severity:</strong> {{ severity }}</p>
<p><strong>Time:</strong> {{ timestamp }}</p>
<div style="background: white; padding: 15px; border-left: 4px solid #dc3545; margin: 20px 0;">
    {{ message }}
</div>
{% if details %}
<h3>Details:</h3>
<ul>
{% for key, value in details.items() %}
    <li><strong>{{ key }}:</strong> {{ value }}</li>
{% endfor %}
</ul>
{% endif %}
{% if action_url %}
<p style="text-align: center; margin-top: 30px;">
    <a href="{{ action_url }}" class="button">View in Dashboard</a>
</p>
{% endif %}
{% endblock %}""",
            
            'welcome.html': """{% extends "base.html" %}
{% block title %}Welcome to Kasa Monitor{% endblock %}
{% block header %}Welcome to Kasa Monitor!{% endblock %}
{% block content %}
<h2>Hello {{ name }}!</h2>
<p>Your account has been successfully created. You can now start monitoring and controlling your Kasa devices.</p>
<h3>Getting Started:</h3>
<ul>
    <li>Add your first device</li>
    <li>Configure electricity rates</li>
    <li>Set up alerts and schedules</li>
    <li>View energy consumption reports</li>
</ul>
<p style="text-align: center; margin-top: 30px;">
    <a href="{{ login_url }}" class="button">Login to Dashboard</a>
</p>
{% endblock %}""",
            
            'password_reset.html': """{% extends "base.html" %}
{% block title %}Password Reset Request{% endblock %}
{% block header %}Password Reset Request{% endblock %}
{% block content %}
<h2>Password Reset Requested</h2>
<p>We received a request to reset your password. If you didn't make this request, you can ignore this email.</p>
<p>To reset your password, click the button below:</p>
<p style="text-align: center; margin: 30px 0;">
    <a href="{{ reset_url }}" class="button">Reset Password</a>
</p>
<p style="color: #666; font-size: 14px;">This link will expire in {{ expiry_hours }} hours.</p>
<p style="color: #666; font-size: 14px;">If the button doesn't work, copy and paste this link into your browser:</p>
<p style="color: #666; font-size: 12px; word-break: break-all;">{{ reset_url }}</p>
{% endblock %}""",
            
            'report.html': """{% extends "base.html" %}
{% block title %}{{ report_type }} Report{% endblock %}
{% block header %}{{ report_type }} Report{% endblock %}
{% block content %}
<h2>{{ report_title }}</h2>
<p><strong>Period:</strong> {{ start_date }} to {{ end_date }}</p>

{% if summary %}
<h3>Summary</h3>
<table style="width: 100%; border-collapse: collapse;">
{% for key, value in summary.items() %}
    <tr>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ key }}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{{ value }}</td>
    </tr>
{% endfor %}
</table>
{% endif %}

{% if data %}
{{ data | safe }}
{% endif %}

{% if attachment_note %}
<p style="margin-top: 20px; padding: 10px; background: #fff3cd; border: 1px solid #ffc107;">
    📎 Detailed report attached to this email
</p>
{% endif %}
{% endblock %}"""
        }
        
        # Save templates if they don't exist
        for filename, content in templates.items():
            template_path = self.template_dir / filename
            if not template_path.exists():
                template_path.write_text(content)
    
    def render(self, template_name: str, context: Dict[str, Any]) -> Tuple[str, str]:
        """Render email template.
        
        Args:
            template_name: Template filename
            context: Template context variables
            
        Returns:
            Tuple of (html_content, text_content)
        """
        # Add default context
        context.setdefault('year', datetime.now().year)
        context.setdefault('timestamp', datetime.now().isoformat())
        
        # Render HTML version
        template = self.jinja_env.get_template(template_name)
        html_content = template.render(**context)
        
        # Generate text version from HTML
        text_content = self._html_to_text(html_content)
        
        return html_content, text_content
    
    def _markdown_filter(self, text: str) -> str:
        """Convert Markdown to HTML.
        
        Args:
            text: Markdown text
            
        Returns:
            HTML content
        """
        return markdown.markdown(text, extensions=['extra', 'nl2br'])
    
    def _format_date_filter(self, date: Union[str, datetime], format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format date for display.
        
        Args:
            date: Date to format
            format: Date format string
            
        Returns:
            Formatted date string
        """
        if isinstance(date, str):
            date = datetime.fromisoformat(date)
        return date.strftime(format)
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text.
        
        Args:
            html: HTML content
            
        Returns:
            Plain text content
        """
        # Simple HTML to text conversion
        import re
        
        # Remove style and script tags
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        
        # Replace common tags
        text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\1\n', text)
        text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text)
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'  • \1\n', text)
        
        # Remove remaining tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        
        return text


class EmailQueue:
    """Email queue management."""
    
    def __init__(self, db_path: str = "kasa_monitor.db"):
        """Initialize email queue.
        
        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self._init_database()
        self.queue = queue.PriorityQueue()
        self.running = False
        self.worker_thread = None
    
    def _init_database(self):
        """Initialize email queue tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                body_html TEXT,
                body_text TEXT,
                attachments TEXT,
                priority INTEGER DEFAULT 2,
                category TEXT,
                status TEXT DEFAULT 'queued',
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scheduled_at TIMESTAMP,
                sent_at TIMESTAMP,
                next_retry TIMESTAMP,
                error_message TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_queue_status 
            ON email_queue(status, scheduled_at)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                FOREIGN KEY (message_id) REFERENCES email_queue(message_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def enqueue(self, message: EmailMessage, scheduled_at: Optional[datetime] = None) -> str:
        """Add email to queue.
        
        Args:
            message: Email message
            scheduled_at: Schedule delivery time
            
        Returns:
            Message ID
        """
        message_id = self._generate_message_id()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO email_queue 
            (message_id, recipient, subject, body_html, body_text, 
             attachments, priority, category, scheduled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id,
            json.dumps(message.to) if isinstance(message.to, list) else message.to,
            message.subject,
            message.body_html,
            message.body_text,
            json.dumps(message.attachments) if message.attachments else None,
            message.priority.value,
            message.category,
            scheduled_at
        ))
        
        conn.commit()
        conn.close()
        
        # Add to in-memory queue if scheduled for now
        if not scheduled_at or scheduled_at <= datetime.now():
            self.queue.put((message.priority.value * -1, message_id, message))
        
        return message_id
    
    def start_worker(self, smtp_config: SMTPConfig, interval: int = 5):
        """Start background worker thread.
        
        Args:
            smtp_config: SMTP configuration
            interval: Check interval in seconds
        """
        if self.running:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(smtp_config, interval),
            daemon=True
        )
        self.worker_thread.start()
    
    def stop_worker(self):
        """Stop background worker thread."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
    
    def _worker_loop(self, smtp_config: SMTPConfig, interval: int):
        """Background worker loop.
        
        Args:
            smtp_config: SMTP configuration
            interval: Check interval
        """
        sender = EmailSender(smtp_config)
        
        while self.running:
            # Process queued emails
            self._process_scheduled_emails()
            
            # Process in-memory queue
            try:
                while not self.queue.empty():
                    _, message_id, message = self.queue.get_nowait()
                    self._send_email(sender, message_id, message)
            except queue.Empty:
                pass
            
            # Process database queue
            self._process_database_queue(sender)
            
            # Sleep before next iteration
            time.sleep(interval)
    
    def _process_scheduled_emails(self):
        """Move scheduled emails to active queue."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT message_id, recipient, subject, body_html, body_text,
                   attachments, priority, category
            FROM email_queue
            WHERE status = 'queued'
            AND (scheduled_at IS NULL OR scheduled_at <= CURRENT_TIMESTAMP)
            LIMIT 10
        """)
        
        for row in cursor.fetchall():
            message_id = row[0]
            message = EmailMessage(
                to=json.loads(row[1]) if row[1].startswith('[') else row[1],
                subject=row[2],
                body_html=row[3],
                body_text=row[4],
                attachments=json.loads(row[5]) if row[5] else None,
                priority=EmailPriority(row[6]),
                category=row[7]
            )
            
            self.queue.put((message.priority.value * -1, message_id, message))
        
        conn.close()
    
    def _process_database_queue(self, sender: 'EmailSender'):
        """Process emails from database queue.
        
        Args:
            sender: Email sender instance
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get emails ready for retry
        cursor.execute("""
            SELECT message_id, recipient, subject, body_html, body_text,
                   attachments, priority, category
            FROM email_queue
            WHERE status = 'retry'
            AND next_retry <= CURRENT_TIMESTAMP
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            message_id = row[0]
            message = EmailMessage(
                to=json.loads(row[1]) if row[1].startswith('[') else row[1],
                subject=row[2],
                body_html=row[3],
                body_text=row[4],
                attachments=json.loads(row[5]) if row[5] else None,
                priority=EmailPriority(row[6]),
                category=row[7]
            )
            
            self._send_email(sender, message_id, message)
        
        conn.close()
    
    def _send_email(self, sender: 'EmailSender', message_id: str, message: EmailMessage):
        """Send email and update status.
        
        Args:
            sender: Email sender instance
            message_id: Message ID
            message: Email message
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update status to sending
        cursor.execute("""
            UPDATE email_queue
            SET status = 'sending', attempts = attempts + 1
            WHERE message_id = ?
        """, (message_id,))
        conn.commit()
        
        try:
            # Send email
            sender.send(message)
            
            # Update status to sent
            cursor.execute("""
                UPDATE email_queue
                SET status = 'sent', sent_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
            """, (message_id,))
            
            # Track delivery
            cursor.execute("""
                INSERT INTO email_tracking (message_id, event_type)
                VALUES (?, 'delivered')
            """, (message_id,))
            
        except Exception as e:
            # Get current attempts
            cursor.execute("""
                SELECT attempts, max_attempts FROM email_queue
                WHERE message_id = ?
            """, (message_id,))
            
            attempts, max_attempts = cursor.fetchone()
            
            if attempts >= max_attempts:
                # Mark as failed
                cursor.execute("""
                    UPDATE email_queue
                    SET status = 'failed', error_message = ?
                    WHERE message_id = ?
                """, (str(e), message_id))
            else:
                # Schedule retry
                next_retry = datetime.now() + timedelta(minutes=5 * attempts)
                cursor.execute("""
                    UPDATE email_queue
                    SET status = 'retry', next_retry = ?, error_message = ?
                    WHERE message_id = ?
                """, (next_retry, str(e), message_id))
            
            # Track failure
            cursor.execute("""
                INSERT INTO email_tracking (message_id, event_type, details)
                VALUES (?, 'failed', ?)
            """, (message_id, str(e)))
        
        conn.commit()
        conn.close()
    
    def _generate_message_id(self) -> str:
        """Generate unique message ID.
        
        Returns:
            Message ID
        """
        timestamp = datetime.now().isoformat()
        random_part = hashlib.md5(timestamp.encode()).hexdigest()[:8]
        return f"{timestamp}-{random_part}"
    
    def get_status(self, message_id: str) -> Optional[Dict]:
        """Get email status.
        
        Args:
            message_id: Message ID
            
        Returns:
            Status information
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT status, attempts, sent_at, error_message
            FROM email_queue
            WHERE message_id = ?
        """, (message_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'status': row[0],
                'attempts': row[1],
                'sent_at': row[2],
                'error_message': row[3]
            }
        
        return None


class EmailSender:
    """Email sending functionality."""
    
    def __init__(self, smtp_config: SMTPConfig):
        """Initialize email sender.
        
        Args:
            smtp_config: SMTP configuration
        """
        self.config = smtp_config
    
    def send(self, message: EmailMessage):
        """Send email message.
        
        Args:
            message: Email message to send
        """
        # Create MIME message
        msg = MIMEMultipart('alternative')
        
        # Set headers
        msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
        msg['Subject'] = message.subject
        
        # Handle recipients
        if isinstance(message.to, list):
            msg['To'] = ', '.join(message.to)
            recipients = message.to
        else:
            msg['To'] = message.to
            recipients = [message.to]
        
        if message.cc:
            if isinstance(message.cc, list):
                msg['Cc'] = ', '.join(message.cc)
                recipients.extend(message.cc)
            else:
                msg['Cc'] = message.cc
                recipients.append(message.cc)
        
        if message.reply_to:
            msg['Reply-To'] = message.reply_to
        
        # Add custom headers
        if message.headers:
            for key, value in message.headers.items():
                msg[key] = value
        
        # Add tracking pixel if enabled
        if message.track_opens and message.body_html:
            tracking_pixel = self._generate_tracking_pixel(msg['Message-ID'])
            message.body_html += tracking_pixel
        
        # Attach body
        if message.body_text:
            msg.attach(MIMEText(message.body_text, 'plain'))
        
        if message.body_html:
            msg.attach(MIMEText(message.body_html, 'html'))
        
        # Add attachments
        if message.attachments:
            for attachment in message.attachments:
                self._attach_file(msg, attachment)
        
        # Send email
        self._send_smtp(msg, recipients)
    
    def _send_smtp(self, msg: MIMEMultipart, recipients: List[str]):
        """Send email via SMTP.
        
        Args:
            msg: MIME message
            recipients: List of recipients
        """
        if self.config.use_ssl:
            server = smtplib.SMTP_SSL(
                self.config.host,
                self.config.port,
                timeout=self.config.timeout
            )
        else:
            server = smtplib.SMTP(
                self.config.host,
                self.config.port,
                timeout=self.config.timeout
            )
            
            if self.config.use_tls:
                server.starttls()
        
        try:
            if self.config.username and self.config.password:
                server.login(self.config.username, self.config.password)
            
            server.send_message(msg, to_addrs=recipients)
        finally:
            server.quit()
    
    def _attach_file(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Attach file to email.
        
        Args:
            msg: MIME message
            attachment: Attachment information
        """
        part = MIMEBase('application', 'octet-stream')
        
        if 'content' in attachment:
            # Content provided directly
            part.set_payload(attachment['content'])
        elif 'path' in attachment:
            # Read from file
            with open(attachment['path'], 'rb') as f:
                part.set_payload(f.read())
        
        encoders.encode_base64(part)
        
        filename = attachment.get('filename', 'attachment')
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={filename}'
        )
        
        msg.attach(part)
    
    def _generate_tracking_pixel(self, message_id: str) -> str:
        """Generate email tracking pixel.
        
        Args:
            message_id: Message ID
            
        Returns:
            HTML for tracking pixel
        """
        # In production, this would point to your tracking endpoint
        tracking_url = f"https://your-domain.com/track/open/{message_id}"
        return f'<img src="{tracking_url}" width="1" height="1" style="display:none" />'