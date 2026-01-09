import os
import re
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from src.app.database import init_db, SessionLocal, PRReminder

# Load environment variables before importing other local modules
load_dotenv()

# Initialize Database
init_db()

from src.app.models import PRMetadata, PRAnalysisOutput
from src.app.agents.pr_agent import get_pr_analysis
from src.app.services.slack import send_slack_message, post_thread_reply
from src.app.services.github import get_github_pr, get_potential_reviewers, request_copilot_review

app = FastAPI(title="PR Whisperer")

# Regex to detect GitHub PR URLs
GITHUB_PR_REGEX = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"

@app.get("/")
async def root():
    """
    Health check endpoint to keep the app awake on Render free tier.
    """
    return {"message": "PR Whisperer is active!", "status": "healthy"}

@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except Exception:
        # Fallback for non-JSON requests
        return {"status": "error", "message": "invalid json"}
    
    # Handle Slack URL Verification (Challenge)
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}
    
    # Process Message Events
    # We check for 'event' key and ensure it's a message not sent by a bot
    event = data.get("event")
    if event and event.get("type") == "message" and not event.get("bot_id"):
        text = event.get("text", "")
        channel = event.get("channel")
        thread_ts = event.get("ts") # Current message timestamp acts as thread ID
        
        # Find ALL PR links in the message
        matches = re.findall(GITHUB_PR_REGEX, text)
        if matches:
            # Process all PRs together in the background
            background_tasks.add_task(
                process_multiple_prs, 
                matches, channel, thread_ts
            )
            
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    # Start the reminder checker loop
    asyncio.create_task(reminder_checker_loop())

async def reminder_checker_loop():
    while True:
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None) # SQLite doesn't store timezone
            due_reminders = db.query(PRReminder).filter(
                PRReminder.reminder_time <= now,
                PRReminder.is_sent == False
            ).all()

            for reminder in due_reminders:
                # Re-fetch PR to see if it's still open
                updated_pr = await get_github_pr(reminder.owner, reminder.repo, reminder.pr_number)
                if updated_pr and updated_pr.review_status == "open":
                    post_thread_reply(
                        reminder.channel, 
                        reminder.thread_ts, 
                        text=f"⏰ Quick nudge! This PR is still open. Any blockers, @{updated_pr.author}?"
                    )
                
                reminder.is_sent = True
                db.commit()
        except Exception as e:
            print(f"Error in reminder loop: {e}")
        finally:
            db.close()
        
        await asyncio.sleep(60 * 60) # Check once an hour

async def process_multiple_prs(matches: list, channel: str, thread_ts: str):
    """Process multiple PR links and send a single consolidated summary."""
    analyses = []
    db = SessionLocal()
    
    try:
        for owner, repo, pr_number in matches:
            pr_number = int(pr_number)
            
            # Fetch & Analyze each PR
            pr_metadata = await get_github_pr(owner, repo, pr_number)
            if pr_metadata:
                reviewers = await get_potential_reviewers(owner, repo, exclude_user=pr_metadata.author)
                analysis = get_pr_analysis(pr_metadata, suggested_reviewers=reviewers)
                analyses.append((pr_metadata, analysis))
                
                # Trigger Copilot review
                await request_copilot_review(owner, repo, pr_number)
                
                # Save Reminder to DB (2 days later) for each PR
                reminder_time = datetime.now() + timedelta(days=2)
                new_reminder = PRReminder(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number,
                    channel=channel,
                    thread_ts=thread_ts,
                    reminder_time=reminder_time
                )
                db.add(new_reminder)
        
        db.commit()
    finally:
        db.close()
    
    # Send a single consolidated message
    if analyses:
        consolidated_message = format_consolidated_summary(analyses)
        post_thread_reply(channel, thread_ts, text=consolidated_message)


def format_consolidated_summary(analyses: list) -> str:
    """Format multiple PR analyses into a single message."""
    if len(analyses) == 1:
        # Single PR - use the standard format
        pr_metadata, analysis = analyses[0]
        return format_single_pr(pr_metadata, analysis)
    
    # Multiple PRs - create a consolidated summary
    lines = [f"📦 *{len(analyses)} PRs detected!* Here's the breakdown:\n"]
    
    for i, (pr_metadata, analysis) in enumerate(analyses, 1):
        lines.append(f"{'─' * 40}")
        lines.append(f"*#{i} — <{pr_metadata.url}|{pr_metadata.title}>*")
        lines.append(f"👤 Author: `{pr_metadata.author}` | 📊 +{pr_metadata.lines_added}/-{pr_metadata.lines_removed}")
        lines.append(f"📝 {analysis.summary}")
        
        # Show detected signals (blockers/warnings)
        blockers = [s for s in analysis.signals if s.detected]
        if blockers:
            lines.append(f"⚠️ Signals: {', '.join(s.name for s in blockers)}")
        
        if analysis.suggested_reviewers:
            lines.append(f"👀 Reviewers: {', '.join(analysis.suggested_reviewers[:3])}")
        lines.append("")
    
    lines.append(f"{'─' * 40}")
    lines.append("🤖 Copilot review requested for all PRs!")
    lines.append("⏰ I'll nudge you in 2 days if any of these are still open!")
    
    return "\n".join(lines)


def format_single_pr(pr_metadata, analysis) -> str:
    """Format a single PR analysis."""
    lines = [
        f"🔍 *PR Analysis: <{pr_metadata.url}|{pr_metadata.title}>*\n",
        f"📝 {analysis.summary}\n",
    ]
    
    # Signals
    detected = [s for s in analysis.signals if s.detected]
    if detected:
        lines.append("*Signals Detected:*")
        for signal in detected:
            lines.append(f"  • {signal.name}: {signal.message}")
        lines.append("")
    
    # Reviewers
    if analysis.suggested_reviewers:
        lines.append(f"👀 *Suggested Reviewers:* {', '.join(analysis.suggested_reviewers)}\n")
    
    # Hints
    if analysis.improvement_hints:
        lines.append("💡 *Tips:*")
        for hint in analysis.improvement_hints:
            lines.append(f"  • {hint}")
    
    lines.append("\n🤖 Copilot review requested!")
    lines.append("⏰ I'll nudge you in 2 days if this is still open!")
    
    return "\n".join(lines)

@app.post("/analyze", response_model=PRAnalysisOutput)
async def analyze_pull_request(pr: PRMetadata):
    try:
        # Try to fetch real reviewers if we have repo info
        reviewers = []
        if "/" in pr.repo_name:
            owner, repo = pr.repo_name.split("/", 1)
            reviewers = await get_potential_reviewers(owner, repo, exclude_user=pr.author)

        analysis = get_pr_analysis(pr, suggested_reviewers=reviewers)
        
        # Optionally send to slack if SLACK_WEBHOOK_URL is set
        if os.getenv("SLACK_WEBHOOK_URL"):
            send_slack_message(analysis)
            
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/github/{owner}/{repo}/{pr_number}", response_model=PRAnalysisOutput)
async def analyze_github_pull_request(owner: str, repo: str, pr_number: int):
    pr_metadata = await get_github_pr(owner, repo, pr_number)
    if not pr_metadata:
        raise HTTPException(status_code=404, detail="PR not found or GitHub API error")
    
    # Fetch real potential reviewers
    reviewers = await get_potential_reviewers(owner, repo, exclude_user=pr_metadata.author)
    
    try:
        analysis = get_pr_analysis(pr_metadata, suggested_reviewers=reviewers)
        
        if os.getenv("SLACK_WEBHOOK_URL"):
            send_slack_message(analysis)
            
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Default to 7860 for Hugging Face compatibility
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)

