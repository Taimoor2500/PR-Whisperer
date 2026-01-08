import os
from dotenv import load_dotenv

# Load environment variables before importing other local modules
load_dotenv()

from fastapi import FastAPI, HTTPException
from src.app.models import PRMetadata, PRAnalysisOutput
from src.app.agents.pr_agent import get_pr_analysis
from src.app.services.slack import send_slack_message
from src.app.services.github import get_github_pr, get_potential_reviewers

app = FastAPI(title="PR Whisperer")

@app.get("/")
async def root():
    return {"message": "PR Whisperer is active!"}

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

