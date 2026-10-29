from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, UUID4, ConfigDict


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: UUID4
    run_id: UUID4
    batch_id: Optional[UUID4] = None
    dataset_name: str
    failure_category: str
    severity: str
    explanation: str
    evidence: Optional[Dict[str, Any]] = None
    recommended_action: str
    status: str
    requires_human_approval: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None


class IncidentRetryRequest(BaseModel):
    approved_by: Optional[str] = "ADMIN_OPERATOR"
