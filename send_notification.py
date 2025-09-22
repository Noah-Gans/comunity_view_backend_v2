#!/usr/bin/env python3
"""
Email notification script for Community View backend
Reliable email delivery for daily update pipeline
"""

import smtplib
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_email(subject, body, to_email, from_email, smtp_user, smtp_pass, log_file=None):
    """
    Send email notification with optional log file attachment
    
    Args:
        subject (str): Email subject
        body (str): Email body content
        to_email (str): Recipient email address
        from_email (str): Sender email address
        smtp_user (str): SMTP username (usually same as from_email)
        smtp_pass (str): SMTP password or app password
        log_file (str): Optional path to log file to attach
    """
    try:
        logger.info(f"📧 Preparing to send email to {to_email}")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach log file if provided and exists
        if log_file and os.path.exists(log_file):
            try:
                with open(log_file, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(log_file)}'
                )
                msg.attach(part)
                logger.info(f"�� Attached log file: {log_file}")
            except Exception as e:
                logger.warning(f"⚠️ Could not attach log file: {e}")
        
        # Connect to Gmail SMTP server
        logger.info("�� Connecting to SMTP server...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        # Login and send email
        logger.info("🔐 Authenticating...")
        server.login(smtp_user, smtp_pass)
        
        # Send email
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        
        logger.info("✅ Email sent successfully!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ SMTP Authentication failed: {e}")
        logger.error("💡 Make sure you're using an App Password, not your regular password")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"❌ SMTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False

def send_success_notification(to_email, from_email, smtp_user, smtp_pass, log_file, duration, summary, health_status=""):
    """Send success notification email"""
    subject = "✅ Community View Daily Update - SUCCESS"
    
    body = f"""
Daily Update Pipeline Report
============================

Status: SUCCESS ✅
Time: {summary.get('timestamp', 'N/A')}
Duration: {duration} seconds

Summary:
{summary.get('message', 'Pipeline completed successfully')}

Details:
- New tiles generated in: {summary.get('tiles_dir', 'N/A')}
- Latest symlink: {summary.get('symlink', 'N/A')}
- Martin config updated: {summary.get('martin_updated', 'Yes')}
- Search index regenerated: {summary.get('search_updated', 'Yes')}
- Old runs cleaned up: {summary.get('cleanup_done', 'Yes')}

Disk Usage: {summary.get('disk_usage', 'N/A')}

Service Health Status:
{health_status}

---
This is an automated message from your Community View backend system.
"""
    
    return send_email(subject, body, to_email, from_email, smtp_user, smtp_pass, log_file)

def send_error_notification(to_email, from_email, smtp_user, smtp_pass, log_file, error_msg, duration):
    """Send error notification email"""
    subject = "❌ Community View Daily Update - FAILED"
    
    body = f"""
Daily Update Pipeline Report
============================

Status: FAILED ❌
Time: {os.popen('date').read().strip()}
Duration: {duration} seconds

Error: {error_msg}

Please check the log file for more details.

Last 20 lines of log:
{get_last_log_lines(log_file)}

---
This is an automated message from your Community View backend system.
Please investigate the issue as soon as possible.
"""
    
    return send_email(subject, body, to_email, from_email, smtp_user, smtp_pass, log_file)

def get_last_log_lines(log_file, lines=20):
    """Get the last N lines from log file"""
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        else:
            return "Log file not found"
    except Exception as e:
        return f"Error reading log file: {e}"

def main():
    """Main function for command line usage"""
    if len(sys.argv) < 7:
        print("Usage: python send_notification.py <type> <to_email> <from_email> <smtp_user> <smtp_pass> <log_file> [additional_args...]")
        print("Types: success, error")
        print("Example: python send_notification.py success user@gmail.com sender@gmail.com sender@gmail.com app_password /path/to/log.txt")
        sys.exit(1)
    
    notification_type = sys.argv[1]
    to_email = sys.argv[2]
    from_email = sys.argv[3]
    smtp_user = sys.argv[4]
    smtp_pass = sys.argv[5]
    log_file = sys.argv[6]
    
    if notification_type == "success":
        # Parse additional arguments for success notification
        duration = sys.argv[7] if len(sys.argv) > 7 else "0"
        
        # Create summary from additional args or defaults
        summary = {
            'timestamp': os.popen('date').read().strip(),
            'message': 'Pipeline completed successfully',
            'tiles_dir': sys.argv[8] if len(sys.argv) > 8 else 'N/A',
            'symlink': sys.argv[9] if len(sys.argv) > 9 else 'N/A',
            'martin_updated': 'Yes',
            'search_updated': 'Yes',
            'cleanup_done': 'Yes',
            'disk_usage': sys.argv[10] if len(sys.argv) > 10 else 'N/A'
        }
        
        success = send_success_notification(to_email, from_email, smtp_user, smtp_pass, log_file, duration, summary)
        
    elif notification_type == "error":
        error_msg = sys.argv[7] if len(sys.argv) > 7 else "Unknown error"
        duration = sys.argv[8] if len(sys.argv) > 8 else "0"
        
        success = send_error_notification(to_email, from_email, smtp_user, smtp_pass, log_file, error_msg, duration)
        
    else:
        print(f"❌ Unknown notification type: {notification_type}")
        sys.exit(1)
    
    if success:
        print("✅ Email notification sent successfully")
        sys.exit(0)
    else:
        print("❌ Failed to send email notification")
        sys.exit(1)

if __name__ == "__main__":
    main()
