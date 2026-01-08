from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PRMetadata(BaseModel):
    title: str
    description: Optional[str] = None
    author: str
    created_at: datetime
    files_changed: int
    lines_added: int
    lines_removed: int
    labels: List[str] = []
    review_status: str = "pending"
    repo_name: str
    pr_number: int
    url: str
    changed_filenames: List[str] = [] # Added to track specific files

class Signal(BaseModel):
    name: str
    detected: bool
    message: str
    action: str

class PRAnalysisOutput(BaseModel):
    summary: str
    signals: List[Signal]
    suggested_reviewers: List[str]
    improvement_hints: List[str]

