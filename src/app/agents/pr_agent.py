import os
from typing import List
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from src.app.models import PRMetadata, PRAnalysisOutput
from src.app.services.signals import analyze_pr

# Define the model. We check for the Gemini API key.
gemini_key = os.getenv("GEMINI_API_KEY")

if gemini_key:
    model = GeminiModel('gemini-1.5-flash', api_key=gemini_key)
else:
    # Fallback or placeholder
    model = 'google-gla:gemini-1.5-flash'

def get_agent():
    return Agent(
        model,
        result_type=PRAnalysisOutput,
        system_prompt=(
            "You are 'PR Whisperer', a helpful bot that analyzes pull requests. "
            "Your goal is to help PRs get reviewed and merged faster by providing "
            "concise summaries, detecting blockers, and suggesting improvements. "
            "Keep your tone playful but professional. "
            "Use the provided PR metadata to generate a natural language summary."
        ),
    )

# Use the AI agent for analysis if the API key is present
def get_pr_analysis(pr: PRMetadata, suggested_reviewers: List[str] = None) -> PRAnalysisOutput:
    if gemini_key:
        try:
            agent = get_agent()
            # We pass the PR data as a string to the agent
            result = agent.run_sync(
                f"Analyze this PR: {pr.model_dump_json()}. "
                f"Suggested reviewers already found: {suggested_reviewers}"
            )
            return result.data
        except Exception as e:
            print(f"AI Analysis failed, falling back to rules: {e}")
    
    # Fallback to rule-based logic if AI is not configured or fails
    return analyze_pr(pr, suggested_reviewers=suggested_reviewers)

