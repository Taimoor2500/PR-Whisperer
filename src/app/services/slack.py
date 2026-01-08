import httpx
import os
from src.app.models import PRAnalysisOutput

def send_slack_message(analysis: PRAnalysisOutput):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Slack webhook URL not set.")
        return

    # Create a nice looking message
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*PR Analysis Summary*\n{analysis.summary}"
            }
        }
    ]

    if analysis.signals:
        signal_text = "*Signals Detected:*\n"
        for s in analysis.signals:
            signal_text += f"• {s.message} _({s.action})_\n"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": signal_text
            }
        })

    if analysis.suggested_reviewers:
        reviewers = ", ".join(analysis.suggested_reviewers)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Suggested Reviewers:* {reviewers}"
            }
        })

    payload = {"blocks": blocks}
    
    try:
        response = httpx.post(webhook_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Slack message: {e}")

