from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, UUID4, ConfigDict


class RecoveryAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_id: UUID4
    incident_id: UUID4
    policy_id: Optional[str] = None
    strategy_applied: str
    status: str
    execution_log: Optional[str] = None
    duration_ms: Optional[int] = None
    post_verification_passed: Optional[bool] = None
    post_verification_details: Optional[Dict[str, Any]] = None
    approved_by: Optional[str] = None
    executed_at: datetime


class DryRunRequest(BaseModel):
    incident_id: UUID4


class DryRunResponse(BaseModel):
    incident_id: UUID4
    strategy: str
    proposed_action: str
    impacted_rows: int
    will_require_approval: bool
    summary: Dict[str, Any]


class ApproveRequest(BaseModel):
    approved_by: str = "ENGINEERING_OPERATOR"
    comments: Optional[str] = None
