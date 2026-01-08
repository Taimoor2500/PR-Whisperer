from src.app.models import PRMetadata, Signal, PRAnalysisOutput
from typing import List

def detect_signals(pr: PRMetadata) -> List[Signal]:
    signals = []

    # Large PR
    if (pr.lines_added + pr.lines_removed) > 500:
        signals.append(Signal(
            name="Large PR",
            detected=True,
            message="Heads up! This PR is a bit chunky 🍔",
            action="Consider splitting it into smaller PRs."
        ))

    # No Tests
    has_test_files = any("test" in f.lower() for f in pr.changed_filenames)
    if not has_test_files and pr.lines_added > 20: # Only suggest tests if there's significant new code
        signals.append(Signal(
            name="No Tests",
            detected=True,
            message="No tests detected! 🧪",
            action="Let's add one for safety."
        ))

    # Docs Missing
    # Common doc paths
    doc_keywords = ["doc", "docs", "documentation", "readme.md"]
    has_doc_changes = any(any(k in f.lower() for k in doc_keywords) for f in pr.changed_filenames)
    if not has_doc_changes and (pr.lines_added > 100 or "feature" in [l.lower() for l in pr.labels]):
        signals.append(Signal(
            name="Docs Missing",
            detected=True,
            message="Docs missing? 📚",
            action="Consider updating documentation for these changes."
        ))
    
    # Stuck PR
    import datetime
    if (datetime.datetime.now(datetime.timezone.utc) - pr.created_at).days > 2:
        signals.append(Signal(
            name="Stuck PR",
            detected=True,
            message="This PR has been open for more than 2 days. ⏳",
            action="Suggest nudging reviewers."
        ))

    return signals

def generate_summary(pr: PRMetadata) -> str:
    # MVP: Simple rule-based summary
    return f"PR by {pr.author} in {pr.repo_name} with {pr.files_changed} files changed (+{pr.lines_added}, -{pr.lines_removed})."

def analyze_pr(pr: PRMetadata, suggested_reviewers: List[str] = None) -> PRAnalysisOutput:
    signals = detect_signals(pr)
    summary = generate_summary(pr)
    
    # Use real reviewers if provided, otherwise fallback to placeholders
    reviewers = suggested_reviewers if suggested_reviewers else ["Alice", "Bob"]
    
    hints = [s.action for s in signals]
    
    return PRAnalysisOutput(
        summary=summary,
        signals=signals,
        suggested_reviewers=reviewers,
        improvement_hints=hints
    )

