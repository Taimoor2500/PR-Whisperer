---
title: PR Whisperer
emoji: 🤫
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# PR Whisperer

PR Whisperer is a bot designed to help pull requests get reviewed and merged faster.

## Features

- **PR Metadata Ingestion**: Handles data from GitHub/GitLab.
- **Rule-based Signals**: Detects large PRs, stuck PRs, and more.
- **Reviewer Suggestions**: Recommends reviewers based on PR history.
- **Slack Integration**: Sends analysis reports directly to Slack.
- **Pydantic AI Ready**: Built on a foundation that easily integrates AI agents.

## Tech Stack

- **FastAPI**: For the web server and webhook handling.
- **Pydantic AI**: For future AI-driven insights.
- **Httpx**: For asynchronous HTTP requests.

## Setup

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure environment variables**:
    Create a `.env` file with:
    - `SLACK_BOT_TOKEN`: Your xoxb token from Slack.
    - `SLACK_WEBHOOK_URL`: (Optional) Your Slack incoming webhook.
    - `GITHUB_TOKEN`: Your GitHub Personal Access Token.
    - `GEMINI_API_KEY`: (Optional) For AI summaries.
    - `DATABASE_URL`: (Optional) SQLite by default, Postgres for production.

3.  **Run the application**:
    ```bash
    uvicorn src.app.main:app --reload
    ```

## Deployment (Hugging Face Spaces + Supabase)

1.  **Supabase**: Create a free project and get the **Connection String (URI)**.
2.  **Hugging Face Spaces**:
    - Create a new **Space** ([huggingface.co/new-space](https://huggingface.co/new-space)).
    - SDK: **Docker** (Blank).
    - Go to **Settings** -> **Connect to GitHub** and link your repo.
    - Go to **Settings** -> **Variables and secrets** and add:
        - `DATABASE_URL`: Your Supabase URI.
        - `SLACK_BOT_TOKEN`: Your xoxb token.
        - `GITHUB_TOKEN`: Your GitHub PAT.
        - `GEMINI_API_KEY`: (Optional).
3.  **Slack Integration**:
    - Once deployed, your URL will be `https://[YOUR-USERNAME]-[SPACE-NAME].hf.space`.
    - Set your Slack Event Subscription Request URL to: `https://[YOUR-USERNAME]-[SPACE-NAME].hf.space/slack/events`.

## API Endpoints

- `POST /analyze`: Receives PR metadata and returns an analysis report.

