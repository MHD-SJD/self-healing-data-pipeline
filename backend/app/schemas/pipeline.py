from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, UUID4, ConfigDict


class PipelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pipeline_id: str
    name: str
    description: Optional[str] = None
    schedule_interval: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PipelineRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: UUID4
    pipeline_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    trigger_type: str
    error_message: Optional[str] = None
    metadata_payload: Optional[Dict[str, Any]] = None


class RunTriggerRequest(BaseModel):
    auto_heal: bool = True
    custom_filepath: Optional[str] = None
