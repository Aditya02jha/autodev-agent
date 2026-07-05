from pydantic import BaseModel, Field
from typing import List, Optional


class AffectedFile(BaseModel):
    file: str                        # filename e.g. EmployeeService.java
    full_path: str                   # absolute path on disk — needed so executor can read it
    reason: str                      # why this file needs to change


class ChangePlan(BaseModel):
    summary: str
    affected_files: List[AffectedFile]
    changes: List[str]               # high-level steps, one per item


class TaskRequest(BaseModel):
    task: str = Field(..., description="Ticket description or task to implement")


class PlanRequest(BaseModel):
    ticket: str = Field(..., description="Ticket description")
    ticket_number: Optional[str] = Field(None, description="Optional ticket ID e.g. EMP-42")

class ApplyRequest(BaseModel):
    # Indices of changes the user approved — rejected files are simply omitted
    approved_indices: Optional[List[int]] = None