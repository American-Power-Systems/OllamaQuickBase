import smtplib
import subprocess
import os
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIGURATION ---
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "your_email@ampowersys.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your_password")
EMAIL_TO = "bengillihan@ampowersys.com"
# ---------------------

def get_logs():
    # Fetch logs for the AI Worker from the last 24 hours (since midnight)
    try:
        # Note: 'today' in journalctl means 00:00:00 of the current day
        cmd = ["journalctl", "-u", "ai-worker", "--since", "today", "--no-pager"]
        result = subprocess.check_output(cmd, text=True)
        return result.splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error fetching logs: {e}")
        return []

def analyze_logs(log_lines):
    stats = {
        "total_jobs": 0,
        "success_jobs": 0,
        "failed_jobs": 0,
        "total_duration": 0.0,
        "errors": []
    }

    for line in log_lines:
        if "Processing Job:" in line:
            stats["total_jobs"] += 1
        
        if "Job complete for" in line:
            stats["success_jobs"] += 1
            
        if "Job failed for" in line:
            stats["failed_jobs"] += 1
            # Extract error message (everything after 'Job failed for ...:')
            parts = line.split(":", 3)
            if len(parts) > 3:
                stats["errors"].append(parts[3].strip())
            else:
                stats["errors"].append(line)

        # Look for the PERFORMANCE tag we added to worker.py
        # Log format: ... PERFORMANCE: Job finished in 123.45 seconds
        if "PERFORMANCE: Job finished in" in line:
            match = re.search(r"finished in (\d+\.\d+) seconds", line)
            if match:
                stats["total_duration"] += float(match.group(1))

    return stats

def send_email(stats):
    avg_time = 0
    if stats["success_jobs"] > 0:
        avg_time = stats["total_duration"] / stats["success_jobs"]

    subject = f"AI Worker Daily Report - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = f"""
    <h2>Daily Processing Summary</h2>
    <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}</p>
    
    <h3>Performance Metrics</h3>
    <ul>
        <li><b>Total Jobs Attempted:</b> {stats['total_jobs']}</li>
        <li><b>Successful Jobs:</b> {stats['success_jobs']}</li>
        <li><b>Failed Jobs:</b> {stats['failed_jobs']}</li>
        <li><b>Average Processing Time:</b> {avg_time:.2f} seconds</li>
    </ul>

    <h3>Issues & Errors</h3>
    { "<ul>" + "".join([f"<li>{e}</li>" for e in stats['errors']]) + "</ul>" if stats['errors'] else "<p>No errors recorded today.</p>" }
    
    <hr>
    <p><i>Sent from Azure AI Processor</i></p>
    """

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Report email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    logs = get_logs()
    if logs:
        statistics = analyze_logs(logs)
        send_email(statistics)
    else:
        print("No logs found for today.")