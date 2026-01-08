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
from src.app.services.github import get_github_pr, get_potential_reviewers

app = FastAPI(title="PR Whisperer")

# Regex to detect GitHub PR URLs
GITHUB_PR_REGEX = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"

@app.get("/")
async def root():
    return {"message": "PR Whisperer is active!"}

@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
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
        
        match = re.search(GITHUB_PR_REGEX, text)
        if match:
            owner, repo, pr_number = match.groups()
            # Process analysis in the background
            background_tasks.add_task(
                process_slack_pr_link, 
                owner, repo, int(pr_number), channel, thread_ts
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

async def process_slack_pr_link(owner: str, repo: str, pr_number: int, channel: str, thread_ts: str):
    # 1. Fetch & Analyze PR
    pr_metadata = await get_github_pr(owner, repo, pr_number)
    if pr_metadata:
        # Fetch real potential reviewers
        reviewers = await get_potential_reviewers(owner, repo, exclude_user=pr_metadata.author)
        analysis = get_pr_analysis(pr_metadata, suggested_reviewers=reviewers)
        
        # 2. Reply in Thread
        post_thread_reply(channel, thread_ts, analysis)
        
        # 3. Save Reminder to DB (2 days later)
        db = SessionLocal()
        try:
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
    uvicorn.run(app, host="0.0.0.0", port=8000)

