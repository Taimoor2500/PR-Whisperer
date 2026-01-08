import httpx
import os
from src.app.models import PRAnalysisOutput

def build_analysis_blocks(analysis: PRAnalysisOutput):
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
    return blocks

def send_slack_message(analysis: PRAnalysisOutput):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Slack webhook URL not set.")
        return

    payload = {"blocks": build_analysis_blocks(analysis)}
    
    try:
        response = httpx.post(webhook_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Slack message: {e}")

def post_thread_reply(channel: str, thread_ts: str, analysis: PRAnalysisOutput = None, text: str = None):
    # Note: Threaded replies usually require a Slack Bot Token (chat.postMessage)
    # rather than an Incoming Webhook. We'll check for the token first.
    token = os.getenv("SLACK_BOT_TOKEN")
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if token:
        url = "https://slack.com/api/chat.postMessage"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "channel": channel,
            "thread_ts": thread_ts,
        }
        if analysis:
            payload["blocks"] = build_analysis_blocks(analysis)
        else:
            payload["text"] = text
            
        try:
            response = httpx.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to post Slack thread reply via API: {e}")
    elif webhook_url:
        # Fallback to webhook (might not support threading depending on webhook type)
        payload = {"thread_ts": thread_ts}
        if analysis:
            payload["blocks"] = build_analysis_blocks(analysis)
        else:
            payload["text"] = text
        try:
            httpx.post(webhook_url, json=payload)
        except Exception as e:
            print(f"Failed to post Slack thread reply via Webhook: {e}")

