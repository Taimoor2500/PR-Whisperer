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

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   Create a `.env` file with:
   - `SLACK_WEBHOOK_URL`
   - `GITHUB_TOKEN` (optional for MVP)
   - `OPENAI_API_KEY` (for future AI features)

3. Run the application:
   ```bash
   python src/app/main.py
   ```

## API Endpoints

- `POST /analyze`: Receives PR metadata and returns an analysis report.

