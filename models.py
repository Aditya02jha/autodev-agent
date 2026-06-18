from pydantic import BaseModel
from typing import List


class AffectedFile(BaseModel):
    file: str
    reason: str


class ChangePlan(BaseModel):
    summary: str
    affected_files: List[AffectedFile]
    changes: List[str]