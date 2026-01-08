import httpx
import os
from datetime import datetime
from typing import Optional, List
from src.app.models import PRMetadata

async def get_github_pr(repo_owner: str, repo_name: str, pr_number: int) -> Optional[PRMetadata]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        # Fetch changed files to check for tests/docs
        files_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}/files"
        files_response = await client.get(files_url, headers=headers)
        changed_filenames = []
        if files_response.status_code == 200:
            changed_filenames = [f["filename"] for f in files_response.json()]
        
        return PRMetadata(
            title=data["title"],
            description=data.get("body"),
            author=data["user"]["login"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            files_changed=data["changed_files"],
            lines_added=data["additions"],
            lines_removed=data["deletions"],
            labels=[l["name"] for l in data.get("labels", [])],
            review_status=data.get("state", "unknown"),
            repo_name=f"{repo_owner}/{repo_name}",
            pr_number=pr_number,
            url=data["html_url"],
            changed_filenames=changed_filenames
        )

async def get_potential_reviewers(repo_owner: str, repo_name: str, exclude_user: str) -> List[str]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    
    # Fetch contributors as a proxy for potential reviewers
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contributors?per_page=10"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                contributors = response.json()
                # Filter out:
                # 1. The PR author
                # 2. Bots (checked via type and login suffix)
                # 3. Limit to 1 suggestion
                potential = [
                    c["login"] for c in contributors 
                    if c["login"] != exclude_user 
                    and c["type"] == "User" 
                    and not c["login"].endswith("[bot]")
                ]
                return potential[:1]
        except Exception as e:
            print(f"Error fetching reviewers: {e}")
    
    return []

